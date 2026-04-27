from mockinterview.agent.user_signals import UserSignal, classify


def test_explicit_end():
    assert classify("我答完了") == UserSignal.END
    assert classify("下一题") == UserSignal.END
    assert classify("answered, next") == UserSignal.END


def test_skip():
    assert classify("跳过") == UserSignal.SKIP
    assert classify("这题我不会，跳过") == UserSignal.SKIP


def test_stuck():
    assert classify("我没思路") == UserSignal.STUCK
    assert classify("能给点提示吗") == UserSignal.STUCK
    assert classify("hint please") == UserSignal.STUCK


def test_switch_scenario():
    assert classify("能换一个例子吗") == UserSignal.SWITCH_SCENARIO
    assert classify("这个例子太薄弱了，换一个") == UserSignal.SWITCH_SCENARIO


def test_normal_answer():
    assert classify("我在 X 项目里负责……") == UserSignal.ANSWER
