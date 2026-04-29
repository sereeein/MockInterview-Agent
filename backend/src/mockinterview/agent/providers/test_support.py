"""Shared helpers for LLMProvider.test_connection() implementations.

Each provider implements test_connection() independently of call_json() to
guarantee max_tokens=30 and prompt determinism, but they all use the same
prompt + the same error categorization rules below.
"""

import json

TEST_SYSTEM = (
    "You are a connection test endpoint. "
    'Reply ONLY with valid JSON: {"ok": true, "echo": "<the user message verbatim>"}. '
    "No prose, no markdown, no code fence."
)
TEST_USER = "ping"
TEST_MAX_TOKENS = 30


def categorize_error(exc: Exception) -> tuple[str, int | None]:
    """Map a provider SDK exception to (category, http_status).

    Categories: "auth" | "rate_limit" | "network" | "unknown"

    Probes (in order):
      1. exc.status_code (Anthropic/OpenAI APIStatusError)
      2. exc.code (google-genai APIError)
      3. exc.response.status_code
      4. class name match (AuthenticationError, RateLimitError, ...)
      5. message string match (timeout, connection)
    """
    status: int | None = None
    raw_status = getattr(exc, "status_code", None)
    if isinstance(raw_status, int):
        status = raw_status
    if status is None:
        raw_code = getattr(exc, "code", None)
        if isinstance(raw_code, int):
            status = raw_code
    if status is None:
        resp = getattr(exc, "response", None)
        if resp is not None:
            rs = getattr(resp, "status_code", None)
            if isinstance(rs, int):
                status = rs

    cls_name = type(exc).__name__.lower()
    msg = str(exc).lower()

    # Auth
    if status in (401, 403):
        return ("auth", status)
    if "authentication" in cls_name or "permissiondenied" in cls_name:
        return ("auth", status)

    # Rate limit
    if status == 429:
        return ("rate_limit", 429)
    if "ratelimit" in cls_name:
        return ("rate_limit", status or 429)

    # Network: timeouts, connection errors, 5xx
    if "connection" in cls_name or "timeout" in cls_name:
        return ("network", status)
    if status is not None and 500 <= status < 600:
        return ("network", status)
    if any(s in msg for s in ("timeout", "timed out", "could not connect", "name resolution", "connection refused")):
        return ("network", status)

    # Other 4xx → unknown
    if status is not None and 400 <= status < 500:
        return ("unknown", status)

    return ("unknown", status)


def validate_json_response(text: str) -> tuple[bool, str | None]:
    """Validate that the LLM's response text is valid JSON with {"ok": true, ...}.

    Returns (ok, raw_excerpt). raw_excerpt is the first 500 chars of text on
    failure (so the frontend can show what the model actually said), None on
    success.
    """
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return (False, text[:500] if text else "")
    if not isinstance(parsed, dict):
        return (False, text[:500] if text else "")
    if parsed.get("ok") is not True:
        return (False, text[:500] if text else "")
    return (True, None)
