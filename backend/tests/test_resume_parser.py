from unittest.mock import patch

import pytest

from mockinterview.agent import resume_parser
from mockinterview.schemas.resume import ResumeStructured


FAKE_RESPONSE = {
    "basic": {
        "name": "Alice Wu",
        "education": [
            {
                "school": "ABC Univ",
                "degree": "MS",
                "major": "Data Science",
                "graduation": "2025",
            }
        ],
    },
    "projects": [
        {
            "title": "User segmentation",
            "period": "2024",
            "role": "Lead",
            "description": "K-means on 10M users",
            "outcomes": "AUC 0.85",
        }
    ],
    "work_experience": [],
    "skills": ["Python", "SQL"],
}


def test_parse_resume_returns_structured(monkeypatch):
    def fake_extract(_):
        return "fake resume text"

    monkeypatch.setattr(resume_parser, "extract_pdf_text", fake_extract)
    with patch("mockinterview.agent.resume_parser.call_json", return_value=FAKE_RESPONSE):
        result = resume_parser.parse_resume(b"PDFBYTES")
    assert isinstance(result, ResumeStructured)
    assert result.basic.name == "Alice Wu"
    assert result.projects[0].outcomes == "AUC 0.85"


def test_parse_resume_empty_text_raises(monkeypatch):
    monkeypatch.setattr(resume_parser, "extract_pdf_text", lambda _: "")
    with pytest.raises(ValueError, match="empty"):
        resume_parser.parse_resume(b"PDFBYTES")
