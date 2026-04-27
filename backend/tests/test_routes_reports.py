from unittest.mock import patch

from sqlmodel import Session

from mockinterview.db.models import Question, ResumeSession
from mockinterview.db.session import engine
from mockinterview.schemas.drill import DrillEvalResult


def _seed():
    with Session(engine) as s:
        rs = ResumeSession(user_id=1, resume_json={}, role_type="pm")
        s.add(rs)
        s.commit()
        s.refresh(rs)
        q = Question(
            resume_session_id=rs.id,
            category="T1",
            text="Q",
            source="x",
            difficulty="medium",
        )
        s.add(q)
        s.commit()
        s.refresh(q)
        return q.id


def test_report_returns_full_data(client):
    qid = _seed()
    drill_id = client.post("/drill", json={"question_id": qid}).json()["drill_id"]
    fake = DrillEvalResult(
        scores={"situation": 3, "task": 3, "action": 2, "result": 1},
        total_score=9,
        weakest_dimension="result",
        weakness_diagnosis="ok",
        next_followup="N/A",
    )
    with (
        patch("mockinterview.agent.drill_loop.evaluate_and_followup", return_value=fake),
        patch(
            "mockinterview.routes.drill.synthesize_exemplar",
            return_value=("exemplar text", ["a", "b", "c"]),
        ),
    ):
        client.post(f"/drill/{drill_id}/answer", json={"text": "好答案"})
    r = client.get(f"/reports/drill/{drill_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["total_score"] == 9
    assert body["exemplar_answer"] == "exemplar text"
    assert len(body["improvement_suggestions"]) == 3
    assert body["rubric"]["category"] == "T1"
