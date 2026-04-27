from unittest.mock import patch

from mockinterview.agent import drill_eval
from mockinterview.schemas.drill import TranscriptTurn


FAKE = {
    "scores": {"situation": 2, "task": 2, "action": 2, "result": 1},
    "total_score": 7,
    "weakest_dimension": "result",
    "weakness_diagnosis": "结果数字没有 baseline",
    "next_followup": "你说留存涨了 5%，baseline 是同期还是上月？",
}


def test_evaluate_returns_parsed_result():
    transcript = [
        TranscriptTurn(role="agent", text="Q?", round=0),
        TranscriptTurn(role="user", text="我做了 X 项目，留存涨了 5%。", round=1),
    ]
    with patch.object(drill_eval, "call_json", return_value=FAKE):
        result = drill_eval.evaluate_and_followup(
            category="T1",
            question_text="X 项目你怎么决策的？",
            transcript=transcript,
        )
    assert result.total_score == 7
    assert result.weakest_dimension == "result"
    assert "baseline" in result.next_followup
