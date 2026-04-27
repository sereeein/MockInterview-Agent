from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from mockinterview.agent.drill_loop import DrillStatus, advance, start_drill
from mockinterview.agent.drill_storage import from_snapshot, to_snapshot
from mockinterview.agent.exemplar import synthesize_exemplar
from mockinterview.db.models import DrillAttempt, Question, QuestionStatus, ResumeSession
from mockinterview.db.session import get_session

router = APIRouter(prefix="/drill", tags=["drill"])


class StartDrillBody(BaseModel):
    question_id: int


class AnswerBody(BaseModel):
    text: str


class DrillResponse(BaseModel):
    drill_id: int
    status: str
    transcript: list[dict]
    last_agent_text: str
    exit_type: str | None
    rubric_scores: dict[str, int] | None
    total_score: int | None


def _serialize(d: DrillAttempt) -> DrillResponse:
    snap = d.state_snapshot or {}
    transcript = snap.get("transcript", [])
    last_agent = next(
        (t["text"] for t in reversed(transcript) if t["role"] == "agent"),
        "",
    )
    last_eval = snap.get("last_eval")
    return DrillResponse(
        drill_id=d.id,
        status=snap.get("status", "active"),
        transcript=transcript,
        last_agent_text=last_agent,
        exit_type=snap.get("exit_type"),
        rubric_scores=last_eval["scores"] if last_eval else None,
        total_score=last_eval["total_score"] if last_eval else None,
    )


@router.post("", response_model=DrillResponse)
def start(body: StartDrillBody, db: Session = Depends(get_session)):
    q = db.get(Question, body.question_id)
    if not q:
        raise HTTPException(404, "question not found")
    rs = db.get(ResumeSession, q.resume_session_id)
    if not rs:
        raise HTTPException(404, "resume_session not found")
    state = start_drill(
        question_id=q.id,
        question_text=q.text,
        category=q.category,
        resume_json=rs.resume_json,
        original_intent=q.source,
    )
    d = DrillAttempt(
        question_id=q.id,
        transcript_json=[t.model_dump() for t in state.transcript],
        rubric_scores_json={},
        total_score=0,
        exit_type="soft",  # placeholder, overwritten on end
        scenario_switch_count=0,
        prompt_mode_count=0,
        followup_rounds=0,
        exemplar_answer="",
        improvement_suggestions=[],
        state_snapshot=to_snapshot(state),
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return _serialize(d)


@router.post("/{drill_id}/answer", response_model=DrillResponse)
def answer(drill_id: int, body: AnswerBody, db: Session = Depends(get_session)):
    d = db.get(DrillAttempt, drill_id)
    if not d:
        raise HTTPException(404, "drill not found")
    if not d.state_snapshot:
        raise HTTPException(400, "drill has no state")
    state = from_snapshot(d.state_snapshot)
    state = advance(state, body.text)

    d.state_snapshot = to_snapshot(state)
    d.transcript_json = [t.model_dump() for t in state.transcript]
    d.followup_rounds = state.followup_rounds
    d.scenario_switch_count = state.scenario_switch_count
    d.prompt_mode_count = state.prompt_mode_count

    if state.status == DrillStatus.ENDED:
        # finalize
        scores = state.last_eval.scores if state.last_eval else {}
        total = state.last_eval.total_score if state.last_eval else 0
        d.rubric_scores_json = scores
        d.total_score = total
        d.exit_type = state.exit_type or "user_end"
        d.ended_at = datetime.now(timezone.utc)
        # only synthesize exemplar for non-skip exits
        if state.exit_type and state.exit_type.value != "skip":
            exemplar, suggestions = synthesize_exemplar(
                category=state.category,
                question_text=state.question_text,
                resume_json=state.resume_json,
                transcript=state.transcript,
            )
            d.exemplar_answer = exemplar
            d.improvement_suggestions = suggestions
        # update Question.status + best_score
        q = db.get(Question, state.question_id)
        if q:
            if state.exit_type and state.exit_type.value == "skip":
                q.status = QuestionStatus.SKIPPED
            elif total >= 9:
                q.status = QuestionStatus.IMPROVED if (q.best_score or 0) >= 9 else QuestionStatus.PRACTICED
            else:
                q.status = QuestionStatus.NEEDS_REDO
            q.best_score = max(q.best_score or 0, total)
            q.last_attempt_at = datetime.now(timezone.utc)
            db.add(q)

    db.add(d)
    db.commit()
    db.refresh(d)
    return _serialize(d)


@router.get("/{drill_id}", response_model=DrillResponse)
def get_drill(drill_id: int, db: Session = Depends(get_session)):
    d = db.get(DrillAttempt, drill_id)
    if not d:
        raise HTTPException(404, "not found")
    return _serialize(d)
