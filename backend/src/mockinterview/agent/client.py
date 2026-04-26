from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from anthropic import Anthropic

from mockinterview.config import get_settings

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.DOTALL)


@lru_cache
def get_client() -> Anthropic:
    return Anthropic(api_key=get_settings().anthropic_api_key)


def build_cached_system(parts: list[str]) -> list[dict[str, Any]]:
    """Construct a system prompt as a list of text blocks where the LAST block
    carries cache_control. This puts the static rubric/prompt context in cache
    while still allowing per-call dynamic prefixes."""
    blocks: list[dict[str, Any]] = [{"type": "text", "text": p} for p in parts]
    if blocks:
        blocks[-1]["cache_control"] = {"type": "ephemeral"}
    return blocks


def parse_json_response(text: str) -> dict[str, Any]:
    m = _JSON_FENCE.search(text)
    payload = m.group(1) if m else text
    return json.loads(payload)


def call_json(
    system_blocks: list[dict[str, Any]],
    messages: list[dict[str, Any]],
    max_tokens: int = 4096,
    model: str | None = None,
) -> dict[str, Any]:
    client = get_client()
    resp = client.messages.create(
        model=model or get_settings().claude_model,
        system=system_blocks,
        messages=messages,
        max_tokens=max_tokens,
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    return parse_json_response(text)
