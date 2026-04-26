import io
from unittest.mock import patch

from sqlmodel import Session, select

from mockinterview.agent.resume_parser import ResumeParseError
from mockinterview.db.models import ResumeSession
from mockinterview.db.session import engine
from mockinterview.schemas.resume import ResumeStructured


PARSED = ResumeStructured.model_validate(
    {
        "basic": {"name": "Alice", "education": []},
        "projects": [],
        "work_experience": [],
        "skills": [],
    }
)


def test_post_resume_creates_session(client):
    with patch("mockinterview.routes.resume.parse_resume", return_value=PARSED):
        r = client.post(
            "/resume",
            files={"file": ("r.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
            data={"role_type": "pm", "jd_text": "PM at X", "company_name": "X"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["role_type"] == "pm"
    assert body["resume_json"]["basic"]["name"] == "Alice"
    with Session(engine) as s:
        rows = s.exec(select(ResumeSession)).all()
    assert len(rows) >= 1


def test_post_resume_invalid_role_type(client):
    r = client.post(
        "/resume",
        files={"file": ("r.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        data={"role_type": "invalid"},
    )
    assert r.status_code == 400


def test_post_resume_empty_file(client):
    r = client.post(
        "/resume",
        files={"file": ("r.pdf", io.BytesIO(b""), "application/pdf")},
        data={"role_type": "pm"},
    )
    assert r.status_code == 400


def test_post_resume_parse_error_returns_400(client):
    with patch(
        "mockinterview.routes.resume.parse_resume",
        side_effect=ResumeParseError("PDF 看似扫描件"),
    ):
        r = client.post(
            "/resume",
            files={"file": ("r.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
            data={"role_type": "pm"},
        )
    assert r.status_code == 400
    assert "扫描件" in r.json()["detail"]
