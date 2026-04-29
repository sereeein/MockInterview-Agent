from time import perf_counter
from typing import Any

from google import genai
from google.genai import types

from mockinterview.agent.providers.base import LLMProvider
from mockinterview.agent.providers.test_support import (
    TEST_MAX_TOKENS,
    TEST_SYSTEM,
    TEST_USER,
    categorize_error,
    validate_json_response,
)
from mockinterview.schemas.provider import ProviderTestResult


class GeminiProvider(LLMProvider):
    """Google Gemini via the google-genai SDK."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def call_json(self, system, messages, max_tokens=4096):
        # Gemini wants conversation history shape {"role": "user"|"model", "parts": [...]}
        contents: list[dict[str, Any]] = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})

        resp = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                response_mime_type="application/json",
            ),
        )
        text = resp.text or ""
        from mockinterview.agent.client import parse_json_response

        return parse_json_response(text)

    def test_connection(self) -> ProviderTestResult:
        t0 = perf_counter()
        try:
            resp = self.client.models.generate_content(
                model=self.model,
                contents=[{"role": "user", "parts": [{"text": TEST_USER}]}],
                config=types.GenerateContentConfig(
                    system_instruction=TEST_SYSTEM,
                    max_output_tokens=TEST_MAX_TOKENS,
                    response_mime_type="application/json",
                    temperature=0,
                ),
            )
            text = resp.text or ""
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
