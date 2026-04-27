from unittest.mock import patch

from mockinterview.agent import exemplar
from mockinterview.schemas.drill import TranscriptTurn


def test_synthesize_returns_tuple():
    fake = {
        "exemplar": "在用户分群项目中，我先定义 baseline 为...",
        "improvement_suggestions": ["明确 baseline", "补充归因方法", "量化业务影响"],
    }
    with patch.object(exemplar, "call_json", return_value=fake):
        ex, sugs = exemplar.synthesize_exemplar(
            category="T1",
            question_text="Q?",
            resume_json={"basic": {"name": "A"}, "projects": []},
            transcript=[TranscriptTurn(role="agent", text="Q?", round=0)],
        )
    assert "baseline" in ex
    assert len(sugs) == 3
