from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mockinterview.config import get_settings
from mockinterview.db.session import init_db
from mockinterview.routes import drill as drill_routes
from mockinterview.routes import mock as mock_routes
from mockinterview.routes import provider as provider_routes
from mockinterview.routes import questions as questions_routes
from mockinterview.routes import reports as reports_routes
from mockinterview.routes import resume as resume_routes


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


settings = get_settings()
app = FastAPI(title="MockInterview Agent", version="0.1.0", lifespan=lifespan)


# Register the catch-all error middleware FIRST (becomes inner layer), then CORS.
# With Starlette's add_middleware semantics (last-added = outermost), this gives:
#   request → CORS → catch_all → router → handler
#   response: handler → router → catch_all (turns exception into JSONResponse)
#                                           → CORS (writes Access-Control-* headers)
# An @app.exception_handler(Exception) decorator does NOT reliably catch arbitrary
# exceptions because FastAPI's ExceptionMiddleware default handlers only include
# HTTPException — generic Exception bubbles past it to ServerErrorMiddleware which
# sits OUTSIDE CORS, producing the "fail to fetch / blocked by CORS" symptom on 500.

@app.middleware("http")
async def catch_all_errors(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        err_type = type(exc).__name__
        err_module = type(exc).__module__
        msg = str(exc)
        if any(s in err_module for s in ("openai", "anthropic", "google")):
            return JSONResponse(
                status_code=502,
                content={
                    "detail": f"上游 LLM provider 错误（{err_type}）：{msg}",
                    "hint": "通常是 model 名或 base_url 不匹配 provider 的可用渠道，或模型输出不是合法 JSON。检查 /setup 页配置。",
                },
            )
        if err_type == "JSONDecodeError":
            return JSONResponse(
                status_code=502,
                content={
                    "detail": f"模型输出不是合法 JSON：{msg}",
                    "hint": "你选的 model 可能不严格遵守 JSON 输出指令。换更强的 model（如 claude-3-5-sonnet / gpt-4-turbo / qwen-max）通常能修。",
                },
            )
        return JSONResponse(
            status_code=500,
            content={"detail": f"{err_type}: {msg}"},
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume_routes.router)
app.include_router(questions_routes.router)
app.include_router(drill_routes.router)
app.include_router(reports_routes.router)
app.include_router(mock_routes.router)
app.include_router(provider_routes.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
