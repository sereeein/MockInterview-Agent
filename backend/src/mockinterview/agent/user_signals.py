import re
from enum import Enum


class UserSignal(str, Enum):
    ANSWER = "answer"
    END = "end"
    SKIP = "skip"
    STUCK = "stuck"
    SWITCH_SCENARIO = "switch_scenario"


_PATTERNS = [
    (UserSignal.SKIP, [r"跳过", r"\bskip\b", r"这题不会", r"这道.*不会"]),
    (UserSignal.STUCK, [
        r"没思路", r"不知道(?:怎么|该|从).*?(?:答|说|讲)",
        r"给.*提示", r"\bhint\b", r"\bclue\b",
        r"我.*想不到", r"我.*想不出",
    ]),
    (UserSignal.SWITCH_SCENARIO, [
        r"换.*?例子", r"换.*?场景",
        r"例子.*?(?:薄弱|不行|不够|太弱)",
        r"举不出", r"想不出.*?例子",
    ]),
    (UserSignal.END, [
        r"^我答完了\.?$", r"^答完了\.?$", r"^下一题\.?$",
        r"^answered\b", r"^done\b", r"^next\b",
    ]),
]


def classify(text: str) -> UserSignal:
    t = text.strip().lower()
    for signal, patterns in _PATTERNS:
        for p in patterns:
            if re.search(p, t, re.IGNORECASE):
                return signal
    return UserSignal.ANSWER
