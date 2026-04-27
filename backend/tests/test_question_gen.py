from unittest.mock import patch

from mockinterview.agent import question_gen


FAKE_PAYLOAD = {
    "questions": [
        {"text": f"Q{i}", "category": cat, "source": "x", "difficulty": "medium"}
        for i, cat in enumerate(
            ["T1"] * 4 + ["T2"] * 2 + ["T3"] * 3 + ["T4"] * 2 + ["T5"]
        )
    ]
}


def test_generate_questions_with_jd_returns_12():
    with patch.object(question_gen, "call_json", return_value=FAKE_PAYLOAD):
        out = question_gen.generate_questions(
            role="pm",
            resume_json={"basic": {"name": "A"}},
            jd_text="PM at X",
            company_name="X",
        )
    assert len(out.questions) == 12
    cats = [q.category for q in out.questions]
    assert cats.count("T1") == 4
    assert cats.count("T3") == 3


def test_generate_questions_without_jd_redistributes():
    dist = question_gen._distribution(has_jd=False)
    assert dist["T3"] == 0
    assert dist["T1"] == 5
    assert sum(dist.values()) == 11
