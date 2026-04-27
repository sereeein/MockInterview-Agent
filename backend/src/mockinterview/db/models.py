from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import Column, JSON
from sqlmodel import Field, Relationship, SQLModel


class QuestionStatus(str, Enum):
    NOT_PRACTICED = "not_practiced"
    PRACTICED = "practiced"
    NEEDS_REDO = "needs_redo"
    IMPROVED = "improved"
    SKIPPED = "skipped"


class ExitType(str, Enum):
    SOFT = "soft"
    HARD_LIMIT = "hard_limit"
    USER_END = "user_end"
    SKIP = "skip"


class ResumeSession(SQLModel, table=True):
    __tablename__ = "resume_session"
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(default=1, index=True)
    resume_json: dict[str, Any] = Field(sa_column=Column(JSON))
    jd_text: str | None = None
    company_name: str | None = None
    role_type: str = Field(index=True)  # pm / data / ai / other
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    questions: list["Question"] = Relationship(back_populates="session")
    reports: list["Report"] = Relationship(back_populates="session")


class Question(SQLModel, table=True):
    __tablename__ = "question"
    id: int | None = Field(default=None, primary_key=True)
    resume_session_id: int = Field(foreign_key="resume_session.id", index=True)
    category: str  # T1..T5
    text: str
    source: str
    difficulty: str  # easy/medium/hard
    status: QuestionStatus = Field(default=QuestionStatus.NOT_PRACTICED, index=True)
    best_score: int | None = None
    last_attempt_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    session: ResumeSession | None = Relationship(back_populates="questions")
    attempts: list["DrillAttempt"] = Relationship(back_populates="question")


class DrillAttempt(SQLModel, table=True):
    __tablename__ = "drill_attempt"
    id: int | None = Field(default=None, primary_key=True)
    question_id: int = Field(foreign_key="question.id", index=True)
    transcript_json: list[dict[str, Any]] = Field(sa_column=Column(JSON))
    rubric_scores_json: dict[str, int] = Field(sa_column=Column(JSON))
    total_score: int
    exit_type: ExitType
    scenario_switch_count: int = 0
    prompt_mode_count: int = 0
    followup_rounds: int = 0
    exemplar_answer: str
    improvement_suggestions: list[str] = Field(sa_column=Column(JSON))
    state_snapshot: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None

    question: Question | None = Relationship(back_populates="attempts")


class Report(SQLModel, table=True):
    __tablename__ = "report"
    id: int | None = Field(default=None, primary_key=True)
    resume_session_id: int = Field(foreign_key="resume_session.id", index=True)
    drill_attempt_ids: list[int] = Field(sa_column=Column(JSON))
    total_avg_score: float
    category_avg_scores: dict[str, float] = Field(sa_column=Column(JSON))
    highlights: list[dict[str, Any]] = Field(sa_column=Column(JSON))
    weaknesses: list[dict[str, Any]] = Field(sa_column=Column(JSON))
    next_steps: list[str] = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    session: ResumeSession | None = Relationship(back_populates="reports")
