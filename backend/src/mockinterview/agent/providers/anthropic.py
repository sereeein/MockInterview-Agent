from time import perf_counter
from typing import Any

from anthropic import Anthropic

from mockinterview.agent.providers.base import LLMProvider
from mockinterview.agent.providers.test_support import (
    TEST_MAX_TOKENS,
    TEST_SYSTEM,
    TEST_USER,
    categorize_error,
    validate_json_response,
)
from mockinterview.schemas.provider import ProviderTestResult


class AnthropicProvider(LLMProvider):
    """Native Anthropic SDK with prompt caching via cache_control."""

    def __init__(self, api_key: str, model: str = "claude-opus-4-7"):
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def call_json(self, system, messages, max_tokens=4096):
        # Anthropic-specific: wrap system in a single text block w/ ephemeral cache
        system_blocks = [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
        ]
        resp = self.client.messages.create(
            model=self.model,
            system=system_blocks,
            messages=messages,
            max_tokens=max_tokens,
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        from mockinterview.agent.client import parse_json_response

        return parse_json_response(text)

    def test_connection(self) -> ProviderTestResult:
        t0 = perf_counter()
        try:
            resp = self.client.messages.create(
                model=self.model,
                system=TEST_SYSTEM,
                messages=[{"role": "user", "content": TEST_USER}],
                max_tokens=TEST_MAX_TOKENS,
                temperature=0,
            )
            text = "".join(
                b.text for b in resp.content if getattr(b, "type", None) == "text"
            )
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
