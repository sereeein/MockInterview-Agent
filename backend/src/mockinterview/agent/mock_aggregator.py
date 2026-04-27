from collections import defaultdict
from typing import Any

from sqlmodel import Session, select

from mockinterview.db.models import DrillAttempt, MockSession, Question


def aggregate_mock(db: Session, mock_id: int) -> dict[str, Any]:
    ms = db.get(MockSession, mock_id)
    if not ms:
        raise ValueError("mock session not found")
    drills = db.exec(
        select(DrillAttempt).where(DrillAttempt.id.in_(ms.drill_attempt_ids))
    ).all()
    drill_summaries: list[dict[str, Any]] = []
    cat_scores: dict[str, list[int]] = defaultdict(list)
    dim_scores: dict[str, list[int]] = defaultdict(list)
    dim_to_cat: dict[str, set[str]] = defaultdict(set)
    highlights: list[dict[str, Any]] = []
    total_scores: list[int] = []

    for d in drills:
        q = db.get(Question, d.question_id)
        drill_summaries.append(
            {
                "drill_id": d.id,
                "question_id": q.id,
                "question_text": q.text,
                "category": q.category,
                "total_score": d.total_score,
            }
        )
        cat_scores[q.category].append(d.total_score)
        total_scores.append(d.total_score)
        if d.total_score >= 9:
            highlights.append(
                {"question_id": q.id, "question_text": q.text, "score": d.total_score}
            )
        for dim_key, score in (d.rubric_scores_json or {}).items():
            dim_scores[dim_key].append(score)
            dim_to_cat[dim_key].add(q.category)

    weaknesses = [
        {
            "dimension": k,
            "avg": sum(v) / len(v),
            "from_categories": sorted(dim_to_cat[k]),
        }
        for k, v in dim_scores.items()
        if v and (sum(v) / len(v)) < 2.0
    ]
    weaknesses.sort(key=lambda w: w["avg"])

    next_steps: list[str] = []
    for w in weaknesses[:3]:
        next_steps.append(
            f"重点重练 {', '.join(w['from_categories'])} 题型中维度 「{w['dimension']}」（当前均值 {w['avg']:.1f}/3）"
        )
    if not next_steps:
        next_steps = ["整体表现良好，可挑战更难类目（T2 / T3 / T4）"]

    return {
        "mock_session_id": mock_id,
        "total_avg_score": sum(total_scores) / len(total_scores) if total_scores else 0.0,
        "category_avg_scores": {k: sum(v) / len(v) for k, v in cat_scores.items()},
        "highlights": highlights,
        "weaknesses": weaknesses[:5],
        "next_steps": next_steps,
        "drill_summaries": drill_summaries,
    }
