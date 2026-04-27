import json

from mockinterview.agent.client import build_cached_system, call_json
from mockinterview.agent.prompts.question_gen import (
    QUESTION_GEN_SYSTEM,
    QUESTION_GEN_USER_TEMPLATE,
    ROLE_ANGLE,
    ROLE_LABEL,
)
from mockinterview.agent.seed_bank import load_seed_bank
from mockinterview.schemas.question import QuestionList


def _distribution(has_jd: bool) -> dict[str, int]:
    if has_jd:
        return {"T1": 4, "T2": 2, "T3": 3, "T4": 2, "T5": 1}
    return {"T1": 5, "T2": 3, "T3": 0, "T4": 2, "T5": 1}


def _format_seeds(role: str, n: int) -> str:
    bank = load_seed_bank(role)
    sample = bank[: max(n * 5, 12)]  # give the model >= 12 candidates to choose from
    return "\n".join(f"- ({q['angle']}, {q['difficulty']}) {q['text']}" for q in sample)


def generate_questions(
    *,
    role: str,
    resume_json: dict,
    jd_text: str | None,
    company_name: str | None,
) -> QuestionList:
    has_jd = bool(jd_text and jd_text.strip())
    dist = _distribution(has_jd)
    total = sum(dist.values())
    system = QUESTION_GEN_SYSTEM.format(
        role=role,
        role_label=ROLE_LABEL[role],
        role_angle=ROLE_ANGLE[role],
        total=total,
        n_t1=dist["T1"],
        n_t2=dist["T2"],
        n_t3=dist["T3"],
        n_t4=dist["T4"],
        n_t5=dist["T5"],
        seed_questions=_format_seeds(role, dist["T4"]),
    )
    user = QUESTION_GEN_USER_TEMPLATE.format(
        resume_json=json.dumps(resume_json, ensure_ascii=False, indent=2),
        jd_block=(jd_text or "（未提供）"),
        company=company_name or "（未提供）",
        total=total,
    )
    payload = call_json(
        system_blocks=build_cached_system([system]),
        messages=[{"role": "user", "content": user}],
        max_tokens=4096,
    )
    return QuestionList.model_validate(payload)
