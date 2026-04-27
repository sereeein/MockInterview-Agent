from typing import Any

from anthropic import Anthropic

from mockinterview.agent.providers.base import LLMProvider


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
