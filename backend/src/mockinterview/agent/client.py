from __future__ import annotations

import json
import re
from typing import Any

from mockinterview.agent.providers import active

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.DOTALL)


def parse_json_response(text: str) -> dict[str, Any]:
    """Extract JSON object from raw model text (with or without ```json fence)."""
    m = _JSON_FENCE.search(text)
    payload = m.group(1) if m else text
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
