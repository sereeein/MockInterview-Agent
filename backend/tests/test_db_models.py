from datetime import datetime, timezone

from sqlmodel import Session, SQLModel, create_engine

from mockinterview.db.models import (
    DrillAttempt,
    Question,
    Report,
    ResumeSession,
    QuestionStatus,
    ExitType,
)


def test_resume_session_round_trip():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        rs = ResumeSession(
            user_id=1,
            resume_json={"basic": {"name": "Alice"}},
            jd_text="PM at ByteDance",
            company_name="ByteDance",
            role_type="pm",
        )
        s.add(rs)
        s.commit()
        s.refresh(rs)
        assert rs.id is not None
        assert rs.created_at is not None


def test_question_default_status_is_not_practiced():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        rs = ResumeSession(user_id=1, resume_json={}, role_type="pm")
        s.add(rs)
        s.commit()
        s.refresh(rs)
        q = Question(
            resume_session_id=rs.id,
            category="T1",
            text="Why this design?",
            source="反推自 项目 X",
            difficulty="medium",
        )
        s.add(q)
        s.commit()
        s.refresh(q)
        assert q.status == QuestionStatus.NOT_PRACTICED
        assert q.best_score is None


def test_drill_attempt_persists_transcript_and_scores():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
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
        d = DrillAttempt(
            question_id=q.id,
            transcript_json=[
                {"role": "agent", "text": "Q?", "round": 0},
                {"role": "user", "text": "A", "round": 1},
            ],
            rubric_scores_json={"S": 2, "T": 2, "A": 3, "R": 2},
            total_score=9,
            exit_type=ExitType.SOFT,
            scenario_switch_count=0,
            prompt_mode_count=0,
            followup_rounds=1,
            exemplar_answer="Sample answer",
            improvement_suggestions=["a", "b", "c"],
            ended_at=datetime.now(timezone.utc),
        )
        s.add(d)
        s.commit()
        s.refresh(d)
        assert d.id is not None
        assert d.total_score == 9
