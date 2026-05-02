"""Data schemas for the evaluation harness.

These shapes serialize to JSON on disk under runs/<run_id>/. Forward-compatibility
constraints (must hold across minimal → full harness):

  * `tier` enum is permanently {tier1, tier2, tier3}. New capability differences
    go in `ProviderCapabilities` flags, not new tier values.
  * Field names never get renamed. New fields may be added (default-nullable so
    older runs stay readable).
  * `run_id` format is permanently `<UTC YYYY-MM-DDTHHMMSS>-<git-short>` so
    sort-by-name matches sort-by-time. Second-granularity is required —
    minute-only collided in Phase 0 when smoke + baseline ran in the same minute.
  * Top-level `failure_modes` keys are append-only.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

Tier = Literal["tier1", "tier2", "tier3"]
ParseStatus = Literal["success", "repaired", "retried", "failed"]
AttemptStatus = Literal["success", "parse_failure", "exception"]
FailureMode = Literal[
    "json_parse_error",
    "schema_validation_error",
    "exception",
    "timeout",
]


@dataclass(frozen=True)
class ProviderCapabilities:
    """Output-reliability features a provider exposes.

    Provider implementations read these to choose internal strategy inside
    `call_with_schema()`. Boolean flags are append-only across versions.
    """
    schema_strict: bool        # output validated against schema (tier1 candidate)
    force_tool_call: bool      # tool_use protocol can force model into structured path
    json_object: bool          # response_format=json_object available as soft fallback
    prompt_cache: bool         # server-side prompt caching supported


@dataclass
class ProviderInfo:
    name: str
    model: str
    tier: Tier
    base_url: str | None = None
    capabilities: ProviderCapabilities | None = None


# --------------------------------------------------------------------------- #
# trace.json                                                                  #
# --------------------------------------------------------------------------- #


@dataclass
class CallRequest:
    system: str
    messages: list[dict[str, Any]]
    max_tokens: int
    tools: list[dict[str, Any]] | None = None        # filled when call_with_schema lands (Phase 6+)
    tool_choice: Any | None = None


@dataclass
class CallResponse:
    raw_text: str | None              # provider-internal parsing means we may not see it pre-Phase-2
    tool_calls: Any | None = None
    stop_reason: str | None = None
    usage: dict[str, Any] | None = None


@dataclass
class CallParse:
    status: ParseStatus
    error: str | None = None
    repaired_diff: str | None = None  # filled by Phase 2 once json-repair lands
    retry_count: int = 0


@dataclass
class LLMCallTrace:
    call_id: int
    caller: str                       # which upstream function originated the call
    timestamp: str                    # ISO 8601
    provider: str
    model: str
    request: CallRequest
    response: CallResponse
    parse: CallParse
    latency_ms: int
    cost_estimate_usd: float = 0.0    # Phase 0: zero-fill, real pricing comes later


@dataclass
class AttemptOutcome:
    status: AttemptStatus
    error_class: str | None = None
    error_message: str | None = None
    produced_artifact: dict[str, Any] | None = None


@dataclass
class AttemptTrace:
    case_id: str
    attempt_idx: int
    started_at: str
    ended_at: str
    calls: list[LLMCallTrace] = field(default_factory=list)
    outcome: AttemptOutcome | None = None


# --------------------------------------------------------------------------- #
# result.json                                                                 #
# --------------------------------------------------------------------------- #


@dataclass
class AttemptResult:
    case_id: str
    attempt_idx: int
    success: bool
    n_questions: int = 0
    relevance_scores: list[int] | None = None     # null until judges enabled
    relevance_avg: float | None = None
    drill_hits: list[int] | None = None
    baseline_we_won: bool | None = None
    total_cost_usd: float = 0.0
    total_calls: int = 0
    failure_mode: FailureMode | None = None       # null on success


# --------------------------------------------------------------------------- #
# aggregate.json + summary.json                                               #
# --------------------------------------------------------------------------- #


@dataclass
class RateWithCI:
    value: float                       # successes / n
    successes: int
    n: int
    ci_95_lower: float                 # Wilson interval
    ci_95_upper: float


@dataclass
class StatBlock:
    mean: float
    std: float
    n: int


@dataclass
class CaseAggregate:
    case_id: str
    n_attempts: int
    success_rate: RateWithCI
    failure_modes: dict[str, int]                  # FailureMode -> count
    relevance_avg: StatBlock | None = None         # over successful attempts
    cost_per_attempt: StatBlock | None = None
    calls_per_attempt: StatBlock | None = None
    latency_per_attempt_ms: StatBlock | None = None


@dataclass
class RunSummary:
    overall_success_rate: float
    total_attempts: int
    total_cost_usd: float
    per_case: dict[str, dict[str, Any]]            # case_id -> CaseAggregate dict
    diff_vs_baseline: dict[str, Any] | None = None # filled by full harness


# --------------------------------------------------------------------------- #
# manifest.json                                                               #
# --------------------------------------------------------------------------- #


@dataclass
class RunManifest:
    run_id: str
    intent: str
    git_commit: str
    git_dirty: bool
    provider: ProviderInfo
    judge_provider: ProviderInfo | None
    cases: list[str]
    repeat_per_case: int
    started_at: str
    ended_at: str | None = None

    # Forward-compat fields — kept null in minimal runs, populated by full harness.
    prompt_versions: dict[str, str] = field(default_factory=dict)
    code_versions: dict[str, str] = field(default_factory=dict)
    baseline_run_id: str | None = None
    fix_under_test: str | None = None
    experiment_arm: str | None = None


# --------------------------------------------------------------------------- #
# JSON helpers                                                                #
# --------------------------------------------------------------------------- #


def _default(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(f"Not serializable: {type(obj).__name__}")


def dump_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, default=_default, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
