from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from mockinterview.agent.question_gen import generate_questions
from mockinterview.db.models import Question, QuestionStatus, ResumeSession
from mockinterview.db.session import get_session
from mockinterview.routes._deps import use_provider
from mockinterview.schemas.api import GenerateRequest, QuestionRead, QuestionStatusUpdate

router = APIRouter(prefix="/questions", tags=["questions"])


@router.post("/generate", response_model=list[QuestionRead])
def generate(
    req: GenerateRequest,
    db: Session = Depends(get_session),
    _: None = Depends(use_provider),
):
    rs = db.get(ResumeSession, req.resume_session_id)
    if not rs:
        raise HTTPException(404, "resume_session not found")
    qlist = generate_questions(
        role=rs.role_type,
        resume_json=rs.resume_json,
        jd_text=rs.jd_text,
        company_name=rs.company_name,
    )
    if not qlist.questions:
        raise HTTPException(502, "agent returned no questions; try again")
    rows: list[Question] = []
    for gq in qlist.questions:
        q = Question(
            resume_session_id=rs.id,
            category=gq.category,
            text=gq.text,
            source=gq.source,
            difficulty=gq.difficulty,
        )
        db.add(q)
        rows.append(q)
    db.commit()
    for q in rows:
        db.refresh(q)
    return rows


@router.get("", response_model=list[QuestionRead])
def list_questions(
    resume_session_id: int,
    category: str | None = None,
    status: QuestionStatus | None = None,
    db: Session = Depends(get_session),
):
    stmt = select(Question).where(Question.resume_session_id == resume_session_id)
    if category:
        stmt = stmt.where(Question.category == category)
    if status:
        stmt = stmt.where(Question.status == status)
    return db.exec(stmt).all()


@router.get("/{question_id}", response_model=QuestionRead)
def get_question(question_id: int, db: Session = Depends(get_session)):
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(404, "not found")
    return q


@router.patch("/{question_id}/status", response_model=QuestionRead)
def patch_status(
    question_id: int,
    body: QuestionStatusUpdate,
    db: Session = Depends(get_session),
):
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(404, "not found")
    q.status = body.status
    db.add(q)
    db.commit()
    db.refresh(q)
    return q
