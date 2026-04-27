from typing import Any

from openai import OpenAI

from mockinterview.agent.providers.base import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI-compatible HTTP API. Works with OpenAI itself and many other providers
    that ship an OpenAI-compatible mode: DeepSeek, 千问/通义 (DashScope), 智谱 (BigModel),
    Kimi (Moonshot), 文心 (Qianfan v2), 豆包 (Volcano Ark), and others.
    Each picks a different `base_url`."""

    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        self.client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
        self.model = model

    def call_json(self, system, messages, max_tokens=4096):
        oai_messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
        for m in messages:
            oai_messages.append({"role": m["role"], "content": m["content"]})

        # Try response_format=json_object for OpenAI-compat providers that support it.
        # Many do (OpenAI, DeepSeek, 智谱, Kimi). Some don't — fall back to plain mode.
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=oai_messages,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        except Exception:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=oai_messages,
                max_tokens=max_tokens,
            )

        text = resp.choices[0].message.content or ""
        from mockinterview.agent.client import parse_json_response

        return parse_json_response(text)
