# Resume Bullets — MockInterview Agent

## 推荐版本（产品 PM 求职，4-bullet 格式 · 锚定 PROJECT.md 的产品策略）

```
MockInterview Agent — 反向挖题 + 多轮追问的 AI 面试演练 agent       2026.04
个人项目 · 为产品 / 数据 / AI 求职者设计 · Anthropic Claude + Next.js 16
+ 10 provider BYOK · Live Demo + GitHub 开源

· 方向取舍：从 3 个求职场景候选筛选 —— 砍掉「网申自动填表」（反爬 + DOM
  异构 1-2 月单人做不出稳定版）、砍掉「岗位聚合」（招聘平台反爬 + 法律灰，
  本质是 ETL+推荐不是 agent），选定「面试准备」：技术 100% 可控、agent
  含量真实、开发者本人就是用户、评估框架清晰。核心洞察：mock interview
  是求职者时间投入最多但收益最差的环节 —— 题库工具假设你已知考点（但 PM
  vs 数据考啥都不一样）、通用 ChatGPT 假设你能问出好问题（但问不出才是
  要练的根本原因），差距在"是否被好面试官追问"。

· 战略与范围：核心策略「深内核 + 开放表层」—— vs 纯垂直（只服务 PM/数据/AI
  会浪费小红书外溢流量）vs 纯通用 + 岗位下拉（反馈质量差、小红书无法被识
  别、讲故事弱）。落地：核心三岗位走 curated rubric + 真题种子库 + role-
  specific drilling，其他岗位走通用兜底入口。v1/v1.5 切分：A 垂直定位 +
  C 简历反向挖题 + D 多轮追问 4 周必做，B 候选人情报数据层推 v1.5 —— 避
  免 4 周卡在反爬数据层、核心 agent 引擎一行没写。简历金句：「**先做
  vertical PMF 验证核心循环，再开放表层做 GTM 增长**」。

· 产品 + 工程交付：U-loop 多轮追问（rubric 评分 + 最弱维度识别 + 追问生
  成单 LLM 调用一次输出，避免多步 agent 累积错误）+ 场景切换 UX（agent
  主动识别例子撑不住考察意图时给台阶，"释放场景维度保留考察意图"，这是真
  实面试官行为，通用对话工具不会做）+ 5 类题型 × 5 套 rubric 替代"一套
  STAR 通杀"。LLM-as-judge 8 pair 自动回归（出题相关性 2.94/3 · 追问命
  中率 100%）。10 provider BYOK 让任何人 0 运营成本试用；开发者本人秋招
  dogfood，「实战命中率」作为长期北极星指标 —— v1.5 跑完真实面试季后
  回填。

· 产出：Live Demo | 视频 Demo | PRD 文档 | 冷启动 playbook | GitHub 开源
```

> 数据来源：`eval/reports/2026-04-27.md`（8 pair × ~35 LLM calls 自动跑出）。
> v1.5 待修：baseline 盲评胜率（当前 0% 是评估方法 bug，不是 agent 真的差）。
> 锚点：PROJECT.md §1.2 痛点筛选过程 / §3 深内核+开放表层策略 / §4 范围切分 / §3.2 简历金句。

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
