from typing import Any

from google import genai
from google.genai import types

from mockinterview.agent.providers.base import LLMProvider


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
