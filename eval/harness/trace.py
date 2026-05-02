"""TraceCapturer: wraps the active LLMProvider so every call_json invocation
gets recorded to disk for later inspection.

Phase 0 limitation: provider implementations parse responses internally, so
raw model text is not visible at this layer. We capture request, exception
status, latency, and which upstream function originated the call. Phase 2
(json-repair work) will add raw text capture by exposing a hook in the parse
layer.
"""
from __future__ import annotations

import inspect
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mockinterview.agent.providers.base import LLMProvider
from mockinterview.schemas.provider import ProviderTestResult

from eval.harness.schemas import (
    AttemptOutcome,
    AttemptTrace,
    CallParse,
    CallRequest,
    CallResponse,
    LLMCallTrace,
    dump_json,
)


# Modules that count as "business callers" for trace attribution.
_CALLER_HINT_MODULES = (
    "mockinterview.agent.",       # backend agent code
    "eval.harness.runner",        # harness-level synthetic callers (e.g., parse_resume_text)
)

# Modules to skip when walking the stack: they're plumbing layers (call_json
# wrapper, provider implementations, the trace wrapper itself) — not the
# upstream caller we want to credit.
_CALLER_SKIP_MODULES = (
    "eval.harness.trace",
    "mockinterview.agent.client",
    "mockinterview.agent.providers.",
)


def _infer_caller() -> str:
    """Walk the stack to find the closest business-level frame above the plumbing layers.

    Returns a string like "question_gen.generate_questions" or
    "runner._parse_resume_text", or "<unknown>" if nothing matches.
    """
    for frame in inspect.stack()[2:]:  # skip _infer_caller + record_call frames
        mod = frame.frame.f_globals.get("__name__", "")
        if any(mod.startswith(p) or mod == p.rstrip(".") for p in _CALLER_SKIP_MODULES):
            continue
        if any(mod.startswith(p) for p in _CALLER_HINT_MODULES):
            tail = mod.split(".")[-1]
            return f"{tail}.{frame.function}"
    return "<unknown>"


class TraceCapturer:
    """Collects LLMCallTrace records for one attempt; writes trace.json on close.

    Used as a context manager:

        with TraceCapturer(out_dir, case_id, attempt_idx) as cap:
            ... # set_active(TracingProvider(real, cap)) and run agent code

    The `outcome` is set externally by the runner when the attempt finishes.
    """

    def __init__(self, output_dir: Path, case_id: str, attempt_idx: int):
        self.output_dir = output_dir
        self.case_id = case_id
        self.attempt_idx = attempt_idx
        self._calls: list[LLMCallTrace] = []
        self._next_call_id = 1
        self._started_at: str = ""
        self._ended_at: str = ""
        self._outcome: AttemptOutcome | None = None

    def __enter__(self) -> "TraceCapturer":
        self._started_at = datetime.now(timezone.utc).isoformat()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._ended_at = datetime.now(timezone.utc).isoformat()
        self.flush()

    # -- recording ---------------------------------------------------------- #

    def record_call(
        self,
        *,
        provider: str,
        model: str,
        request: CallRequest,
        response: CallResponse,
        parse: CallParse,
        latency_ms: int,
        caller: str | None = None,
    ) -> None:
        self._calls.append(
            LLMCallTrace(
                call_id=self._next_call_id,
                caller=caller or _infer_caller(),
                timestamp=datetime.now(timezone.utc).isoformat(),
                provider=provider,
                model=model,
                request=request,
                response=response,
                parse=parse,
                latency_ms=latency_ms,
            )
        )
        self._next_call_id += 1

    def set_outcome(self, outcome: AttemptOutcome) -> None:
        self._outcome = outcome

    @property
    def call_count(self) -> int:
        return len(self._calls)

    # -- persistence -------------------------------------------------------- #

    def flush(self) -> Path:
        trace = AttemptTrace(
            case_id=self.case_id,
            attempt_idx=self.attempt_idx,
            started_at=self._started_at,
            ended_at=self._ended_at,
            calls=list(self._calls),
            outcome=self._outcome,
        )
        path = self.output_dir / "trace.json"
        dump_json(path, trace)
        return path


class TracingProvider(LLMProvider):
    """LLMProvider wrapper that records every call_json invocation to a TraceCapturer.

    Behavior:
      - delegates the actual call to `inner`
      - reads the ParseRecord that parse_json_response published on the context
        channel to fill raw_text + parse.status (success / repaired / failed)
      - on exception: records exception class+message; re-raises so caller observes
    """

    def __init__(self, inner: LLMProvider, capture: TraceCapturer):
        self._inner = inner
        self._capture = capture

    @property
    def inner(self) -> LLMProvider:
        return self._inner

    # -- LLMProvider interface --------------------------------------------- #

    def call_json(
        self,
        system: str,
        messages: list[dict[str, Any]],
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        from mockinterview.agent.client import consume_last_parse_record

        provider_name = type(self._inner).__name__.replace("Provider", "").lower()
        model = getattr(self._inner, "model", "<unknown>")
        request = CallRequest(system=system, messages=messages, max_tokens=max_tokens)

        # Drain any stale record before the call so we only see this call's outcome.
        consume_last_parse_record()

        t0 = time.perf_counter()
        try:
            result = self._inner.call_json(system, messages, max_tokens)
        except Exception as e:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            # parse_json_response may have published a ParseRecord with raw_text
            # before raising — pick that up if available so the trace shows the
            # actual model output we couldn't parse.
            rec = consume_last_parse_record()
            self._capture.record_call(
                provider=provider_name,
                model=model,
                request=request,
                response=CallResponse(raw_text=rec.raw_text if rec else None),
                parse=CallParse(
                    status="failed",
                    error=f"{type(e).__name__}: {e}",
                    repaired_diff=rec.repair_summary if rec else None,
                ),
                latency_ms=latency_ms,
            )
            raise
        else:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            rec = consume_last_parse_record()
            # status comes from the parse layer: "success" (clean parse) or
            # "repaired" (json-repair fixed it). Anything else means caller
            # bypassed parse_json_response — record as success since the call
            # didn't raise.
            parse_status = rec.status if rec and rec.status in ("success", "repaired") else "success"
            self._capture.record_call(
                provider=provider_name,
                model=model,
                request=request,
                response=CallResponse(raw_text=rec.raw_text if rec else None),
                parse=CallParse(
                    status=parse_status,                              # type: ignore[arg-type]
                    repaired_diff=rec.repair_summary if rec else None,
                ),
                latency_ms=latency_ms,
            )
            return result

    def test_connection(self) -> ProviderTestResult:
        return self._inner.test_connection()
