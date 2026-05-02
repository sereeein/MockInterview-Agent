"""Tests for the parse + retry layer in mockinterview.agent.client.

Covers:
  - happy path JSON extraction (raw + fenced)
  - json-repair fallback for unescaped quote (the actual Phase 1 failure mode)
  - ParseRecord publication on the context channel
  - call_json retry behavior on parse failures
"""
import json

import pytest

from mockinterview.agent.client import (
    build_cached_system,
    call_json,
    consume_last_parse_record,
    parse_json_response,
)
from mockinterview.agent.providers import set_active
from mockinterview.agent.providers.base import LLMProvider
from mockinterview.schemas.provider import ProviderTestResult


# --------------------------------------------------------------------------- #
# parse_json_response                                                          #
# --------------------------------------------------------------------------- #


def test_build_cached_system_concatenates_parts():
    out = build_cached_system(["你是面试官", "rubric: ..."])
    assert isinstance(out, str)
    assert "你是面试官" in out
    assert "rubric: ..." in out


def test_parse_json_response_extracts_json_block():
    fake = '```json\n{"a": 1}\n```'
    assert parse_json_response(fake) == {"a": 1}


def test_parse_json_response_handles_raw_json():
    assert parse_json_response('{"a": 1}') == {"a": 1}


def test_parse_json_response_handles_trailing_comma():
    """Trailing comma is one of the cheap pre-cleanups."""
    assert parse_json_response('{"a": 1, "b": 2,}') == {"a": 1, "b": 2}


def test_parse_json_response_repairs_unescaped_quote():
    """The actual Phase 1 failure mode: model embeds a quoted phrase in a string
    value with bare ASCII quotes. json-repair recovers it."""
    text = '{"text": "只写了"撰写2份董事会汇报材料"。如果让你..."}'
    result = parse_json_response(text)
    assert result["text"].startswith("只写了")
    assert "撰写2份董事会汇报材料" in result["text"]


def test_parse_json_response_records_success_on_clean_parse():
    consume_last_parse_record()  # drain stale
    parse_json_response('{"a": 1}')
    rec = consume_last_parse_record()
    assert rec is not None
    assert rec.status == "success"
    assert rec.repaired is False


def test_parse_json_response_records_repaired_on_fallback():
    consume_last_parse_record()
    text = '{"text": "只写了"撰写2份董事会汇报材料"。"}'
    parse_json_response(text)
    rec = consume_last_parse_record()
    assert rec is not None
    assert rec.status == "repaired"
    assert rec.repaired is True
    assert rec.repair_summary is not None
    assert "json-repair" in rec.repair_summary


def test_parse_json_response_consumes_record():
    """consume_last_parse_record clears the value so a second consumer gets None."""
    consume_last_parse_record()
    parse_json_response('{"a": 1}')
    rec1 = consume_last_parse_record()
    rec2 = consume_last_parse_record()
    assert rec1 is not None
    assert rec2 is None


# --------------------------------------------------------------------------- #
# call_json retry                                                              #
# --------------------------------------------------------------------------- #


class _ScriptedProvider(LLMProvider):
    """Test double: returns scripted dicts or raises scripted exceptions in order.

    Each entry in `script` is either a dict (returned) or a callable raising
    an exception (raised on call). Records every call's messages for inspection.
    """

    def __init__(self, script):
        self.script = list(script)
        self.calls = []
        self.model = "test-model"

    def call_json(self, system, messages, max_tokens=4096):
        self.calls.append({"system": system, "messages": list(messages)})
        if not self.script:
            raise AssertionError("provider script exhausted")
        item = self.script.pop(0)
        if callable(item):
            item()  # raises
        return item

    def test_connection(self) -> ProviderTestResult:
        return ProviderTestResult(
            ok=True, category="ok", http_status=200,
            provider_message=None, raw_response=None, elapsed_ms=0,
        )


def _raise_json_decode():
    raise json.JSONDecodeError("Expecting ',' delimiter", "...", 0)


@pytest.fixture
def reset_provider():
    """Save/restore active provider around each test."""
    from mockinterview.agent.providers import _active

    token = _active.set(None)
    try:
        yield
    finally:
        _active.reset(token)


def test_call_json_no_retry_on_success(reset_provider):
    p = _ScriptedProvider([{"ok": True}])
    set_active(p)
    result = call_json("system", [{"role": "user", "content": "hi"}], max_retries=1)
    assert result == {"ok": True}
    assert len(p.calls) == 1


def test_call_json_retries_once_on_parse_failure_then_succeeds(reset_provider):
    p = _ScriptedProvider([_raise_json_decode, {"ok": True}])
    set_active(p)
    result = call_json("system", [{"role": "user", "content": "hi"}], max_retries=1)
    assert result == {"ok": True}
    assert len(p.calls) == 2
    # The second call should include the correction message appended after the original.
    second_messages = p.calls[1]["messages"]
    assert len(second_messages) == 2
    assert second_messages[0]["content"] == "hi"
    assert "合法 JSON" in second_messages[1]["content"]


def test_call_json_raises_after_retries_exhausted(reset_provider):
    p = _ScriptedProvider([_raise_json_decode, _raise_json_decode])
    set_active(p)
    with pytest.raises(json.JSONDecodeError):
        call_json("system", [{"role": "user", "content": "hi"}], max_retries=1)
    assert len(p.calls) == 2  # initial + 1 retry


def test_call_json_max_retries_zero_means_no_retry(reset_provider):
    p = _ScriptedProvider([_raise_json_decode])
    set_active(p)
    with pytest.raises(json.JSONDecodeError):
        call_json("system", [{"role": "user", "content": "hi"}], max_retries=0)
    assert len(p.calls) == 1
