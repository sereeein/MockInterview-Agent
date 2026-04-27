import json
import random
from typing import Any

from anthropic import Anthropic

BASELINE_INTERVIEWER_SYSTEM = """你是一名面试官。基于候选人简历 + JD，向候选人提一道开放问题并准备追问。
输出严格 JSON：
```json
{"question": "<题面>", "first_followup": "<针对一个普通中等回答的追问>"}
```
"""

JUDGE_SYSTEM = """你是面试评估官，盲评两位面试官在同样输入下的表现。
评判标准：哪个面试官的题更像真实面试？哪个的追问更深、更精准？
输出严格 JSON：
```json
{"winner": "A" | "B" | "tie", "rationale": "<1-2 句>"}
```
"""


def baseline_pair(
    client: Anthropic, *, resume: str, jd: str
) -> dict[str, Any]:
    """生成 baseline (裸 Claude) 的题 + 第一轮追问双输出。
    Our agent 部分由 run_eval.py 调用现有 backend 模块得到。"""
    user = f"""简历：
{resume[:2000]}
JD：
{jd[:1200] if jd else "（未提供）"}

请按要求输出。"""
    resp = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        system=[{"type": "text", "text": BASELINE_INTERVIEWER_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    payload = text[text.find("{") : text.rfind("}") + 1]
    return json.loads(payload)


def judge_blind(
    client: Anthropic,
    *,
    resume: str,
    jd: str,
    a_pair: dict[str, Any],
    b_pair: dict[str, Any],
) -> dict[str, Any]:
    user = f"""简历：
{resume[:1500]}
JD：
{jd[:1000] if jd else "（未提供）"}

面试官 A：
- 题：{a_pair['question']}
- 第一轮追问：{a_pair['first_followup']}

面试官 B：
- 题：{b_pair['question']}
- 第一轮追问：{b_pair['first_followup']}

请盲评谁更像真实面试官。"""
    resp = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=256,
        system=[{"type": "text", "text": JUDGE_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    payload = text[text.find("{") : text.rfind("}") + 1]
    return json.loads(payload)


def shuffled_label_pair(
    ours: dict[str, Any], baseline: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Returns (a_pair, b_pair, ours_label) where ours_label is 'A' or 'B' randomly.
    Used to ensure judge is genuinely blind (can't infer "A is always ours")."""
    if random.random() < 0.5:
        return ours, baseline, "A"
    return baseline, ours, "B"
