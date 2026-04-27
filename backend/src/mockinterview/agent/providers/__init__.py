from contextvars import ContextVar
from typing import Any, Optional

from mockinterview.agent.providers.base import LLMProvider

# Preset configs: kind drives which Provider class, default_model + base_url are starting points.
PROVIDER_PRESETS: dict[str, dict[str, Any]] = {
    "anthropic": {"kind": "anthropic", "default_model": "claude-opus-4-7", "base_url": None},
    "openai":    {"kind": "openai",    "default_model": "gpt-4-turbo",     "base_url": None},
    "deepseek":  {"kind": "openai",    "default_model": "deepseek-chat",   "base_url": "https://api.deepseek.com/v1"},
    "qwen":      {"kind": "openai",    "default_model": "qwen-max",        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    "zhipu":     {"kind": "openai",    "default_model": "glm-4-plus",      "base_url": "https://open.bigmodel.cn/api/paas/v4"},
    "kimi":      {"kind": "openai",    "default_model": "moonshot-v1-32k", "base_url": "https://api.moonshot.cn/v1"},
    "wenxin":    {"kind": "openai",    "default_model": "ernie-4.0-turbo-8k", "base_url": "https://qianfan.baidubce.com/v2"},
    "doubao":    {"kind": "openai",    "default_model": "doubao-pro-32k",  "base_url": "https://ark.cn-beijing.volces.com/api/v3"},
    "gemini":    {"kind": "gemini",    "default_model": "gemini-2.0-flash-exp", "base_url": None},
    "custom":    {"kind": "openai",    "default_model": "",                "base_url": ""},
}

_active: ContextVar[Optional[LLMProvider]] = ContextVar("active_provider", default=None)


def make_provider(
    *,
    provider: str,
    api_key: str,
    model: str | None = None,
    base_url: str | None = None,
) -> LLMProvider:
    preset = PROVIDER_PRESETS.get(provider)
    if not preset:
        raise ValueError(
            f"Unknown provider: {provider!r}. Available: {list(PROVIDER_PRESETS.keys())}"
        )
    if not api_key:
        raise ValueError("api_key is required")

    actual_model = model or preset["default_model"]
    actual_base_url = base_url or preset["base_url"]

    kind = preset["kind"]
    if kind == "anthropic":
        from mockinterview.agent.providers.anthropic import AnthropicProvider

        return AnthropicProvider(api_key=api_key, model=actual_model)
    elif kind == "openai":
        from mockinterview.agent.providers.openai_compat import OpenAICompatibleProvider

        return OpenAICompatibleProvider(
            api_key=api_key, model=actual_model, base_url=actual_base_url
        )
    elif kind == "gemini":
        from mockinterview.agent.providers.gemini import GeminiProvider

        return GeminiProvider(api_key=api_key, model=actual_model)
    raise ValueError(f"Unknown provider kind: {kind}")


def set_active(provider: LLMProvider) -> None:
    _active.set(provider)


def active() -> LLMProvider:
    p = _active.get()
    if p is None:
        raise RuntimeError(
            "No active LLMProvider in this request context. "
            "A FastAPI dependency must call set_active() before agent code runs."
        )
    return p


def reset_active() -> None:
    _active.set(None)
