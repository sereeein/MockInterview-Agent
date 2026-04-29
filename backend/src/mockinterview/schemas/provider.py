from typing import Literal

from pydantic import BaseModel


TestCategory = Literal["ok", "network", "auth", "rate_limit", "json_format", "unknown"]


class ProviderTestResult(BaseModel):
    """Result of a connection test for the active LLM provider.

    Returned by POST /provider/test. Each category lets the frontend render a
    targeted error message + action hint without parsing free-form strings.
    """

    ok: bool
    category: TestCategory
    http_status: int | None = None
    provider_message: str | None = None
    raw_response: str | None = None
    elapsed_ms: int
