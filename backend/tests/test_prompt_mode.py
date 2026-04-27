from unittest.mock import patch

from mockinterview.agent import drill_eval


def test_thinking_framework():
    with patch.object(drill_eval, "call_json", return_value={"hint": "试试从用户场景、决策依据、量化结果三个角度切入。"}):
        out = drill_eval.give_thinking_framework(
            category="T1",
            question_text="X 项目你怎么决策的？",
            last_user_text="我没思路",
        )
    assert "用户场景" in out or "决策依据" in out
