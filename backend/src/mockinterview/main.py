from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app.include_router(resume_routes.router)
app.include_router(questions_routes.router)
app.include_router(drill_routes.router)
app.include_router(reports_routes.router)
app.include_router(mock_routes.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
