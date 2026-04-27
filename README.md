# MockInterview Agent

垂直岗位 AI 面试演练 · 简历反向挖题 · 多轮追问 · 场景切换 UX。

**Live**: _TBD — see `docs/deployment.md`_

## What it does
- 上传简历 PDF + 选岗位（PM / 数据 / AI / 其他）+ 可选 JD
- agent 反向挖出 12 道个性化面试题（5 类：项目深挖 / outcomes 追问 / JD 对齐 / 通用题 / 行为题）
- 单题 U-loop 演练：rubric 评分 + 多轮追问 + **场景切换让路**（"这个例子不够典型，要不你说说项目里类似的事？"）
- 单题报告（雷达图 + 改进建议 + 范例答案）/ 整套面试报告（5 题串联 + 短板维度）

## Architecture
- **Backend**: Python 3.12 + FastAPI + Anthropic SDK (Claude 4.7 Opus) + SQLModel + SQLite + pdfplumber
- **Frontend**: Next.js 16 (App Router) + TypeScript + shadcn/ui + Tailwind v4 + Recharts
- **Agent**: 手写状态机 + 单次 LLM structured output（每轮一次调用：评分 + 找最弱维度 + 生成追问 + 场景切换 / 提示模式）
- **Eval**: LLM-as-judge pipeline（relevance / drilling / baseline compare）

## Eval results
评估报告位于 `eval/reports/`。运行步骤见 [`docs/deployment.md`](docs/deployment.md#run-eval)。
3 个核心指标 + 阈值：
- 出题相关性：≥ 2.2 / 3
- 追问命中率：≥ 70%
- vs 裸 Claude 盲评胜率：≥ 70%

简历金句汇总：[`docs/resume-bullets.md`](docs/resume-bullets.md)。

## Local dev

```bash
# Backend
cd backend
env -u VIRTUAL_ENV uv sync
ANTHROPIC_API_KEY=sk-... env -u VIRTUAL_ENV uv run uvicorn mockinterview.main:app --reload

# Frontend (in another terminal)
cd frontend
pnpm install
pnpm dev
```

打开 http://localhost:3000 。

## Project journey
- 立项: [`PROJECT.md`](PROJECT.md)
- 设计: [`docs/superpowers/specs/2026-04-27-mock-interview-agent-v1-design.md`](docs/superpowers/specs/2026-04-27-mock-interview-agent-v1-design.md)
- 实施计划: [`plans/2026-04-27-mock-interview-agent-v1.md`](plans/2026-04-27-mock-interview-agent-v1.md)
- 进度日志: [`memory.md`](memory.md)
- 部署 + 评估手册: [`docs/deployment.md`](docs/deployment.md)
