from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mockinterview.config import get_settings
from mockinterview.db.session import init_db
from mockinterview.routes import drill as drill_routes
from mockinterview.routes import mock as mock_routes
from mockinterview.routes import questions as questions_routes
from mockinterview.routes import reports as reports_routes
from mockinterview.routes import resume as resume_routes


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


settings = get_settings()
app = FastAPI(title="MockInterview Agent", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled exceptions BEFORE they reach Starlette's ServerErrorMiddleware
    (which sits outside CORSMiddleware and would emit a 500 with no CORS headers).
    Returning a JSONResponse here keeps the response inside the middleware chain
    so CORS headers are correctly applied even on errors.

    Specifically tags upstream LLM-provider errors (openai / anthropic / google) as
    502 with a translated message, since those mean the user's chosen provider/model
    is misconfigured rather than a server bug.
    """
    err_type = type(exc).__name__
    err_module = type(exc).__module__
    msg = str(exc)
    if any(s in err_module for s in ("openai", "anthropic", "google")):
        return JSONResponse(
            status_code=502,
            content={
                "detail": f"上游 LLM provider 错误（{err_type}）：{msg}",
                "hint": "通常是 model 名或 base_url 不匹配 provider 的可用渠道。检查 /setup 页配置。",
            },
        )
    return JSONResponse(
        status_code=500,
        content={"detail": f"{err_type}: {msg}"},
    )

app.include_router(resume_routes.router)
app.include_router(questions_routes.router)
app.include_router(drill_routes.router)
app.include_router(reports_routes.router)
app.include_router(mock_routes.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
