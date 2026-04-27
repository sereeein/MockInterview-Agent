from unittest.mock import patch

from mockinterview.agent import drill_eval


def test_propose_scenario_switch():
    with patch.object(drill_eval, "call_json", return_value={"prompt": "这个例子可能不够典型，要不你说说项目里类似的经历？"}):
        out = drill_eval.propose_scenario_switch(
            question_text="举一个实习中体现领导力的例子",
            original_intent="领导力",
            last_user_answer="我帮同事改了 PPT",
            prior_switches=0,
        )
    assert "不够典型" in out
