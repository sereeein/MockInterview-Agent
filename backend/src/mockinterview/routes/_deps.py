from fastapi import Header, HTTPException

from mockinterview.agent.providers import make_provider, set_active


async def use_provider(
    x_provider: str = Header(default="anthropic", alias="X-Provider"),
    x_api_key: str = Header(default="", alias="X-API-Key"),
    x_model: str | None = Header(default=None, alias="X-Model"),
    x_base_url: str | None = Header(default=None, alias="X-Base-URL"),
) -> None:
    """Per-request dependency that constructs an LLM provider from headers
    and sets it as the active provider for the call stack.

    MUST be `async` so it runs on the main event loop task (not a threadpool worker).
    ContextVar.set() in a sync dep + sync handler results in two separate threadpool
    tasks that don't share the var. Async dep + sync handler is fine because anyio
    propagates the dep's context into the handler's threadpool via `context.run()`.

    Headers:
      X-Provider: one of anthropic / openai / deepseek / qwen / zhipu / kimi / wenxin / doubao / gemini / custom
      X-API-Key: required, the user's own API key for that provider
      X-Model: optional, override the preset default model
      X-Base-URL: optional, only used when X-Provider=custom (or to override OpenAI-compat base_url)
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="missing X-API-Key header. The frontend must collect the user's own API key and forward it.",
        )
    try:
        p = make_provider(
            provider=x_provider,
            api_key=x_api_key,
            model=x_model,
            base_url=x_base_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    set_active(p)
