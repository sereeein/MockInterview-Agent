"""Command-line interface for the evaluation harness.

Phase 0: only `run` is implemented. The argparse skeleton already declares the
subcommand layout for full harness commands (show / diff / stats / promote)
so adding them later is a paste-in, not a restructure.

Usage examples:

    # Run a single case 2 times (smoke test)
    cd backend && env -u VIRTUAL_ENV uv run --active python -m eval.harness.cli \\
        run --case ai_no_jd --repeat 2 --intent "phase 0 smoke test"

    # Run all cases for one role
    ... run --role pm --repeat 5

    # Use a non-default provider
    MOCK_PROVIDER=deepseek MOCK_API_KEY=... \\
        ... run --case ai_no_jd --repeat 3
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Import-time bootstrap: make `mockinterview` importable regardless of cwd, and
# auto-load backend/.env so a plain `python -m eval.harness.cli ...` works.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BACKEND_SRC = _REPO_ROOT / "backend" / "src"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_dotenv(_REPO_ROOT / "backend" / ".env")

from rich.console import Console
from rich.table import Table

from eval.harness.aggregator import (
    aggregate_case,
    aggregate_run,
    load_attempt_results,
    write_case_aggregate,
    write_run_summary,
)
from eval.harness.loader import load_cases
from eval.harness.runner import run_case
from eval.harness.schemas import (
    ProviderCapabilities,
    ProviderInfo,
    RunManifest,
    dump_json,
)

EVAL_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = EVAL_ROOT / "runs"

console = Console()


# --------------------------------------------------------------------------- #
# Provider construction (mirrors run_eval.py's env-driven setup)              #
# --------------------------------------------------------------------------- #


def _build_provider_from_env():
    """Read MOCK_PROVIDER / MOCK_API_KEY / MOCK_MODEL / MOCK_BASE_URL from env.

    API key resolution order:
      1. MOCK_API_KEY (explicit override)
      2. <PROVIDER>_API_KEY  (e.g. DEEPSEEK_API_KEY, ANTHROPIC_API_KEY) — convention
      3. ANTHROPIC_API_KEY (back-compat default for old runs)
    """
    provider = os.environ.get("MOCK_PROVIDER", "anthropic")
    provider_key_var = f"{provider.upper()}_API_KEY"
    api_key = (
        os.environ.get("MOCK_API_KEY")
        or os.environ.get(provider_key_var)
        or os.environ.get("ANTHROPIC_API_KEY", "")
    )
    if not api_key:
        raise SystemExit(
            f"No API key found. Set MOCK_API_KEY or {provider_key_var} in env / backend/.env."
        )
    model = os.environ.get("MOCK_MODEL") or None
    base_url = os.environ.get("MOCK_BASE_URL") or None

    from mockinterview.agent.providers import make_provider, set_active

    inst = make_provider(provider=provider, api_key=api_key, model=model, base_url=base_url)
    set_active(inst)
    return provider, inst


def _provider_info(name: str, inst) -> ProviderInfo:
    """Best-effort metadata snapshot. Tier and capabilities are placeholders
    until call_with_schema lands in Phase 4+ — for now everything is tier3
    (no schema-strict guarantees from call_json) which is honest about the
    current state.
    """
    return ProviderInfo(
        name=name,
        model=getattr(inst, "model", "<unknown>"),
        tier="tier3",
        base_url=getattr(inst, "base_url", None),
        capabilities=ProviderCapabilities(
            schema_strict=False,
            force_tool_call=False,
            json_object=False,
            prompt_cache=(name == "anthropic"),
        ),
    )


# --------------------------------------------------------------------------- #
# Run identity helpers                                                        #
# --------------------------------------------------------------------------- #


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short=10", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def _git_dirty() -> bool:
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain"], text=True, stderr=subprocess.DEVNULL,
        )
        return bool(out.strip())
    except Exception:
        return False


def _make_run_id(commit: str) -> str:
    """run_id format: <UTC YYYY-MM-DDTHHMMSS>-<git-short-7>.

    Second-granularity timestamp is what guarantees uniqueness across back-to-back
    runs (pre-fix → post-fix, smoke → baseline). Lexicographic sort matches
    chronological order. NEVER drop the seconds field — runs sharing the same
    minute were observed to collide and overwrite each other in early Phase 0.
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
    return f"{ts}-{commit[:7]}"


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _capture_prompt_versions() -> dict[str, str]:
    """Hash key prompt strings used by the harness path. New prompts get added
    here as they become relevant to harness runs."""
    versions: dict[str, str] = {}
    try:
        from mockinterview.agent.prompts.question_gen import QUESTION_GEN_SYSTEM
        from mockinterview.agent.prompts.resume_parse import RESUME_PARSE_SYSTEM

        versions["question_gen_system"] = _hash_text(QUESTION_GEN_SYSTEM)
        versions["resume_parse_system"] = _hash_text(RESUME_PARSE_SYSTEM)
    except Exception as e:
        versions["__error__"] = str(e)[:120]
    return versions


# --------------------------------------------------------------------------- #
# `run` subcommand                                                            #
# --------------------------------------------------------------------------- #


def cmd_run(args: argparse.Namespace) -> int:
    cases = load_cases(
        filter_ids=args.case or None,
        filter_role=args.role,
    )
    if not cases:
        console.print("[red]no cases matched the filter[/red]")
        return 2

    provider_name, provider_inst = _build_provider_from_env()
    commit = _git_commit()
    run_id = _make_run_id(commit)
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = RunManifest(
        run_id=run_id,
        intent=args.intent or "<unspecified>",
        git_commit=commit,
        git_dirty=_git_dirty(),
        provider=_provider_info(provider_name, provider_inst),
        judge_provider=None,                          # judges not run in Phase 0
        cases=[c.case_id for c in cases],
        repeat_per_case=args.repeat,
        started_at=datetime.now(timezone.utc).isoformat(),
        prompt_versions=_capture_prompt_versions(),
    )
    dump_json(run_dir / "manifest.json", manifest)

    console.print(f"[bold]run_id[/bold] = {run_id}")
    console.print(f"[bold]provider[/bold] = {provider_name} / {manifest.provider.model}")
    console.print(f"[bold]cases[/bold] = {len(cases)} × {args.repeat} attempts each")

    case_aggs = {}
    for case in cases:
        console.print(f"\n[cyan]→ {case.case_id}[/cyan] (role={case.role}, jd={'yes' if case.jd_path else 'no'})")
        case_dir = run_dir / "cases" / case.case_id
        results = run_case(case, args.repeat, case_dir)

        agg = aggregate_case(case.case_id, results)
        write_case_aggregate(case_dir, agg)
        case_aggs[case.case_id] = agg

        succ = agg.success_rate.successes
        n = agg.success_rate.n
        lo = agg.success_rate.ci_95_lower
        hi = agg.success_rate.ci_95_upper
        console.print(
            f"  success {succ}/{n} = {succ/n:.0%}  "
            f"(95% CI [{lo:.0%}, {hi:.0%}])"
        )
        if any(v > 0 for v in agg.failure_modes.values()):
            modes = ", ".join(f"{k}={v}" for k, v in agg.failure_modes.items() if v > 0)
            console.print(f"  failure_modes: {modes}")

    summary = aggregate_run(case_aggs)
    write_run_summary(run_dir, summary)

    # Update manifest with end timestamp
    manifest.ended_at = datetime.now(timezone.utc).isoformat()
    dump_json(run_dir / "manifest.json", manifest)

    # Pretty summary table
    table = Table(title="\nRun summary")
    table.add_column("case", style="cyan")
    table.add_column("succ/n")
    table.add_column("rate")
    table.add_column("CI 95%")
    for cid, agg in case_aggs.items():
        sr = agg.success_rate
        table.add_row(
            cid,
            f"{sr.successes}/{sr.n}",
            f"{sr.value:.0%}",
            f"[{sr.ci_95_lower:.0%}, {sr.ci_95_upper:.0%}]",
        )
    console.print(table)
    console.print(f"\n[green]artifacts written to[/green]: {run_dir}")
    return 0


# --------------------------------------------------------------------------- #
# Stub subcommands (skeleton; implemented in full harness)                    #
# --------------------------------------------------------------------------- #


def cmd_show(args: argparse.Namespace) -> int:
    console.print("[yellow]`show` command not implemented in Phase 0 minimal harness.[/yellow]")
    return 1


def cmd_diff(args: argparse.Namespace) -> int:
    console.print("[yellow]`diff` command not implemented in Phase 0 minimal harness.[/yellow]")
    return 1


def cmd_stats(args: argparse.Namespace) -> int:
    """Re-aggregate from already-written result.json files. Useful when you
    edit an attempt manually or want to recompute aggregates without rerunning."""
    run_id = args.run_id
    run_dir = RUNS_DIR / run_id
    if not run_dir.exists():
        console.print(f"[red]run not found:[/red] {run_dir}")
        return 2

    cases_root = run_dir / "cases"
    case_aggs = {}
    for cdir in sorted(cases_root.iterdir()):
        if not cdir.is_dir():
            continue
        results = load_attempt_results(cdir)
        if not results:
            continue
        agg = aggregate_case(cdir.name, results)
        write_case_aggregate(cdir, agg)
        case_aggs[cdir.name] = agg

    summary = aggregate_run(case_aggs)
    write_run_summary(run_dir, summary)
    console.print(f"[green]re-aggregated[/green]: {run_dir}")
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    console.print("[yellow]`promote` command not implemented in Phase 0 minimal harness.[/yellow]")
    return 1


# --------------------------------------------------------------------------- #
# Argparse                                                                    #
# --------------------------------------------------------------------------- #


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="eval.harness", description="MockInterview eval harness")
    sub = p.add_subparsers(dest="cmd", required=True)

    # run
    p_run = sub.add_parser("run", help="run a case (or all cases) N times")
    p_run.add_argument("--case", action="append", default=[], help="case_id (repeatable)")
    p_run.add_argument("--role", default=None, help="filter by role: pm/data/ai/other")
    p_run.add_argument("--repeat", type=int, default=1, help="attempts per case")
    p_run.add_argument("--intent", default=None, help="free-text description of why this run was launched")
    p_run.set_defaults(func=cmd_run)

    # show (stub)
    p_show = sub.add_parser("show", help="(future) pretty-print one attempt's trace")
    p_show.add_argument("run_id")
    p_show.add_argument("--case", default=None)
    p_show.add_argument("--attempt", type=int, default=None)
    p_show.set_defaults(func=cmd_show)

    # stats (re-aggregate without rerunning)
    p_stats = sub.add_parser("stats", help="recompute aggregates from result.json files")
    p_stats.add_argument("run_id")
    p_stats.set_defaults(func=cmd_stats)

    # diff (stub)
    p_diff = sub.add_parser("diff", help="(future) compare two runs")
    p_diff.add_argument("run_a")
    p_diff.add_argument("run_b")
    p_diff.set_defaults(func=cmd_diff)

    # promote (stub)
    p_promote = sub.add_parser("promote", help="(future) tag a run as the new baseline")
    p_promote.add_argument("run_id")
    p_promote.add_argument("--as", dest="baseline_name", required=True)
    p_promote.set_defaults(func=cmd_promote)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
