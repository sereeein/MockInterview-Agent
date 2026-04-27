from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from mockinterview.agent.mock_aggregator import aggregate_mock
from mockinterview.db.models import (
    DrillAttempt,
    MockSession,
    Question,
    ResumeSession,
)
from mockinterview.db.session import get_session

router = APIRouter(prefix="/mock", tags=["mock"])

MOCK_SIZE = 5


class StartBody(BaseModel):
    resume_session_id: int


@router.post("")
def start_mock(body: StartBody, db: Session = Depends(get_session)):
    rs = db.get(ResumeSession, body.resume_session_id)
    if not rs:
        raise HTTPException(404, "resume_session not found")
    qs = db.exec(
        select(Question).where(Question.resume_session_id == rs.id).order_by(
            Question.status, Question.id
        )
    ).all()
    chosen: list[Question] = []
    seen_cats: set[str] = set()
    for q in qs:
        if len(chosen) >= MOCK_SIZE:
            break
        if q.category not in seen_cats:
            chosen.append(q)
            seen_cats.add(q.category)
    while len(chosen) < MOCK_SIZE and len(chosen) < len(qs):
        for q in qs:
            if q not in chosen:
                chosen.append(q)
                if len(chosen) == MOCK_SIZE:
                    break
    ms = MockSession(
        resume_session_id=rs.id,
        question_ids=[q.id for q in chosen],
    )
    db.add(ms)
    db.commit()
    db.refresh(ms)
    return ms


@router.get("/{mock_id}")
def get_mock(mock_id: int, db: Session = Depends(get_session)):
    ms = db.get(MockSession, mock_id)
    if not ms:
        raise HTTPException(404, "not found")
    return ms


class AdvanceBody(BaseModel):
    drill_attempt_id: int


@router.post("/{mock_id}/advance")
def advance_mock(mock_id: int, body: AdvanceBody, db: Session = Depends(get_session)):
    ms = db.get(MockSession, mock_id)
    if not ms:
        raise HTTPException(404, "not found")
    if ms.status == "ended":
        return ms
    d = db.get(DrillAttempt, body.drill_attempt_id)
    if not d:
        raise HTTPException(404, "drill_attempt not found")
    if body.drill_attempt_id not in ms.drill_attempt_ids:
        ms.drill_attempt_ids = ms.drill_attempt_ids + [body.drill_attempt_id]
    ms.current_index = ms.current_index + 1
    if ms.current_index >= len(ms.question_ids):
        ms.status = "ended"
        ms.ended_at = datetime.now(timezone.utc)
    db.add(ms)
    db.commit()
    db.refresh(ms)
    return ms


@router.get("/{mock_id}/report")
def mock_report(mock_id: int, db: Session = Depends(get_session)):
    ms = db.get(MockSession, mock_id)
    if not ms:
        raise HTTPException(404, "not found")
    return aggregate_mock(db, mock_id)
