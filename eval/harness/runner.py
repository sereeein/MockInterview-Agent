"""Per-attempt runner: drives one full generate_questions cycle for a case,
with the active provider replaced by a TracingProvider so all LLM calls are
captured. Writes trace.json + result.json into the attempt directory.

Phase 0 scope:
  - parse_resume_text  (1 LLM call)
  - generate_questions (1 LLM call)
  - record success/failure + failure_mode classification
  - judges (relevance, drilling, baseline_compare) NOT run; that wires in
    later behind a `--with-judges` flag in cli.py.
"""
from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mockinterview.agent.client import build_cached_system, parse_json_response
from mockinterview.agent.providers import active, set_active
from mockinterview.agent.prompts.resume_parse import (
    RESUME_PARSE_SYSTEM,
    RESUME_PARSE_USER_TEMPLATE,
)
from mockinterview.agent.question_gen import generate_questions

from eval.harness.loader import Case
from eval.harness.schemas import (
    AttemptOutcome,
    AttemptResult,
    FailureMode,
    dump_json,
)
from eval.harness.trace import TraceCapturer, TracingProvider


def _parse_resume_text(text: str) -> dict[str, Any]:
    """Inline copy of run_eval.py's parse_resume_text — uses the same production
    prompt so we test the real path. Goes through `active()` so TracingProvider
    captures the call."""
    from mockinterview.agent.client import call_json
    return call_json(
        system_blocks=build_cached_system([RESUME_PARSE_SYSTEM]),
        messages=[
            {
                "role": "user",
                "content": RESUME_PARSE_USER_TEMPLATE.replace("{resume_text}", text),
            }
        ],
        max_tokens=4096,
    )


def _classify_failure(exc: BaseException) -> FailureMode:
    name = type(exc).__name__
    if name in ("JSONDecodeError", "ValueError"):
        msg = str(exc)
        if "Expecting" in msg or "JSON" in msg.upper() or "delimiter" in msg:
            return "json_parse_error"
    if name in ("ValidationError",):
        return "schema_validation_error"
    if name == "TimeoutError":
        return "timeout"
    return "exception"


def run_attempt(
    case: Case,
    attempt_idx: int,
    output_dir: Path,
) -> AttemptResult:
    """Run one attempt for `case`, writing trace.json and result.json into output_dir.

    `output_dir` is expected to be runs/<run_id>/cases/<case_id>/attempts/<NNN>/.
    The active provider must already be set in this context.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    real_provider = active()
    capture = TraceCapturer(output_dir, case.case_id, attempt_idx)
    tracing = TracingProvider(real_provider, capture)

    success = False
    failure_mode: FailureMode | None = None
    artifact: dict[str, Any] | None = None
    error_class: str | None = None
    error_message: str | None = None
    n_questions = 0

    with capture:
        # Swap in the tracing provider for the duration of this attempt; restore after.
        set_active(tracing)
        try:
            resume_text = case.resume_text()
            jd_text = case.jd_text()

            structured = _parse_resume_text(resume_text)

            qlist = generate_questions(
                role=case.role,
                resume_json=structured,
                jd_text=jd_text,
                company_name=None,
            )
            artifact = qlist.model_dump()
            n_questions = len(qlist.questions)
            success = True

        except Exception as e:
            failure_mode = _classify_failure(e)
            error_class = type(e).__name__
            error_message = f"{e}"
            # Attach a short stack tail to error_message for debuggability.
            tb_tail = "".join(traceback.format_exception(type(e), e, e.__traceback__))[-800:]
            error_message = f"{error_message}\n---\n{tb_tail}"
        finally:
            set_active(real_provider)

        capture.set_outcome(
            AttemptOutcome(
                status="success" if success else (
                    "parse_failure" if failure_mode == "json_parse_error" else "exception"
                ),
                error_class=error_class,
                error_message=error_message,
                produced_artifact=artifact,
            )
        )

    result = AttemptResult(
        case_id=case.case_id,
        attempt_idx=attempt_idx,
        success=success,
        n_questions=n_questions,
        total_calls=capture.call_count,
        failure_mode=None if success else failure_mode,
    )
    dump_json(output_dir / "result.json", result)
    return result


def run_case(
    case: Case,
    repeat: int,
    case_dir: Path,
) -> list[AttemptResult]:
    """Run `repeat` attempts for `case` under case_dir/attempts/<NNN>/."""
    attempts_root = case_dir / "attempts"
    attempts_root.mkdir(parents=True, exist_ok=True)

    results: list[AttemptResult] = []
    for i in range(1, repeat + 1):
        attempt_dir = attempts_root / f"{i:03d}"
        result = run_attempt(case, i, attempt_dir)
        results.append(result)
    return results
