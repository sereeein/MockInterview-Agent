from typing import Any

from mockinterview.agent.client import build_cached_system, call_json
from mockinterview.agent.prompts.drill_eval import DRILL_EVAL_SYSTEM, DRILL_EVAL_USER_TEMPLATE
from mockinterview.agent.prompts.scenario_switch import (
    SCENARIO_SWITCH_SYSTEM,
    SCENARIO_SWITCH_USER_TEMPLATE,
)
from mockinterview.agent.rubrics import load_rubric
from mockinterview.schemas.drill import DrillEvalResult, TranscriptTurn


def _format_rubric(rubric: dict[str, Any]) -> str:
    lines = []
    for d in rubric["dimensions"]:
        lines.append(f"- {d['key']} ({d['label']}): {d['description']}")
    lines.append("")
    lines.append("评分级别：")
    for level, desc in rubric["score_levels"].items():
        lines.append(f"  {level}: {desc}")
    return "\n".join(lines)


def _format_transcript(turns: list[TranscriptTurn]) -> str:
    lines = []
    for t in turns:
        prefix = {"agent": "面试官", "user": "候选人"}[t.role]
        tag = "" if t.kind == "normal" else f" [{t.kind}]"
        lines.append(f"[{t.round}] {prefix}{tag}: {t.text}")
    return "\n".join(lines)


def evaluate_and_followup(
    *,
    category: str,
    question_text: str,
    transcript: list[TranscriptTurn],
) -> DrillEvalResult:
    rubric = load_rubric(category)
    system = build_cached_system([DRILL_EVAL_SYSTEM])
    user = DRILL_EVAL_USER_TEMPLATE.format(
        category=category,
        question_text=question_text,
        rubric_block=_format_rubric(rubric),
        transcript_block=_format_transcript(transcript),
    )
    payload = call_json(
        system_blocks=system,
        messages=[{"role": "user", "content": user}],
        max_tokens=1024,
    )
    return DrillEvalResult.model_validate(payload)


def propose_scenario_switch(
    *,
    question_text: str,
    original_intent: str,
    last_user_answer: str,
    prior_switches: int,
) -> str:
    system = build_cached_system([SCENARIO_SWITCH_SYSTEM])
    user = SCENARIO_SWITCH_USER_TEMPLATE.format(
        question_text=question_text,
        original_intent=original_intent,
        last_user_answer=last_user_answer,
        prior_switches=prior_switches,
    )
    payload = call_json(
        system_blocks=system,
        messages=[{"role": "user", "content": user}],
        max_tokens=512,
    )
    return payload["prompt"]
