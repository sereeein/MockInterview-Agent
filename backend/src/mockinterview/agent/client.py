from __future__ import annotations

import json
import re
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from mockinterview.agent.providers import active

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.DOTALL)


# --------------------------------------------------------------------------- #
# Parse-record context channel                                                 #
# --------------------------------------------------------------------------- #
#
# Why this exists:
#   The eval harness needs to record per-call parse outcomes (success / repaired /
#   retried / failed) and the raw model text — but provider implementations parse
#   internally before returning, so the outer wrapper can't see those details.
#
#   We use a ContextVar so parse_json_response can publish its outcome where the
#   wrapper (TracingProvider in eval/harness/trace.py) can read it after the
#   call returns. Production code never reads this — it's tracing-only.
#
#   The ContextVar is reset on each call_json entry so stale records don't leak
#   between unrelated calls if a wrapper forgets to consume it.


@dataclass
class ParseRecord:
    raw_text: str | None = None
    status: str = "success"           # success | repaired | failed
    error: str | None = None
    repaired: bool = False
    repair_summary: str | None = None # e.g. "json_repair fixed unescaped quote"


_last_parse_record: ContextVar[ParseRecord | None] = ContextVar(
    "_last_parse_record", default=None
)


def consume_last_parse_record() -> ParseRecord | None:
    """Read and clear the most recent ParseRecord. For tracing wrappers only."""
    rec = _last_parse_record.get()
    _last_parse_record.set(None)
    return rec


def _publish(record: ParseRecord) -> None:
    _last_parse_record.set(record)


# --------------------------------------------------------------------------- #
# Parse layer                                                                  #
# --------------------------------------------------------------------------- #


def _clean_json_payload(payload: str) -> str:
    """Best-effort pre-clean for common LLM output quirks.

    Conservative — only fixes things that are unambiguously safe:
      - Chinese full-width punctuation in structural positions (mostly comma/colon)
      - Trailing commas before closing brace/bracket

    Aggressive cleanup (unescaped quotes, missing brackets, etc.) is delegated to
    json-repair in the fallback path so we don't risk corrupting valid JSON here.
    """
    payload = (
        payload
        .replace("，", ",")
        .replace("：", ":")
    )
    payload = re.sub(r",(\s*[}\]])", r"\1", payload)
    return payload


def _extract_payload(text: str) -> str:
    """Strip code fences / extract braces; otherwise return text as-is."""
    m = _JSON_FENCE.search(text)
    if m:
        return m.group(1)
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last > first:
        return text[first : last + 1]
    return text


def parse_json_response(text: str) -> dict[str, Any]:
    """Extract + parse a JSON object from raw model text.

    Strategy (in order):
      1. Extract candidate from ```json fence or {...} substring
      2. Light cleanup (`_clean_json_payload`)
      3. `json.loads` fast path
      4. On failure: `json_repair.repair_json` fallback (handles unescaped quotes,
         missing commas, truncated objects, etc.)
      5. On still-failure: raise JSONDecodeError so caller can choose to retry

    Publishes a `ParseRecord` to the context channel for tracing wrappers.
    """
    payload = _extract_payload(text)
    cleaned = _clean_json_payload(payload)

    # Fast path
    try:
        result = json.loads(cleaned)
        _publish(ParseRecord(raw_text=text, status="success"))
        return result
    except json.JSONDecodeError as fast_err:
        # json-repair fallback
        try:
            from json_repair import repair_json

            repaired = repair_json(cleaned, return_objects=True)
            if not isinstance(repaired, dict):
                # repair_json returned a non-dict (str, list, None) — treat as failure
                # so caller can re-prompt rather than handing back wrong shape.
                msg = (
                    f"json-repair returned {type(repaired).__name__}, expected dict. "
                    f"original error: {fast_err}"
                )
                _publish(
                    ParseRecord(
                        raw_text=text,
                        status="failed",
                        error=msg,
                    )
                )
                raise json.JSONDecodeError(msg, cleaned, getattr(fast_err, "pos", 0))

            _publish(
                ParseRecord(
                    raw_text=text,
                    status="repaired",
                    repaired=True,
                    repair_summary=(
                        f"json-repair recovered from "
                        f"{type(fast_err).__name__} at line {fast_err.lineno} "
                        f"col {fast_err.colno}"
                    ),
                )
            )
            return repaired

        except json.JSONDecodeError:
            raise   # already published above
        except Exception as repair_err:
            # json-repair itself blew up (rare). Treat as parse failure.
            msg = f"json-repair raised {type(repair_err).__name__}: {repair_err}"
            _publish(
                ParseRecord(
                    raw_text=text,
                    status="failed",
                    error=msg,
                )
            )
            raise json.JSONDecodeError(msg, cleaned, getattr(fast_err, "pos", 0))


# --------------------------------------------------------------------------- #
# Top-level call wrapper                                                       #
# --------------------------------------------------------------------------- #


def build_cached_system(parts: list[str]) -> list[dict[str, Any]] | str:
    """Concatenate system prompt strings. Back-compat shim — callers historically
    passed Anthropic-shaped block lists; provider now handles caching internally
    so we just join to a single string."""
    return "\n\n".join(parts)


_RETRY_CORRECTION_MESSAGE = (
    "上一轮输出无法解析为合法 JSON。请严格按之前的要求输出有效 JSON——"
    "尤其注意字符串值内不要嵌入未转义的双引号（如要引用原文请用单引号 '…' 或不加引号）。"
)


def call_json(
    system_blocks: list[dict[str, Any]] | str | list[str],
    messages: list[dict[str, Any]],
    max_tokens: int = 4096,
    model: str | None = None,
    max_retries: int = 1,
) -> dict[str, Any]:
    """Run system + messages against the active provider; return parsed JSON.

    Parse-failure recovery (provider-agnostic):
      1. parse_json_response fast path → json-repair fallback (inside provider call)
      2. If still fails: re-prompt the provider with a correction message and parse
         again. Up to `max_retries` retries (default 1 = at most 2 LLM calls total).

    Each LLM call records its own ParseRecord on the context channel — the harness
    wrapper consumes them in order to attribute success/repaired/retried per call.

    `system_blocks` accepts str / list[str] / legacy list[dict] for back-compat.
    `model` is currently unused (provider holds its own model setting).
    """
    if isinstance(system_blocks, str):
        system = system_blocks
    elif isinstance(system_blocks, list):
        parts: list[str] = []
        for b in system_blocks:
            if isinstance(b, dict) and "text" in b:
                parts.append(str(b["text"]))
            elif isinstance(b, str):
                parts.append(b)
        system = "\n\n".join(parts)
    else:
        system = str(system_blocks)

    current_messages = list(messages)
    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return active().call_json(
                system=system, messages=current_messages, max_tokens=max_tokens
            )
        except json.JSONDecodeError as e:
            last_err = e
            if attempt >= max_retries:
                break
            # Append a correction turn and try again. We send a synthetic
            # user-role turn rather than a system-role turn so it works on
            # providers that disallow multi-system messages mid-conversation.
            current_messages = current_messages + [
                {"role": "user", "content": _RETRY_CORRECTION_MESSAGE}
            ]

    assert last_err is not None
    raise last_err
