from time import perf_counter
from typing import Any

from openai import OpenAI

from mockinterview.agent.providers.base import LLMProvider
from mockinterview.agent.providers.test_support import (
    TEST_MAX_TOKENS,
    TEST_SYSTEM,
    TEST_USER,
    categorize_error,
    validate_json_response,
)
from mockinterview.schemas.provider import ProviderTestResult


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

    def test_connection(self) -> ProviderTestResult:
        t0 = perf_counter()
        messages = [
            {"role": "system", "content": TEST_SYSTEM},
            {"role": "user", "content": TEST_USER},
        ]
        try:
            # Try response_format=json_object first; many OpenAI-compat providers
            # support it and it makes the JSON output more reliable. Fall back to
            # plain mode if rejected — same approach as call_json.
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=TEST_MAX_TOKENS,
                    temperature=0,
                    response_format={"type": "json_object"},
                )
            except Exception as inner:
                # Only fall back when response_format is the cause; auth/network/rate
                # errors should propagate so we categorize them, not silently retry.
                inner_msg = str(inner).lower()
                if (
                    getattr(inner, "status_code", None) in (401, 403, 429)
                    or "authentication" in type(inner).__name__.lower()
                    or "ratelimit" in type(inner).__name__.lower()
                    or "connection" in type(inner).__name__.lower()
                    or "timeout" in inner_msg
                ):
                    raise
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=TEST_MAX_TOKENS,
                    temperature=0,
                )

            text = (resp.choices[0].message.content or "") if resp.choices else ""
            elapsed = int((perf_counter() - t0) * 1000)
            ok, excerpt = validate_json_response(text)
            if ok:
                return ProviderTestResult(
                    ok=True,
                    category="ok",
                    http_status=200,
                    provider_message=None,
                    raw_response=None,
                    elapsed_ms=elapsed,
                )
            return ProviderTestResult(
                ok=False,
                category="json_format",
                http_status=200,
                provider_message=None,
                raw_response=excerpt,
                elapsed_ms=elapsed,
            )
        except Exception as exc:
            elapsed = int((perf_counter() - t0) * 1000)
            category, status = categorize_error(exc)
            return ProviderTestResult(
                ok=False,
                category=category,  # type: ignore[arg-type]
                http_status=status,
                provider_message=str(exc)[:500],
                raw_response=None,
                elapsed_ms=elapsed,
            )
