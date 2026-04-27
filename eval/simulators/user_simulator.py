import json
from typing import Any

from anthropic import Anthropic

SIM_SYSTEM = """你是一个面试中"中等质量"的求职者，扮演候选人作答。
你的特征：
- 项目经历真实（按收到的简历素材展开）
- 答题完整度大概 5-7/12 分（rubric 上）
- 偶尔遗漏 baseline / 量化归因 / 业务意义等关键维度
- 不卡壳、不主动结束、不要求换场景，老实作答（这样才能测出 agent 的追问质量）

输出严格 JSON：
```json
{"answer": "<候选人本轮回复，1-3 句>"}
```
"""


def simulate_answer(
    client: Anthropic,
    *,
    resume: str,
    question: str,
    transcript: list[dict[str, Any]],
) -> str:
    transcript_block = "\n".join(
        f"[{t['role']}] {t['text']}" for t in transcript
    )
    user = f"""你的简历素材：
{resume[:2000]}

当前对话 transcript：
{transcript_block}

请作答下一轮。"""
    resp = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        system=[{"type": "text", "text": SIM_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    payload = text[text.find("{") : text.rfind("}") + 1]
    return json.loads(payload)["answer"]
