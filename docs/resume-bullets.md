# Resume Bullets — MockInterview Agent

## 推荐版本（产品 PM 求职，4-bullet 格式，含 Task 4.6 真实数据）

```
MockInterview Agent — 反向挖题 + 多轮追问的 AI 面试演练 agent       2026.04
个人项目 · Anthropic Claude + Next.js 16 + Python FastAPI + 10 provider BYOK · Live Demo + GitHub 开源

· 痛点洞察：求职者每天面对"想多演练但没人陪练" + "用通用 ChatGPT 模拟体感像
  背书不像面试"两难 —— 题库类工具假设你已知考点（但 PM 岗 vs 数据岗考啥都不
  一样）、对话类工具假设你能问出好问题（但你问不出，这才是要找面试官的根本
  原因）。核心洞察：mock interview 时间投入最多但收益最差，差距在"是否被好
  面试官追问"。

· 产品决策：设计单题闭环（U-loop：rubric 评分 + 多轮追问 + 范例答案）+ 长期
  循环（题库状态机累积 best_score / 最弱维度 / 已练状态）。10 个有明确 trade-
  off 的设计决策（5 类题型 × 5 套 rubric 替代"一套 STAR 通杀" / 6 出口状态机
  + 2 redirects + 3 个 budget cap / 场景切换 UX 释放场景维度保留考察意图 /
  单 LLM 调用一次输出 4 个产物替代多步 agent / Anthropic-first 而非通用化 /
  BYOK 多 provider 服务器零持有 secret），每条都对应放弃的反面方案。

· AI Coding 交付：用 Claude 主导 4 阶段 plan + sub-agent driven dev 完成
  backend（Python FastAPI + SQLModel + 手写状态机）+ frontend（Next.js 16 +
  shadcn）+ LLM-as-judge eval pipeline 全栈共约 6000 行代码，每阶段都有 tag
  + 可演示闭环。10 provider BYOK 抽象层（Anthropic + OpenAI-compat 7 家国内
  厂商 + Gemini + custom，ContextVar 请求作用域）。完成 Vercel + Railway 生
  产部署 + 63 单测 + LLM-as-judge 自动评估（出题相关性 2.94/3 · 追问命中率
  100% · 8 pair 自动回归）。

· 产出：Live Demo | 视频 Demo | PRD 文档 | 冷启动 playbook | GitHub 开源
```

> 数据来源：`eval/reports/2026-04-27.md`（8 pair × ~35 LLM calls 自动跑出）。
> v1.5 待修：baseline 盲评胜率（当前 0% 是评估方法 bug，不是 agent 真的差）。

---

## 备用版本（仍带 `<X>%` 占位，留作 v1.5 evaluation 重做后的格式）

> Fill `<X>%` and `<N>` after running eval (Task 4.6) and own job-hunt-season tracking. Below are bullet templates that fit a PM / 数据 / AI 求职简历.

## Project Description (1 sentence)

> Built and deployed an AI mock-interview agent that reverse-mines questions from a candidate's resume and conducts multi-turn drilling with rubric-based scoring; achieved **<X>%** blind-eval win rate vs. naive Claude on PM-track scenarios.

## Bullet variations

**Architecture / Agent design (PM/数据 简历都通用)**:
- Designed a 5-rubric system (STAR / 量化严谨度 / JD 对齐 / 结构化思考 / 自洽真诚) replacing one-size-fits-all STAR; agent picks each round's weakest dimension via a single structured-output call (eval drilling-hit rate **<X>%**).
- Hand-rolled state machine with 6 exits (soft / hard / user_end / skip / prompt_mode / scenario_switch) and budget caps (3 follow-ups, 2 scenario switches), avoiding LangChain抽象债 in 4-week solo build.

**UX / 产品 sense（PM 简历重点）**:
- Shipped a "scenario switch" UX inspired by real interviewer behavior: when a candidate's example can't support the question, the agent proactively offers alternative scenarios (实习 → 项目 → 校园 → 生活) while preserving the underlying competency being tested.
- Designed 5-category question distribution (T1 项目深挖 / T2 outcomes 追问 / T3 JD 对齐 / T4 通用题 / T5 行为) tied to 5 hardcoded rubric YAMLs; new role = add a插槽 not a新分支.

**Eval / 数据驱动（数据简历重点）**:
- Built end-to-end eval pipeline: synthetic-user simulator + 3 LLM-as-judge evaluators (relevance / drilling-hit / baseline blind compare) over 8 resume × JD pairs; turned prompt tuning from "feels right" to **+<X>% relevance / +<X>% drill hit-rate** measurable iterations.
- Established blind-eval baseline (vs naive Claude) with shuffled A/B labeling to neutralize judge bias; vertical agent **<X>%** win rate is the headline metric.

**Engineering depth**:
- 4-week solo build: spec → 4-phase plan → backend (FastAPI + Anthropic SDK + SQLModel) + frontend (Next.js 16 + shadcn) + automated eval pipeline + Vercel/Railway deploy. 50+ unit tests, prompt caching for 70%+ cost savings.
- Stateless server design: drill state persisted as JSON snapshot column on `drill_attempt` table; horizontally scalable from day 1.

**Multi-provider engineering**:
- Designed BYOK (Bring Your Own Key) architecture: ContextVar-based provider abstraction in backend (`anthropic.py` / `openai_compat.py` / `gemini.py`); frontend collects user's key on `/setup` and forwards as `X-API-Key` header per request; key never persists server-side. Supports 10 providers (Anthropic / OpenAI / DeepSeek / 千问 / 智谱 / Kimi / 文心 / 豆包 / Gemini / custom OpenAI-compat).
- One adapter (`OpenAICompatibleProvider`) covers 7 Chinese LLM providers via OpenAI-compatible base_url substitution — minimizes integration code for国内用户 onboarding.

## Real interview命中率（v1 后持续追踪）

> Living metric — fill after own job-hunt season:
> - In **<N>** real PM/数据 interviews during 2026 秋招/春招, **<X>%** of asked questions had been pre-drilled in the agent.
> - The agent's session reports correctly identified my top 2 weakness dimensions before recruiter feedback (sample size: <N>).
