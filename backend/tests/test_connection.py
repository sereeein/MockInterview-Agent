"""Tests for v1.1 T2: provider connection test (`POST /provider/test`).

Layered: helper unit tests → per-provider mock tests → route integration test.
1 optional real-LLM happy-path is gated behind ANTHROPIC_API_KEY env var.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from mockinterview.agent.providers.test_support import (
    categorize_error,
    validate_json_response,
)


# ---------- helper unit tests ----------


def test_validate_json_response_ok():
    ok, excerpt = validate_json_response('{"ok": true, "echo": "ping"}')
    assert ok is True
    assert excerpt is None


def test_validate_json_response_invalid_json():
    ok, excerpt = validate_json_response("Sure! Here is the answer: ping")
    assert ok is False
    assert excerpt is not None
    assert "Sure!" in excerpt


def test_validate_json_response_missing_ok_field():
    ok, excerpt = validate_json_response('{"status": "ok"}')
    assert ok is False
    assert excerpt is not None


def test_validate_json_response_ok_false():
    ok, excerpt = validate_json_response('{"ok": false}')
    assert ok is False


def test_validate_json_response_truncates_long_excerpt():
    long_text = "x" * 1000
    ok, excerpt = validate_json_response(long_text)
    assert ok is False
    assert excerpt is not None
    assert len(excerpt) == 500


# ---------- categorize_error: status_code branch ----------


def _err_with(status: int | None = None, code: int | None = None, message: str = "boom"):
    """Build a fake exception that mimics how SDKs expose status codes."""

    class FakeError(Exception):
        pass

    e = FakeError(message)
    if status is not None:
        e.status_code = status  # type: ignore[attr-defined]
    if code is not None:
        e.code = code  # type: ignore[attr-defined]
    return e


def test_categorize_auth_401():
    cat, status = categorize_error(_err_with(status=401))
    assert cat == "auth"
    assert status == 401


def test_categorize_auth_403():
    cat, status = categorize_error(_err_with(status=403))
    assert cat == "auth"
    assert status == 403


def test_categorize_rate_limit_429():
    cat, status = categorize_error(_err_with(status=429, message="rate limit exceeded"))
    assert cat == "rate_limit"
    assert status == 429


def test_categorize_network_5xx():
    cat, status = categorize_error(_err_with(status=502))
    assert cat == "network"
    assert status == 502


def test_categorize_network_via_class_name():
    class APIConnectionError(Exception):
        pass

    cat, status = categorize_error(APIConnectionError("connection refused"))
    assert cat == "network"


def test_categorize_network_via_message():
    class GenericError(Exception):
        pass

    cat, _ = categorize_error(GenericError("request timed out after 30s"))
    assert cat == "network"


def test_categorize_unknown_4xx():
    cat, status = categorize_error(_err_with(status=418))
    assert cat == "unknown"
    assert status == 418


def test_categorize_unknown_when_no_signal():
    cat, status = categorize_error(_err_with(message="something weird"))
    assert cat == "unknown"
    assert status is None


def test_categorize_auth_via_class_name():
    class AuthenticationError(Exception):
        pass

    cat, _ = categorize_error(AuthenticationError("invalid API key"))
    assert cat == "auth"


# ---------- per-provider test_connection: mocked SDK ----------


def test_anthropic_test_connection_ok():
    from mockinterview.agent.providers.anthropic import AnthropicProvider

    p = AnthropicProvider(api_key="sk-test", model="claude-opus-4-7")
    fake_resp = MagicMock()
    fake_resp.content = [MagicMock(type="text", text='{"ok": true, "echo": "ping"}')]
    with patch.object(p.client.messages, "create", return_value=fake_resp):
        result = p.test_connection()

    assert result.ok is True
    assert result.category == "ok"
    assert result.http_status == 200
    assert result.elapsed_ms >= 0


def test_anthropic_test_connection_json_format_failure():
    from mockinterview.agent.providers.anthropic import AnthropicProvider

    p = AnthropicProvider(api_key="sk-test", model="claude-opus-4-7")
    fake_resp = MagicMock()
    fake_resp.content = [MagicMock(type="text", text="Sure thing! Here is your ping reply.")]
    with patch.object(p.client.messages, "create", return_value=fake_resp):
        result = p.test_connection()

    assert result.ok is False
    assert result.category == "json_format"
    assert result.http_status == 200
    assert result.raw_response is not None
    assert "Sure thing" in result.raw_response


def test_anthropic_test_connection_auth_error():
    from mockinterview.agent.providers.anthropic import AnthropicProvider

    p = AnthropicProvider(api_key="sk-bad", model="claude-opus-4-7")
    auth_exc = _err_with(status=401, message="invalid API key")
    with patch.object(p.client.messages, "create", side_effect=auth_exc):
        result = p.test_connection()

    assert result.ok is False
    assert result.category == "auth"
    assert result.http_status == 401
    assert result.provider_message is not None
    assert "invalid API key" in result.provider_message


def test_anthropic_test_connection_rate_limit():
    from mockinterview.agent.providers.anthropic import AnthropicProvider

    p = AnthropicProvider(api_key="sk-test", model="claude-opus-4-7")
    rate_exc = _err_with(status=429, message="rate limited; retry after 60s")
    with patch.object(p.client.messages, "create", side_effect=rate_exc):
        result = p.test_connection()

    assert result.ok is False
    assert result.category == "rate_limit"
    assert result.http_status == 429


def test_openai_compat_test_connection_ok():
    from mockinterview.agent.providers.openai_compat import OpenAICompatibleProvider

    p = OpenAICompatibleProvider(api_key="sk-test", model="gpt-4-turbo")
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock(message=MagicMock(content='{"ok": true, "echo": "ping"}'))]
    with patch.object(p.client.chat.completions, "create", return_value=fake_resp):
        result = p.test_connection()

    assert result.ok is True
    assert result.category == "ok"


def test_openai_compat_test_connection_falls_back_when_response_format_rejected():
    """If response_format=json_object is rejected (e.g. older OpenAI-compat),
    we retry without it. This must not surface as an error."""
    from mockinterview.agent.providers.openai_compat import OpenAICompatibleProvider

    p = OpenAICompatibleProvider(api_key="sk-test", model="m")
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock(message=MagicMock(content='{"ok": true, "echo": "ping"}'))]

    call_count = {"n": 0}

    def fake_create(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1 and "response_format" in kwargs:
            # response_format unsupported — but NOT an auth/rate/network error
            raise RuntimeError("response_format not supported by this model")
        return fake_resp

    with patch.object(p.client.chat.completions, "create", side_effect=fake_create):
        result = p.test_connection()

    assert result.ok is True
    assert call_count["n"] == 2


def test_openai_compat_test_connection_does_not_retry_on_auth_error():
    """When the first call fails with 401, we should categorize as auth, not retry
    the fallback. (Otherwise we'd waste a second token allocation on a known-dead key.)"""
    from mockinterview.agent.providers.openai_compat import OpenAICompatibleProvider

    p = OpenAICompatibleProvider(api_key="sk-bad", model="m")
    auth_exc = _err_with(status=401, message="invalid key")

    call_count = {"n": 0}

    def fake_create(**kwargs):
        call_count["n"] += 1
        raise auth_exc

    with patch.object(p.client.chat.completions, "create", side_effect=fake_create):
        result = p.test_connection()

    assert result.ok is False
    assert result.category == "auth"
    assert call_count["n"] == 1, "should not retry fallback on auth error"


def test_gemini_test_connection_ok():
    from mockinterview.agent.providers.gemini import GeminiProvider

    p = GeminiProvider(api_key="sk-test", model="gemini-2.0-flash-exp")
    fake_resp = MagicMock()
    fake_resp.text = '{"ok": true, "echo": "ping"}'
    with patch.object(p.client.models, "generate_content", return_value=fake_resp):
        result = p.test_connection()

    assert result.ok is True
    assert result.category == "ok"


def test_gemini_test_connection_network_error():
    from mockinterview.agent.providers.gemini import GeminiProvider

    p = GeminiProvider(api_key="sk-test", model="gemini-2.0-flash-exp")

    class APIConnectionError(Exception):
        pass

    with patch.object(
        p.client.models, "generate_content", side_effect=APIConnectionError("connection refused")
    ):
        result = p.test_connection()

    assert result.ok is False
    assert result.category == "network"


# ---------- route integration test ----------


def test_provider_test_route_returns_structured_result():
    """End-to-end: POST /provider/test passes through use_provider Depends and
    returns whatever the active provider's test_connection() yields."""
    from fastapi.testclient import TestClient

    from mockinterview.agent.providers import set_active
    from mockinterview.main import app
    from mockinterview.routes._deps import use_provider
    from mockinterview.schemas.provider import ProviderTestResult

    fake_provider = MagicMock()
    fake_provider.test_connection.return_value = ProviderTestResult(
        ok=False,
        category="json_format",
        http_status=200,
        provider_message=None,
        raw_response="not json",
        elapsed_ms=42,
    )

    async def _override() -> None:
        set_active(fake_provider)

    app.dependency_overrides[use_provider] = _override
    try:
        with TestClient(app) as client:
            r = client.post(
                "/provider/test",
                headers={"X-Provider": "anthropic", "X-API-Key": "sk-fake"},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is False
        assert body["category"] == "json_format"
        assert body["http_status"] == 200
        assert body["raw_response"] == "not json"
        assert body["elapsed_ms"] == 42
    finally:
        app.dependency_overrides.clear()


def test_provider_test_route_rejects_missing_api_key():
    """The use_provider Depends raises 401 when X-API-Key is missing.
    /provider/test should not bypass that gate."""
    from fastapi.testclient import TestClient

    from mockinterview.main import app

    with TestClient(app) as client:
        r = client.post("/provider/test")
    assert r.status_code == 401


# ---------- optional: real-LLM happy path ----------


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="No ANTHROPIC_API_KEY in env — skipping real LLM happy path",
)
def test_anthropic_real_key_happy_path():
    """When ANTHROPIC_API_KEY is set in env, validate the prompt design actually
    produces parseable JSON from a real Claude call. This is the only test that
    spends real tokens; default CI runs without ANTHROPIC_API_KEY skip it."""
    from mockinterview.agent.providers.anthropic import AnthropicProvider

    p = AnthropicProvider(
        api_key=os.environ["ANTHROPIC_API_KEY"],
        model="claude-haiku-4-5-20251001",  # cheapest haiku for the smoke
    )
    result = p.test_connection()
    assert result.ok is True, f"real LLM connection test failed: {result}"
    assert result.category == "ok"
    assert result.http_status == 200
