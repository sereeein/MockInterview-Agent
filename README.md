# MockInterview Agent

垂直岗位 AI 面试演练 · 简历反向挖题 · 多轮追问 · 场景切换 UX。

**Live**: https://mockinterview-agent.vercel.app
**Backend API**: https://mockinterview-backend-production.up.railway.app（Swagger 在 `/docs`）
**Repo**: https://github.com/sereeein/MockInterview-Agent · **Release**: [v1.0](https://github.com/sereeein/MockInterview-Agent/releases/tag/v1.0)

> Status: **v1.0 shipped** (4 周 1 人独立交付 · 63 unit tests · 出题相关性 2.94/3 · 追问命中率 100%)

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

## BYOK (Bring Your Own Key)

MockInterview Agent never uses a server-side API key. Each user supplies their own key via the in-app `/setup` page; key is stored in browser localStorage and forwarded as headers on every request.

**Supported providers** (10 total):
| Provider | Default model | 备注 |
|---|---|---|
| Anthropic Claude | `claude-opus-4-7` | **推荐** —— prompt 在 Claude 上调优；prompt caching 节省 70%+ 成本 |
| OpenAI | `gpt-4-turbo` | OpenAI 官方 |
| DeepSeek | `deepseek-chat` | OpenAI-compat |
| 通义千问 (Qwen) | `qwen-max` | DashScope OpenAI-compat 模式 |
| 智谱 GLM | `glm-4-plus` | OpenAI-compat |
| Kimi (Moonshot) | `moonshot-v1-32k` | OpenAI-compat |
| 文心一言 | `ernie-4.0-turbo-8k` | 千帆 OpenAI-compat |
| 豆包 | `doubao-pro-32k` | 火山方舟 OpenAI-compat |
| Google Gemini | `gemini-2.0-flash-exp` | Gemini 原生 SDK |
| Custom | — | 任何 OpenAI-compat 端点 |

> 注：prompt 是按 Claude 调优的，跨家可能效果有差异。Anthropic 是默认推荐；其他 provider 用于"我已经有 X 家的 key"场景。

## Eval results

评估报告位于 `eval/reports/`。运行步骤见 [`docs/deployment.md`](docs/deployment.md#run-eval)。

**3 个核心指标 + 阈值**：
- 出题相关性：≥ 2.2 / 3
- 追问命中率：≥ 70%
- vs 裸 Claude 盲评胜率：≥ 70%

**注**：eval 的 LLM-as-judge"裁判"固定用 Anthropic Claude（保证不同 provider 跑出的结果可对比）；agent 本身可换任意支持的 provider 跑（通过 `MOCK_PROVIDER` env var）。简历金句汇总：[`docs/resume-bullets.md`](docs/resume-bullets.md)；BYOK 架构说明：[`docs/byok.md`](docs/byok.md)。

## Local dev

```bash
# Backend
cd backend
env -u VIRTUAL_ENV uv sync
env -u VIRTUAL_ENV uv run uvicorn mockinterview.main:app --reload

# Frontend (in another terminal)
cd frontend
pnpm install
pnpm dev
```

打开 http://localhost:3000 → 第一次访问会跳到 `/setup` 引导你配置 API key（任意支持的 provider）→ 然后回到上传页。

## Project journey
- 立项策略: [`PROJECT.md`](PROJECT.md)
- v1 设计文档: [`docs/superpowers/specs/2026-04-27-mock-interview-agent-v1-design.md`](docs/superpowers/specs/2026-04-27-mock-interview-agent-v1-design.md)
- 4 周实施 plan（~50 task）: [`plans/2026-04-27-mock-interview-agent-v1.md`](plans/2026-04-27-mock-interview-agent-v1.md)
- 完整开发日志: [`memory.md`](memory.md)
- **6 层学习指南**（面试 defense 用）: [`docs/learning-guide.md`](docs/learning-guide.md)
- BYOK 架构说明: [`docs/byok.md`](docs/byok.md)
- 简历金句: [`docs/resume-bullets.md`](docs/resume-bullets.md)
- 部署 + 评估手册: [`docs/deployment.md`](docs/deployment.md)
- 小红书 4 周冷启动模板: [`docs/xiaohongshu/`](docs/xiaohongshu/)
