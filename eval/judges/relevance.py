import json
from typing import Any

from anthropic import Anthropic

JUDGE_SYSTEM = """你是面试题评分员。
你会收到：
- 简历摘要
- JD 摘要（可能为空）
- 一道生成的面试题（含题面 + category + source）

按 0-3 分打分（"题与候选人简历 + JD 的契合度"）：
0 = 完全无关 / 答非所问 / 任何候选人都能答
1 = 牵强 / 浅层关联
2 = 相关 / 能用上简历素材
3 = 精准 / 引用了具体项目 outcomes 或 JD 关键能力

严格输出 JSON：
```json
{"score": int, "rationale": "<1 句>"}
```
"""


def score_question(client: Anthropic, *, resume: str, jd: str, question: dict[str, Any]) -> dict:
    user = f"""简历：
{resume[:2000]}

JD：
{jd[:1200] if jd else "（未提供）"}

题：
- text: {question['text']}
- category: {question['category']}
- source: {question['source']}

请打分。"""
    resp = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=256,
        system=[{"type": "text", "text": JUDGE_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    payload = text[text.find("{") : text.rfind("}") + 1]
    return json.loads(payload)
