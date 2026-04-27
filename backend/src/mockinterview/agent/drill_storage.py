from typing import Any

from mockinterview.agent.drill_loop import DrillState, DrillStatus
from mockinterview.db.models import ExitType
from mockinterview.schemas.drill import DrillEvalResult, TranscriptTurn


def to_snapshot(state: DrillState) -> dict[str, Any]:
    return {
        "question_id": state.question_id,
        "question_text": state.question_text,
        "category": state.category,
        "original_intent": state.original_intent,
        "resume_json": state.resume_json,
        "transcript": [t.model_dump() for t in state.transcript],
        "followup_rounds": state.followup_rounds,
        "scenario_switch_count": state.scenario_switch_count,
        "prompt_mode_count": state.prompt_mode_count,
        "last_eval": state.last_eval.model_dump() if state.last_eval else None,
        "status": state.status.value,
        "exit_type": state.exit_type.value if state.exit_type else None,
    }


def from_snapshot(snap: dict[str, Any]) -> DrillState:
    return DrillState(
        question_id=snap["question_id"],
        question_text=snap["question_text"],
        category=snap["category"],
        original_intent=snap["original_intent"],
        resume_json=snap["resume_json"],
        transcript=[TranscriptTurn.model_validate(t) for t in snap["transcript"]],
        followup_rounds=snap["followup_rounds"],
        scenario_switch_count=snap["scenario_switch_count"],
        prompt_mode_count=snap["prompt_mode_count"],
        last_eval=(
            DrillEvalResult.model_validate(snap["last_eval"]) if snap["last_eval"] else None
        ),
        status=DrillStatus(snap["status"]),
        exit_type=ExitType(snap["exit_type"]) if snap["exit_type"] else None,
    )
