import json
from typing import Any

from anthropic import Anthropic

DRILL_JUDGE_SYSTEM = """你是面试官评估官。
对一段「面试官-候选人」交互，判断面试官的某一轮追问是否击中了候选人答案最弱维度。

输入：
- 题目 + rubric 4 维度
- 上一轮候选人回答
- 面试官本轮追问

输出：
```json
{"hit_weakest": bool, "rationale": "<1 句>"}
```
"""


def judge_followup(
    client: Anthropic,
    *,
    question: str,
    rubric_dims: list[dict[str, str]],
    last_answer: str,
    followup: str,
) -> dict[str, Any]:
    dims_block = "\n".join(f"- {d['key']} ({d['label']}): {d['description']}" for d in rubric_dims)
    user = f"""题目：{question}

Rubric 维度：
{dims_block}

候选人上一轮回答：
{last_answer}

面试官本轮追问：
{followup}

请判断追问是否击中最弱维度。"""
    resp = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=256,
        system=[{"type": "text", "text": DRILL_JUDGE_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    payload = text[text.find("{") : text.rfind("}") + 1]
    return json.loads(payload)
