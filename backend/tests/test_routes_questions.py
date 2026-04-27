from unittest.mock import patch

from sqlmodel import Session

from mockinterview.db.models import ResumeSession
from mockinterview.db.session import engine
from mockinterview.schemas.question import QuestionList


FAKE_QLIST = QuestionList.model_validate(
    {
        "questions": [
            {"text": f"Q{i}", "category": c, "source": "x", "difficulty": "medium"}
            for i, c in enumerate(["T1"] * 4 + ["T2"] * 2 + ["T3"] * 3 + ["T4"] * 2 + ["T5"])
        ]
    }
)


def _seed_session(role="pm", jd="PM at X"):
    with Session(engine) as s:
        rs = ResumeSession(
            user_id=1, resume_json={"basic": {"name": "A"}}, jd_text=jd, role_type=role
        )
        s.add(rs)
        s.commit()
        s.refresh(rs)
        return rs.id


def test_generate_persists_12_questions(client):
    sid = _seed_session()
    with patch("mockinterview.routes.questions.generate_questions", return_value=FAKE_QLIST):
        r = client.post("/questions/generate", json={"resume_session_id": sid})
    assert r.status_code == 200
    assert len(r.json()) == 12


def test_list_filters_by_category(client):
    sid = _seed_session()
    with patch("mockinterview.routes.questions.generate_questions", return_value=FAKE_QLIST):
        client.post("/questions/generate", json={"resume_session_id": sid})
    r = client.get(f"/questions?resume_session_id={sid}&category=T1")
    assert len(r.json()) == 4


def test_patch_status_updates(client):
    sid = _seed_session()
    with patch("mockinterview.routes.questions.generate_questions", return_value=FAKE_QLIST):
        ids = [q["id"] for q in client.post("/questions/generate", json={"resume_session_id": sid}).json()]
    qid = ids[0]
    r = client.patch(f"/questions/{qid}/status", json={"status": "needs_redo"})
    assert r.json()["status"] == "needs_redo"


def test_generate_empty_returns_502(client):
    sid = _seed_session()
    empty_list = QuestionList.model_validate({"questions": []})
    with patch("mockinterview.routes.questions.generate_questions", return_value=empty_list):
        r = client.post("/questions/generate", json={"resume_session_id": sid})
    assert r.status_code == 502


def test_generate_unknown_session_returns_404(client):
    r = client.post("/questions/generate", json={"resume_session_id": 99999})
    assert r.status_code == 404
