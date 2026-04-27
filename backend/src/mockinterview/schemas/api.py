from datetime import datetime

from pydantic import BaseModel

from mockinterview.db.models import QuestionStatus


class QuestionRead(BaseModel):
    id: int
    resume_session_id: int
    category: str
    text: str
    source: str
    difficulty: str
    status: QuestionStatus
    best_score: int | None
    last_attempt_at: datetime | None
    created_at: datetime


class GenerateRequest(BaseModel):
    resume_session_id: int


class QuestionStatusUpdate(BaseModel):
    status: QuestionStatus
