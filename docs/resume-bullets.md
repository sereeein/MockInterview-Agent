# Resume Bullets — MockInterview Agent

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
