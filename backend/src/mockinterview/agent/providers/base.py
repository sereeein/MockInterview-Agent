from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract interface for any LLM provider that can answer with structured JSON."""

    @abstractmethod
    def call_json(
        self,
        system: str,
        messages: list[dict[str, Any]],
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Send a system + messages prompt; return parsed JSON dict.

        Each provider handles its own caching / output format / SDK-specific shape.
        Caller passes a plain string for `system` (NOT the Anthropic block list).
        """
        ...
