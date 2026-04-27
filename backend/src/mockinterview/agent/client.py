from __future__ import annotations

import json
import re
from typing import Any

from mockinterview.agent.providers import active

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.DOTALL)


def _clean_json_payload(payload: str) -> str:
    """Best-effort cleanup of common LLM output quirks before parsing.

    Handles: Chinese punctuation slipping into structural positions
    (commas / colons / quotes), and trailing commas before }/]. Does NOT try
    to fix unmatched braces / quotes — those should fail loudly so we can
    re-prompt. Aggressive enough to fix 90% of "Expecting ',' delimiter" errors
    we've seen in practice, conservative enough not to corrupt valid JSON.
    """
    # Chinese punctuation → ASCII equivalents. Mostly affects model output where
    # the model slipped into Chinese typography mid-token (esp. on Claude reverse-
    # proxy services). Acceptable collateral if a Chinese string value gets its
    # commas swapped — values are usually short and the agent reads them as text.
    payload = (
        payload
        .replace("，", ",")
        .replace("：", ":")
        .replace("“", '"')
        .replace("”", '"')
    )
    # Trailing comma before closing brace/bracket: common LLM mistake
    payload = re.sub(r",(\s*[}\]])", r"\1", payload)
    return payload


def parse_json_response(text: str) -> dict[str, Any]:
    """Extract JSON object from raw model text (with or without ```json fence).

    Strategy:
      1. If a ```json fence is present, take its inner content.
      2. Otherwise take the substring from first '{' to last '}'.
      3. Apply _clean_json_payload (Chinese punctuation, trailing commas).
      4. Parse. On failure, raise JSONDecodeError so caller can choose to re-prompt.
    """
    m = _JSON_FENCE.search(text)
    if m:
        payload = m.group(1)
    else:
        first = text.find("{")
        last = text.rfind("}")
        payload = text[first : last + 1] if first != -1 and last > first else text

    payload = _clean_json_payload(payload)
    return json.loads(payload)


def build_cached_system(parts: list[str]) -> list[dict[str, Any]] | str:
    """Concatenate multiple system prompt strings.

    Backward-compat shim: legacy callers passed list[dict] with `cache_control` markers.
    Now we just return a single string; provider handles caching internally.
    Kept as a function so call sites don't need to change."""
    return "\n\n".join(parts)


def call_json(
    system_blocks: list[dict[str, Any]] | str | list[str],
    messages: list[dict[str, Any]],
    max_tokens: int = 4096,
    model: str | None = None,
) -> dict[str, Any]:
    """Run a system + messages prompt against the active provider; return parsed JSON.

    `system_blocks` accepts:
      - str (preferred): treated as the system prompt.
      - list[dict] (legacy Anthropic shape): joined by extracting "text" fields.
      - list[str]: joined with double-newlines.
    `model` is currently ignored at this layer — the active provider has its own model
    set at construction time. Kept in the signature for backward compat with old callers.
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

    return active().call_json(system=system, messages=messages, max_tokens=max_tokens)
