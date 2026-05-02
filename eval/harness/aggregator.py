"""Aggregation: turn per-attempt AttemptResults into per-case CaseAggregate
and a run-level RunSummary. Reads result.json files written by runner.py;
keeps reading concerns out of run-time so re-aggregation is cheap.
"""
from __future__ import annotations

import statistics
from pathlib import Path
from typing import Any

from eval.harness.schemas import (
    AttemptResult,
    CaseAggregate,
    FailureMode,
    RateWithCI,
    RunSummary,
    StatBlock,
    dump_json,
    load_json,
)
from eval.harness.significance import wilson_ci

# Failure-mode keys that always appear (count 0 if absent) so downstream tools
# can rely on their presence.
_FAILURE_MODE_KEYS: tuple[FailureMode, ...] = (
    "json_parse_error",
    "schema_validation_error",
    "exception",
    "timeout",
)


def _stat_block(values: list[float]) -> StatBlock | None:
    if not values:
        return None
    return StatBlock(
        mean=statistics.fmean(values),
        std=statistics.stdev(values) if len(values) > 1 else 0.0,
        n=len(values),
    )


def aggregate_case(case_id: str, attempts: list[AttemptResult]) -> CaseAggregate:
    n = len(attempts)
    successes = sum(1 for a in attempts if a.success)
    lo, hi = wilson_ci(successes, n) if n > 0 else (0.0, 0.0)

    failure_modes: dict[str, int] = {k: 0 for k in _FAILURE_MODE_KEYS}
    for a in attempts:
        if not a.success and a.failure_mode:
            failure_modes[a.failure_mode] = failure_modes.get(a.failure_mode, 0) + 1

    rel_values = [a.relevance_avg for a in attempts if a.success and a.relevance_avg is not None]
    cost_values = [a.total_cost_usd for a in attempts]
    calls_values = [float(a.total_calls) for a in attempts]

    return CaseAggregate(
        case_id=case_id,
        n_attempts=n,
        success_rate=RateWithCI(
            value=successes / n if n else 0.0,
            successes=successes,
            n=n,
            ci_95_lower=lo,
            ci_95_upper=hi,
        ),
        failure_modes=failure_modes,
        relevance_avg=_stat_block(rel_values) if rel_values else None,
        cost_per_attempt=_stat_block(cost_values),
        calls_per_attempt=_stat_block(calls_values),
        latency_per_attempt_ms=None,   # latency not yet rolled up in result.json
    )


def aggregate_run(case_aggregates: dict[str, CaseAggregate]) -> RunSummary:
    total_attempts = sum(c.n_attempts for c in case_aggregates.values())
    total_successes = sum(c.success_rate.successes for c in case_aggregates.values())
    total_cost = sum(
        (c.cost_per_attempt.mean * c.n_attempts) if c.cost_per_attempt else 0.0
        for c in case_aggregates.values()
    )
    return RunSummary(
        overall_success_rate=(total_successes / total_attempts) if total_attempts else 0.0,
        total_attempts=total_attempts,
        total_cost_usd=total_cost,
        per_case={cid: _agg_to_dict(agg) for cid, agg in case_aggregates.items()},
    )


def _agg_to_dict(agg: CaseAggregate) -> dict[str, Any]:
    """dataclasses.asdict equivalent that handles nested dataclasses for JSON
    serialization at the summary level."""
    return {
        "case_id": agg.case_id,
        "n_attempts": agg.n_attempts,
        "success_rate": {
            "value": agg.success_rate.value,
            "successes": agg.success_rate.successes,
            "n": agg.success_rate.n,
            "ci_95_lower": agg.success_rate.ci_95_lower,
            "ci_95_upper": agg.success_rate.ci_95_upper,
        },
        "failure_modes": agg.failure_modes,
        "relevance_avg": _stat_to_dict(agg.relevance_avg),
        "cost_per_attempt": _stat_to_dict(agg.cost_per_attempt),
        "calls_per_attempt": _stat_to_dict(agg.calls_per_attempt),
        "latency_per_attempt_ms": _stat_to_dict(agg.latency_per_attempt_ms),
    }


def _stat_to_dict(s: StatBlock | None) -> dict[str, Any] | None:
    if s is None:
        return None
    return {"mean": s.mean, "std": s.std, "n": s.n}


# --------------------------------------------------------------------------- #
# Disk-driven aggregation (reads result.json files)                           #
# --------------------------------------------------------------------------- #


def load_attempt_results(case_dir: Path) -> list[AttemptResult]:
    """Read every result.json under case_dir/attempts/*/."""
    results: list[AttemptResult] = []
    attempts_root = case_dir / "attempts"
    if not attempts_root.exists():
        return results
    for adir in sorted(attempts_root.iterdir()):
        rfile = adir / "result.json"
        if not rfile.exists():
            continue
        raw = load_json(rfile)
        results.append(
            AttemptResult(
                case_id=raw["case_id"],
                attempt_idx=raw["attempt_idx"],
                success=raw["success"],
                n_questions=raw.get("n_questions", 0),
                relevance_scores=raw.get("relevance_scores"),
                relevance_avg=raw.get("relevance_avg"),
                drill_hits=raw.get("drill_hits"),
                baseline_we_won=raw.get("baseline_we_won"),
                total_cost_usd=raw.get("total_cost_usd", 0.0),
                total_calls=raw.get("total_calls", 0),
                failure_mode=raw.get("failure_mode"),
            )
        )
    return results


def write_case_aggregate(case_dir: Path, agg: CaseAggregate) -> Path:
    path = case_dir / "aggregate.json"
    dump_json(path, agg)
    return path


def write_run_summary(run_dir: Path, summary: RunSummary) -> Path:
    path = run_dir / "summary.json"
    dump_json(path, summary)
    return path
