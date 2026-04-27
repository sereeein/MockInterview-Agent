from unittest.mock import patch

import pytest

from mockinterview.agent.drill_loop import DrillState, DrillStatus, advance, start_drill
from mockinterview.agent.user_signals import UserSignal
from mockinterview.db.models import ExitType
from mockinterview.schemas.drill import DrillEvalResult, TranscriptTurn


def _state(**overrides):
    base = dict(
        question_id=1,
        question_text="说说你做的 X 项目",
        category="T1",
        original_intent="项目深挖",
        resume_json={"basic": {"name": "A"}, "projects": []},
        transcript=[TranscriptTurn(role="agent", text="说说你做的 X 项目", round=0)],
        followup_rounds=0,
        scenario_switch_count=0,
        prompt_mode_count=0,
        last_eval=None,
        status=DrillStatus.ACTIVE,
        exit_type=None,
    )
    base.update(overrides)
    return DrillState(**base)


def test_start_drill_returns_initial_state():
    s = start_drill(
        question_id=1,
        question_text="Q?",
        category="T1",
        resume_json={"basic": {"name": "A"}},
        original_intent="X",
    )
    assert s.status == DrillStatus.ACTIVE
    assert len(s.transcript) == 1
    assert s.transcript[0].role == "agent"


def test_advance_user_end_signal_triggers_user_end_exit():
    state = _state()
    out = advance(state, "我答完了")
    assert out.status == DrillStatus.ENDED
    assert out.exit_type == ExitType.USER_END


def test_advance_user_skip_signal_triggers_skip_exit():
    state = _state()
    out = advance(state, "跳过")
    assert out.status == DrillStatus.ENDED
    assert out.exit_type == ExitType.SKIP


def test_advance_user_stuck_triggers_prompt_mode_no_round_increment():
    state = _state()
    with patch("mockinterview.agent.drill_loop.give_thinking_framework", return_value="试试 X / Y / Z 三个角度。"):
        out = advance(state, "我没思路")
    assert out.status == DrillStatus.ACTIVE
    assert out.followup_rounds == 0  # not incremented
    assert out.prompt_mode_count == 1
    assert out.transcript[-1].kind == "prompt_mode"


def test_advance_switch_scenario_consumes_budget_and_resets_round():
    state = _state(followup_rounds=2)
    with patch("mockinterview.agent.drill_loop.propose_scenario_switch", return_value="换个项目里的例子？"):
        out = advance(state, "能换一个吗")
    assert out.status == DrillStatus.ACTIVE
    assert out.scenario_switch_count == 1
    assert out.followup_rounds == 0  # reset
    assert out.transcript[-1].kind == "scenario_switch"


def test_advance_switch_scenario_caps_at_2_then_hard_limit():
    state = _state(scenario_switch_count=2, followup_rounds=2)
    out = advance(state, "再换一个")
    # 3rd switch attempt should not consume; falls through to normal answer eval
    # because we've capped budget
    assert out.scenario_switch_count == 2


def test_advance_normal_answer_runs_eval():
    state = _state()
    fake_eval = DrillEvalResult(
        scores={"situation": 2, "task": 2, "action": 2, "result": 2},
        total_score=8,
        weakest_dimension="result",
        weakness_diagnosis="缺 baseline",
        next_followup="baseline 怎么定的？",
    )
    with patch("mockinterview.agent.drill_loop.evaluate_and_followup", return_value=fake_eval):
        out = advance(state, "我做了 X 项目，结果还行。")
    assert out.followup_rounds == 1
    assert out.status == DrillStatus.ACTIVE
    assert out.transcript[-2].role == "user"
    assert out.transcript[-1].text == "baseline 怎么定的？"


def test_advance_high_score_triggers_soft_exit():
    state = _state()
    fake_eval = DrillEvalResult(
        scores={"situation": 3, "task": 3, "action": 2, "result": 1},
        total_score=9,
        weakest_dimension="result",
        weakness_diagnosis="ok",
        next_followup="N/A",
    )
    with patch("mockinterview.agent.drill_loop.evaluate_and_followup", return_value=fake_eval):
        out = advance(state, "我答得很完整。")
    assert out.status == DrillStatus.ENDED
    assert out.exit_type == ExitType.SOFT


def test_advance_hits_hard_limit_at_3_followups():
    state = _state(followup_rounds=2)  # 第 3 轮提交后强制结束
    fake_eval = DrillEvalResult(
        scores={"situation": 1, "task": 1, "action": 1, "result": 1},
        total_score=4,
        weakest_dimension="action",
        weakness_diagnosis="弱",
        next_followup="再追一问？",
    )
    with patch("mockinterview.agent.drill_loop.evaluate_and_followup", return_value=fake_eval):
        out = advance(state, "再答一次")
    assert out.followup_rounds == 3
    assert out.status == DrillStatus.ENDED
    assert out.exit_type == ExitType.HARD_LIMIT
