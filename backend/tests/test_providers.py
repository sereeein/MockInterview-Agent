from unittest.mock import MagicMock, patch

import pytest

from mockinterview.agent.providers import (
    PROVIDER_PRESETS,
    active,
    make_provider,
    reset_active,
    set_active,
)
from mockinterview.agent.providers.anthropic import AnthropicProvider
from mockinterview.agent.providers.gemini import GeminiProvider
from mockinterview.agent.providers.openai_compat import OpenAICompatibleProvider


def test_presets_have_known_providers():
    expected = {"anthropic", "openai", "deepseek", "qwen", "zhipu", "kimi", "wenxin", "doubao", "gemini", "custom"}
    assert set(PROVIDER_PRESETS.keys()) == expected


def test_make_provider_anthropic():
    p = make_provider(provider="anthropic", api_key="sk-test")
    assert isinstance(p, AnthropicProvider)


def test_make_provider_deepseek_uses_openai_compat_with_base_url():
    p = make_provider(provider="deepseek", api_key="sk-test")
    assert isinstance(p, OpenAICompatibleProvider)
    assert p.client.base_url is not None
    assert "deepseek" in str(p.client.base_url)


def test_make_provider_gemini():
    p = make_provider(provider="gemini", api_key="sk-test")
    assert isinstance(p, GeminiProvider)


def test_make_provider_unknown_raises():
    with pytest.raises(ValueError, match="Unknown provider"):
        make_provider(provider="bogus", api_key="sk-test")


def test_make_provider_blank_key_raises():
    with pytest.raises(ValueError, match="api_key is required"):
        make_provider(provider="anthropic", api_key="")


def test_make_provider_custom_model_overrides_default():
    p = make_provider(provider="anthropic", api_key="sk-test", model="claude-haiku-4-5-20251001")
    assert p.model == "claude-haiku-4-5-20251001"


def test_make_provider_custom_base_url_overrides_default():
    p = make_provider(provider="custom", api_key="sk-test", model="my-model", base_url="https://my.api/v1")
    assert isinstance(p, OpenAICompatibleProvider)


def test_set_and_get_active_provider():
    reset_active()
    with pytest.raises(RuntimeError, match="No active LLMProvider"):
        active()

    fake = MagicMock()
    set_active(fake)
    assert active() is fake
    reset_active()


def test_anthropic_provider_call_json_invokes_sdk_with_cache_control():
    p = AnthropicProvider(api_key="sk-test", model="claude-opus-4-7")
    fake_resp = MagicMock()
    fake_resp.content = [MagicMock(type="text", text='```json\n{"x": 1}\n```')]
    with patch.object(p.client.messages, "create", return_value=fake_resp) as m:
        out = p.call_json(system="sys", messages=[{"role": "user", "content": "u"}])
    assert out == {"x": 1}
    args = m.call_args.kwargs
    assert args["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert args["model"] == "claude-opus-4-7"


def test_openai_compat_provider_call_json_falls_back_when_response_format_rejected():
    p = OpenAICompatibleProvider(api_key="sk-test", model="m", base_url="https://x/v1")
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock(message=MagicMock(content='{"y": 2}'))]

    call_count = {"n": 0}

    def fake_create(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1 and "response_format" in kwargs:
            raise RuntimeError("provider doesn't support response_format")
        return fake_resp

    with patch.object(p.client.chat.completions, "create", side_effect=fake_create):
        out = p.call_json(system="sys", messages=[{"role": "user", "content": "u"}])
    assert out == {"y": 2}
    assert call_count["n"] == 2  # tried response_format, then plain
