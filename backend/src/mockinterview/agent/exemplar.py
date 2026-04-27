import json
from typing import Any

from mockinterview.agent.client import build_cached_system, call_json
from mockinterview.agent.prompts.exemplar import EXEMPLAR_SYSTEM, EXEMPLAR_USER_TEMPLATE
from mockinterview.agent.rubrics import load_rubric
from mockinterview.schemas.drill import TranscriptTurn


def synthesize_exemplar(
    *,
    category: str,
    question_text: str,
    resume_json: dict[str, Any],
    transcript: list[TranscriptTurn],
) -> tuple[str, list[str]]:
    rubric = load_rubric(category)
    dims = ", ".join(f"{d['label']} ({d['description']})" for d in rubric["dimensions"])
    system = build_cached_system([EXEMPLAR_SYSTEM])
    transcript_block = "\n".join(
        f"[{t.round}] {'面试官' if t.role == 'agent' else '候选人'}: {t.text}"
        for t in transcript
    )
    user = EXEMPLAR_USER_TEMPLATE.format(
        question_text=question_text,
        category=category,
        dimensions=dims,
        resume_json=json.dumps(resume_json, ensure_ascii=False, indent=2),
        transcript_block=transcript_block,
    )
    payload = call_json(
        system_blocks=system,
        messages=[{"role": "user", "content": user}],
        max_tokens=1024,
    )
    return payload["exemplar"], payload["improvement_suggestions"]
