from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mockinterview.agent.drill_eval import (
    evaluate_and_followup,
    give_thinking_framework,
    propose_scenario_switch,
)
from mockinterview.agent.user_signals import UserSignal, classify
from mockinterview.db.models import ExitType
from mockinterview.schemas.drill import DrillEvalResult, TranscriptTurn

MAX_FOLLOWUPS = 3
MAX_SWITCHES = 2
SOFT_THRESHOLD = 9


class DrillStatus(str, Enum):
    ACTIVE = "active"
    ENDED = "ended"


@dataclass
class DrillState:
    question_id: int
    question_text: str
    category: str
    original_intent: str
    resume_json: dict[str, Any]
    transcript: list[TranscriptTurn] = field(default_factory=list)
    followup_rounds: int = 0
    scenario_switch_count: int = 0
    prompt_mode_count: int = 0
    last_eval: DrillEvalResult | None = None
    status: DrillStatus = DrillStatus.ACTIVE
    exit_type: ExitType | None = None


def start_drill(
    *,
    question_id: int,
    question_text: str,
    category: str,
    resume_json: dict[str, Any],
    original_intent: str,
) -> DrillState:
    return DrillState(
        question_id=question_id,
        question_text=question_text,
        category=category,
        original_intent=original_intent,
        resume_json=resume_json,
        transcript=[TranscriptTurn(role="agent", text=question_text, round=0)],
    )


def _append_user(state: DrillState, text: str) -> None:
    state.transcript.append(
        TranscriptTurn(role="user", text=text, round=state.followup_rounds)
    )


def advance(state: DrillState, user_text: str) -> DrillState:
    if state.status == DrillStatus.ENDED:
        return state

    signal = classify(user_text)

    # End-class signals
    if signal == UserSignal.END:
        _append_user(state, user_text)
        state.status = DrillStatus.ENDED
        state.exit_type = ExitType.USER_END
        return state
    if signal == UserSignal.SKIP:
        _append_user(state, user_text)
        state.status = DrillStatus.ENDED
        state.exit_type = ExitType.SKIP
        return state

    # Redirect-class: stuck → prompt mode (no round increment)
    if signal == UserSignal.STUCK:
        _append_user(state, user_text)
        hint = give_thinking_framework(
            category=state.category,
            question_text=state.question_text,
            last_user_text=user_text,
        )
        state.transcript.append(
            TranscriptTurn(
                role="agent",
                text=hint,
                round=state.followup_rounds,
                kind="prompt_mode",
            )
        )
        state.prompt_mode_count += 1
        return state

    # Redirect-class: scenario switch (only if budget left)
    if signal == UserSignal.SWITCH_SCENARIO and state.scenario_switch_count < MAX_SWITCHES:
        _append_user(state, user_text)
        switch_msg = propose_scenario_switch(
            question_text=state.question_text,
            original_intent=state.original_intent,
            last_user_answer=user_text,
            prior_switches=state.scenario_switch_count,
        )
        state.scenario_switch_count += 1
        state.followup_rounds = 0  # reset budget
        state.transcript.append(
            TranscriptTurn(
                role="agent",
                text=switch_msg,
                round=0,
                kind="scenario_switch",
            )
        )
        return state

    # Normal answer (or scenario switch attempted past budget) → evaluate
    _append_user(state, user_text)
    state.followup_rounds += 1
    eval_result = evaluate_and_followup(
        category=state.category,
        question_text=state.question_text,
        transcript=state.transcript,
    )
    state.last_eval = eval_result

    if eval_result.total_score >= SOFT_THRESHOLD:
        state.status = DrillStatus.ENDED
        state.exit_type = ExitType.SOFT
        return state

    if state.followup_rounds >= MAX_FOLLOWUPS:
        state.status = DrillStatus.ENDED
        state.exit_type = ExitType.HARD_LIMIT
        return state

    # Continue: agent emits the followup
    state.transcript.append(
        TranscriptTurn(
            role="agent",
            text=eval_result.next_followup,
            round=state.followup_rounds,
        )
    )
    return state
