from sqlmodel import Session

from mockinterview.db.models import Question, ResumeSession
from mockinterview.db.session import engine


def _seed_with_questions():
    with Session(engine) as s:
        rs = ResumeSession(user_id=1, resume_json={}, role_type="pm")
        s.add(rs)
        s.commit()
        s.refresh(rs)
        for i, c in enumerate(["T1", "T2", "T3", "T4", "T5", "T1", "T2"]):
            s.add(
                Question(
                    resume_session_id=rs.id,
                    category=c,
                    text=f"Q{i}",
                    source="x",
                    difficulty="medium",
                )
            )
        s.commit()
        return rs.id


def test_start_mock_picks_5_distinct_categories(client):
    sid = _seed_with_questions()
    r = client.post("/mock", json={"resume_session_id": sid})
    body = r.json()
    assert len(body["question_ids"]) == 5


def test_advance_increments(client):
    sid = _seed_with_questions()
    mid = client.post("/mock", json={"resume_session_id": sid}).json()["id"]
    from sqlmodel import Session as SQLSession
    from mockinterview.db.models import DrillAttempt, ExitType
    with SQLSession(engine) as s:
        d = DrillAttempt(
            question_id=1,
            transcript_json=[],
            rubric_scores_json={"a": 1},
            total_score=4,
            exit_type=ExitType.SOFT,
            exemplar_answer="",
            improvement_suggestions=[],
        )
        s.add(d)
        s.commit()
        s.refresh(d)
        did = d.id
    r = client.post(f"/mock/{mid}/advance", json={"drill_attempt_id": did})
    assert r.json()["current_index"] == 1
