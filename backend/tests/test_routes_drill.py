from unittest.mock import patch

from sqlmodel import Session

from mockinterview.db.models import Question, ResumeSession
from mockinterview.db.session import engine
from mockinterview.schemas.drill import DrillEvalResult


def _seed_question():
    with Session(engine) as s:
        rs = ResumeSession(user_id=1, resume_json={}, role_type="pm")
        s.add(rs)
        s.commit()
        s.refresh(rs)
        q = Question(
            resume_session_id=rs.id,
            category="T1",
            text="说说 X 项目",
            source="反推自项目 X",
            difficulty="medium",
        )
        s.add(q)
        s.commit()
        s.refresh(q)
        return q.id


def test_start_drill_creates_attempt(client):
    qid = _seed_question()
    r = client.post("/drill", json={"question_id": qid})
    assert r.status_code == 200
    assert r.json()["status"] == "active"
    assert "X 项目" in r.json()["last_agent_text"]


def test_advance_with_skip_ends_drill(client):
    qid = _seed_question()
    drill_id = client.post("/drill", json={"question_id": qid}).json()["drill_id"]
    r = client.post(f"/drill/{drill_id}/answer", json={"text": "跳过"})
    assert r.json()["status"] == "ended"
    assert r.json()["exit_type"] == "skip"


def test_advance_with_high_score_soft_exits(client):
    qid = _seed_question()
    drill_id = client.post("/drill", json={"question_id": qid}).json()["drill_id"]
    fake_eval = DrillEvalResult(
        scores={"situation": 3, "task": 3, "action": 2, "result": 1},
        total_score=9,
        weakest_dimension="result",
        weakness_diagnosis="ok",
        next_followup="N/A",
    )
    with (
        patch("mockinterview.agent.drill_loop.evaluate_and_followup", return_value=fake_eval),
        patch(
            "mockinterview.routes.drill.synthesize_exemplar",
            return_value=("exemplar text", ["a", "b", "c"]),
        ),
    ):
        r = client.post(
            f"/drill/{drill_id}/answer",
            json={"text": "完整答案 with baseline 同期 + 归因 + 量化"},
        )
    assert r.json()["exit_type"] == "soft"
    assert r.json()["total_score"] == 9
