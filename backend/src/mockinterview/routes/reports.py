from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from mockinterview.agent.mock_aggregator import aggregate_mock
from mockinterview.agent.rubrics import load_rubric
from mockinterview.db.models import DrillAttempt, Question
from mockinterview.db.session import get_session

router = APIRouter(prefix="/reports", tags=["reports"])


class SingleReport(BaseModel):
    drill_id: int
    question_id: int
    question_text: str
    category: str
    transcript: list[dict]
    rubric: dict
    rubric_scores: dict[str, int]
    total_score: int
    exit_type: str
    scenario_switch_count: int
    prompt_mode_count: int
    followup_rounds: int
    exemplar_answer: str
    improvement_suggestions: list[str]


@router.get("/drill/{drill_id}", response_model=SingleReport)
def drill_report(drill_id: int, db: Session = Depends(get_session)):
    d = db.get(DrillAttempt, drill_id)
    if not d:
        raise HTTPException(404, "drill not found")
    q = db.get(Question, d.question_id)
    rubric = load_rubric(q.category)
    return SingleReport(
        drill_id=d.id,
        question_id=q.id,
        question_text=q.text,
        category=q.category,
        transcript=d.transcript_json,
        rubric=rubric,
        rubric_scores=d.rubric_scores_json,
        total_score=d.total_score,
        exit_type=d.exit_type.value if hasattr(d.exit_type, "value") else d.exit_type,
        scenario_switch_count=d.scenario_switch_count,
        prompt_mode_count=d.prompt_mode_count,
        followup_rounds=d.followup_rounds,
        exemplar_answer=d.exemplar_answer,
        improvement_suggestions=d.improvement_suggestions,
    )


@router.get("/mock/{mock_id}")
def mock_report_alias(mock_id: int, db: Session = Depends(get_session)):
    return aggregate_mock(db, mock_id)
