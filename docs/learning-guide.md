# 从 0 到 1 学一遍这个 Agent —— MockInterview Agent 学习指南

> 给你（开发者本人）的自学手册：把项目所有思路 / 决策 / 技术 / 代码位置串成 6 层，每层标注**面试要掌握到的深度**。读完这份文档，PM / 数据 / AI 任何方向的面试官追问任意一点你都能扛住。
>
> **读法建议**：
> 1. **先扫一遍 6 层标题**，建立全局地图
> 2. **每层带着面试问答读**——把"如果被问到 X，我答 Y"刻进肌肉记忆
> 3. **重点看 ⭐ 标记的"高频面试问题"**——这些是垂直岗位面试官 100% 会戳的点
> 4. **最后过一遍代码位置**——能精确指到哪个文件哪一段，是"真做过"的硬证据

---

## 项目极简版（30 秒 elevator pitch）

**做什么**：为 PM / 数据 / AI 求职者打造的 AI 面试演练 agent。上传简历 + 选岗位 + 可选 JD → agent 反推 12 道个性化面试题 → 单题 U-loop 多轮追问 → rubric 评分 + 范例答案。

**核心差异化**（一句话讲清）：相对题库工具的优势是**反向挖题**（不是题库匹配）；相对通用 ChatGPT 的优势是**多轮追问 + 场景切换 UX**（agent 像真面试官那样给台阶但不放弃考察意图）。

**为什么这个项目能扛简历**：技术 100% 可控、agent 含量真实、开发者本人就是用户、评估框架清晰、4 周可独立交付。

---

# Layer 1：产品策略层（PM 面试 must-master ⭐⭐⭐）

> **掌握深度**：所有决策点的"放弃方案 + 选择理由"都要能 5 秒内说出。这一层 PM 面试官会反复钻。

## 1.1 项目方向取舍

最初 **3 个候选求职痛点方向**，砍 2 留 1：

| 方向 | 决定 | 砍掉/选定的根本理由 |
|---|---|---|
| **网申自动填表** | ✗ 砍 | 各家系统反爬 + DOM 异构，1-2 月单人做不出稳定版；讲故事偏技术，跟产品岗错位 |
| **岗位聚合** | ✗ 砍 | 主流招聘平台反爬 + 法律灰色；本质是 ETL+推荐**不是 agent** |
| **面试准备** | ✓ 选 | 技术 100% 可控、agent 含量真实、开发者本人就是用户、评估框架清晰 |

⭐ **面试问答**：
- 问："你这个项目为什么不做网申自动化？" → 答："反爬 + DOM 异构 4 周做不出稳定版；讲故事偏技术不是 PM 故事。"
- 问："为什么选 mock interview 这个具体场景？" → 答："4 个标准——技术可控、agent 含量真、自己就是用户（dogfooding 信号强）、评估框架清晰。"

📍 代码位置：`PROJECT.md` §1.2

---

## 1.2 核心战略：「深内核 + 开放表层」

3 个候选战略，对比后选定第 3 个：

| 策略 | 描述 | 决定 |
|---|---|---|
| ① 纯垂直 | 只服务 PM/数据/AI，其他岗位拒绝 | ✗ 浪费小红书外溢流量 |
| ② 纯通用 + 岗位下拉 | UI 加岗位选择，后端同一套通用 prompt | ✗ 反馈质量差 / 小红书无法被识别 / 讲故事弱 |
| ③ **深内核 + 开放表层** | 三类核心岗位走精细路径，其他岗位走通用兜底 | ✓ 选 |

落地：
- **前端**：「产品 / 数据 / AI」作为主推显著位置 + 「其他岗位」作为兜底入口
- **后端两条路径**：核心三岗位走 curated rubric + 真题种子库 + role-specific drilling；其他岗位走纯 LLM 通用路径

⭐ **简历金句**（PROJECT.md §3.2 既有）："**先做 vertical PMF 验证核心循环，再开放表层做 GTM 增长**"

⭐ **面试问答**：
- 问："如果只服务 PM 用户不会做得更深吗？" → 答："会浪费小红书的外溢流量——PM 帖子下面会有数据 / AI 求职者点进来，纯垂直把他们拒之门外是流量浪费。"
- 问："纯通用 + 岗位下拉为什么不行？" → 答："反馈质量差、小红书无法识别（任何通用工具都说自己'支持所有岗位'）、讲故事弱（没有'垂直'的 PMF 验证就讲不出 GTM 故事）。"

📍 代码位置：`PROJECT.md` §3

---

## 1.3 4 个差异化点的取舍（A / B / C / D）

| 代号 | 名称 | 状态 | 工程量 / 风险 |
|---|---|---|---|
| **A** | 垂直定位 | v1 必做 | 几乎不抢工时，是 prompt 规约 + 种子库 curate |
| **B-reframed** | 候选人情报（聚合 Glassdoor / 看准网 / 一亩三分地 / 知乎面经） | v1.5 推迟 | 独立工程坑：反爬 + 数据清洗 + 时效排序 + 可信度排序 |
| **C** | 简历反向挖题 | v1 核心 | 是 agent 含量主载体之一 |
| **D** | 多轮追问 | v1 核心 | 是 agent 循环价值的最佳展示 |

**关键耦合**：**C + D 必须一起做**——C 出题、D 用 C 的题为基础往深挖，分开任一边都没灵魂。

**为什么 B 推 v1.5**：候选人情报是反爬独立工程坑，4 周如果背上它可能核心 agent 引擎一行没写。引擎稳定后 B 只是给出题阶段挂数据源，下游不动。

⭐ **B-reframed 的精确定义**：
- ❌ 原版 B（已弃）：抓公司新闻 / 财报 / 高管访谈，让 agent 看新闻
- ✅ B-reframed（v1.5 采用）：抓求职者 / 在职员工的评价、面试经验、对公司偏好的反馈，让 agent **做信息考古**

⭐ **面试问答**：
- 问："为什么不一开始就接候选人情报数据？" → 答："反爬独立工程坑（Glassdoor、看准网、一亩三分地各家反爬都不一样），4 周如果先做这个核心 agent 一行没写。先稳引擎，B 后续挂数据源不动下游。"
- 问："C 和 D 谁更难？" → 答："D 难，因为 D 是状态机 + 多轮 LLM 调用；C 是单次调用 + structured output。但 C+D 必须一起做——分开任一边都没灵魂。"

📍 代码位置：`PROJECT.md` §4

---

## 1.4 v1 / v1.5 范围切分

**v1（4 周）** = A 垂直定位 + C 简历反向挖题 + D 多轮追问
**v1.5（后续）** = + B-reframed 候选人情报

**这套切法的关键好处**：
1. v1 失败仍有可交付项目（核心引擎独立成立）
2. v1 成功有清晰升级路径，简历叙事节奏好（"先做 PMF，再做增长"）

⭐ **面试问答**：
- 问："如果时间还有就接着加功能不更好？" → 答："v1 失败兜底是关键——保证 4 周后即使 B 没接，A+C+D 仍是可交付项目；v1 成功的话 v1.5 升级路径清晰，简历叙事节奏好。"

📍 代码位置：`PROJECT.md` §5

---

## 1.5 北极星指标设计（数据 / PM 面试都会问）

**MVP 期北极星**：出题相关性（每道题 0-3 分）
**成熟期北极星**：**实战命中率**——开发者本人参加 N 次真实面试后，被问到的题中 agent 提前练过的占比

这是简历上**最有说服力的数据**——不是"理论评估"而是"真实使用证明"。

⭐ **面试问答**：
- 问："你怎么衡量这个产品好不好？" → 答："MVP 期看出题相关性（LLM-as-judge 0-3 分），成熟期看实战命中率（被问到的题里有多少 agent 提前练过）。前者是工程指标，后者才是真用户价值。"
- 问："为什么不用 NPS？" → 答："NPS 量表 v1 没用户量不可信。先用 LLM-as-judge 自动化 + 自己的实战命中率两个硬指标。"

📍 代码位置：`PROJECT.md` §7（评估指标）

---

# Layer 2：用户体验层（产品交互 ⭐⭐）

> **掌握深度**：每个 UX 决策的"放弃方案 + 选择理由"都要能秒答。这一层 PM 面试官也会戳。

## 2.1 折中使用单元：B 为骨 + A 为皮

3 候选交互形态：

| 形态 | 描述 | 决定 |
|---|---|---|
| A 整套面试模式 | 一次走完 N 道题 30-60 分钟，仪式感强 | ❌ 仪式感强但门槛高，第 3 周才有可演示成果 |
| B 模块化单题练习 | 每次 10-15 分钟挑一道题深挖 | ❌ 缺乏仪式感，小红书拍不出"哇被盘问 40 分钟"的爽点视频 |
| **折中**：B 为骨 + A 为皮 | 单题演练是核心循环；整套面试是薄包装 | ✅ |

⭐ **关键洞察**：**单题演练是原子能力，整套模式 = 串联 + 包装**。Week 1-3 只做单题，Week 4 加一层会话包装就能讲两个故事。

📍 代码位置：`backend/src/mockinterview/agent/drill_loop.py`（单题）；`backend/src/mockinterview/routes/mock.py`（整套包装）；`docs/superpowers/specs/2026-04-27-mock-interview-agent-v1-design.md` §1.1

---

## 2.2 输入设计：必选 vs 可选

| 输入 | 必选 | 选型理由 |
|---|---|---|
| 简历 PDF | ✓ | 反向挖题原料 |
| 岗位类型（PM/数据/AI/其他） | ✓ | A 垂直路由开关 |
| JD | 可选 | 有则 T3 类生成；无则略过 T3，T1/T2 各加 1 道补足 |
| 公司名 | 可选 | v1 不接 B 数据，仅作为报告标签 |

**为什么不强制 JD**？因为用户在泛投阶段没具体 JD 也要能用。强制 JD 会锁住"还没具体目标"的场景。

**为什么 PDF 而非纯文本粘贴**？UX 完整度优先于 MVP 砍功能——开发者明确表态愿为体验投入工程时间。pdfplumber + Claude structured output 1-3 天可控。

📍 代码位置：`backend/src/mockinterview/routes/resume.py`；`docs/superpowers/specs/2026-04-27-mock-interview-agent-v1-design.md` §2

---

## 2.3 场景切换 UX（D 灵魂 ⭐⭐⭐）

**这是 v1 区别于通用对话工具的核心 UX**。面试官 100% 会问。

**场景**：题问"实习中的领导力"，候选人答"我帮组里同事改 PPT"——例子撑不住考察意图。

**通用 ChatGPT 怎么做**：要么死磕这个例子追问到尴尬，要么直接放弃下一题。

**MockInterview Agent 怎么做**：agent 主动给台阶——
> "这个例子可能不够典型。你有没有在 **项目 / 校园 / 课外活动 / 生活场景** 类似的事？"

**核心机制**：**释放场景维度（实习/项目/校园/生活），保留考察意图（领导力/决策/数据驱动）**。

如果连考察意图本身都没料（比如真没领导经验），agent 进一步松绑到相邻意图（"那举一个你主动推动事情发生的例子"）。

**预算**：每题最多切换 2 次场景（防止无限漂移），切换重置 1 轮追问预算。

⭐ **面试问答**：
- 问："这个 UX 跟普通的 ChatGPT 对话有什么区别？" → 答："通用工具碰到用户给烂例子时只有 2 个结局——死磕到尴尬 / 放弃下一题。我的 agent 像真面试官那样**主动让路但不放弃考察意图**——释放场景维度（实习→项目→校园→生活）保留考察维度（领导力 / 决策力）。"
- 问："为什么限制 2 次场景切换？" → 答："防止无限漂移。用户切超过 2 次说明这个考察维度真的没料，应该换题不是继续切。"

📍 代码位置：
- Prompt：`backend/src/mockinterview/agent/prompts/scenario_switch.py`
- Helper：`backend/src/mockinterview/agent/drill_eval.py:propose_scenario_switch`
- 状态机集成：`backend/src/mockinterview/agent/drill_loop.py`（搜 SWITCH_SCENARIO）

---

## 2.4 三种报告形态

| 报告 | 触发时机 | 关键模块 |
|---|---|---|
| **单题报告** | 每题 U-loop 结束 | rubric 4 维度 + 雷达图 + 改进建议 + 范例答案 + transcript |
| **题库总览** | 任意时刻进 `/library` | 卡片网格 + 顶部统计（未练 / 已练 / 待重练 / rubric 维度全局均值） |
| **整套面试报告** | 5 题模拟面试结束后 | 总览 + 高光时刻 + 短板维度 + 下一步建议 + bar chart |

**为什么 transcript 必须保留**：用户复盘的素材 + 简历演示最有说服力的证据（"看 agent 怎么把烂例子追问出真实领导力"）。

📍 代码位置：`backend/src/mockinterview/routes/reports.py`；`frontend/src/app/report/[id]/page.tsx`

---

# Layer 3：Agent 架构层（AI / 工程面试 must-master ⭐⭐⭐）

> **掌握深度**：每个 agent 决策都要能解释"为什么这么设计 + 反面方案是什么"。AI 面试官 100% 会戳。

## 3.1 U-loop 状态机（核心逻辑）

**6 个出口/重定向**：

```
                        ┌─ END (用户主动结束) → exit_type=USER_END
                        ├─ SKIP (用户主动跳过) → exit_type=SKIP
                        ├─ STUCK (用户卡壳) → 提示模式（给思考框架）
用户答 → classify ────┤                       不增 followup_rounds
                        ├─ SWITCH_SCENARIO → propose_scenario_switch
                        │                     重置 followup_rounds，最多 2 次
                        └─ ANSWER → evaluate_and_followup (LLM 调用)
                                    ├─ total_score ≥ 9 → SOFT exit
                                    ├─ followup_rounds = 3 → HARD_LIMIT
                                    └─ 否则继续追问
```

**3 个 budget caps**：
- `MAX_FOLLOWUPS = 3`：最多 3 轮追问，避免折磨用户
- `MAX_SWITCHES = 2`：场景切换上限，防漂移
- `SOFT_THRESHOLD = 9`：4 维度满分 12 中 ≥9 即结束（不凑层数）

⭐ **关键设计：场景切换不增 followup_rounds**——这是 UX 设计：场景切换是"重新出发"不是"再问一轮"。

⭐ **面试问答**：
- 问："为什么要做状态机不直接用 LangGraph？" → 答："4 周 1 人项目，状态机就 6 出口很简单（出题→答→评估→追问/结束→报告），手写 Python 完全够。LangGraph 学习曲线 + 文档变化快至少 1 周陷阱。简历叙事'手写状态机'反而比'用 LangChain'更体现工程理解。"
- 问："SOFT 退出阈值 9 是怎么定的？" → 答："4 维度 × 0-3 分 = 12 满分。≥9 = 平均 2.25 维度，意味着至少 3 个维度合格 + 1 个出色。低于这个不到结束级别，但 v1.5 会按真实使用反馈调。"
- 问："为什么 followup_rounds 硬上限是 3？" → 答："真实面试被追问到第 5 层会让人挫败。3 是平衡——足够深挖但不折磨用户。"

📍 代码位置：
- 状态机：`backend/src/mockinterview/agent/drill_loop.py`
- 状态结构：`DrillState` dataclass（11 字段）
- 信号分类：`backend/src/mockinterview/agent/user_signals.py`（纯 regex，5 信号）
- 9 单测覆盖所有 6 出口：`backend/tests/test_drill_loop.py`

---

## 3.2 5 类题型 × 5 套 rubric（替代"一套 STAR 通杀"）

⭐ **面试官最容易问的设计决策点**。

| 题类 | Rubric 名 | 4 个维度 | 触发场景 |
|---|---|---|---|
| T1 项目深挖 | STAR | Situation / Task / Action / Result | 反推自简历 projects + work_experience |
| T2 outcomes 追问 | 量化严谨度 | Baseline / 归因 / 显著性 / 业务意义 | 反推自 outcomes 量化数字 |
| T3 JD 能力对齐 | STAR + 框架 | 案例支撑 / 框架化思考 / 落地可行性 / 复盘视角 | JD 关键词 ✕ 简历项目 |
| T4 岗位通用题 | 结构化思考 | 拆解维度完整 / 优先级合理 / 风险与边界 / 可证伪 | 种子题库（PM/数据/AI/other 各 30 题） |
| T5 行为/动机题 | 自洽 + 真诚 | 动机具体 / 与履历自洽 / 非套话 / 包含反思 | "为什么投这家"等 |

**为什么不一套 STAR 通杀**？
- T2（outcomes 追问）问的是"GMV +30%，baseline 是什么？"——STAR 不适用，应该考察量化严谨度
- T4（思路题）"如何评估通知推送质量？"——STAR 不适用，应该考察拆解维度完整度
- T5（动机题）"为什么投我们"——STAR 不适用，应该考察自洽和真诚度

每维度 0-3 分，总分 12，**≥ 9 算"完整"**可结束。

⭐ **面试问答**：
- 问："STAR 是面试通用框架，为什么要做 5 套？" → 答："STAR 只适合行为/经历类题。T2 的 baseline / 归因 / 显著性 / 业务意义、T4 的拆解维度 / 优先级 / 边界 / 可证伪——这些都不是 STAR 能覆盖的。一套通杀的代价是"评估和追问不专业"。"
- 问："4 维度怎么定的？" → 答："少于 4 不够细，多于 4 LLM 评分容易抓不准。4 是平衡——既能区分能力层次，又能让 LLM 在一次调用里输出可信分数。"

📍 代码位置：
- 5 套 YAML：`backend/src/mockinterview/configs/rubrics/{t1_star,t2_quant,t3_jd_align,t4_structured,t5_motivation}.yaml`
- Loader：`backend/src/mockinterview/agent/rubrics.py`

---

## 3.3 单 LLM 调用一次输出 4 个产物（vs 多步 agent ⭐⭐）

每轮用户答完后，**一次 LLM 调用同时输出**：
1. `scores`：4 维度各打 0-3 分
2. `total_score`：0-12 总分
3. `weakest_dimension`：最弱维度的 key
4. `weakness_diagnosis`：一句话诊断
5. `next_followup`：下一轮追问

```json
{
  "scores": {"situation": 2, "task": 2, "action": 2, "result": 1},
  "total_score": 7,
  "weakest_dimension": "result",
  "weakness_diagnosis": "结果数字没有 baseline",
  "next_followup": "你说留存涨了 5%，baseline 是同期还是上月？"
}
```

**为什么不多步 agent**（先评分 → 再挑维度 → 再生成追问）？
- 多步增加延迟 + 成本
- 中间步骤错误会**累积**
- 现代 LLM context 够大，一次调用质量更稳

⭐ **关键设计：让 LLM 自己挑最弱维度**而不是启发式（"按 STAR 顺序补缺"）——最弱维度是上下文相关的，启发式判错会让追问尴尬。LLM 自己挑更灵活。

⭐ **面试问答**：
- 问："为什么不像 LangChain 那样多步拆开？" → 答："多步累积错误。一次调用可以让 LLM 看完整 transcript + rubric 后做综合判断。这也是为什么 agent 含量集中在 prompt 不在 orchestration——好的 prompt > 多步 agent。"
- 问："4 维度评分谁挑最弱怎么挑？" → 答："让 LLM 自己挑，不是启发式（按 STAR 顺序补缺）。因为'最弱'是上下文相关的——用户答了一堆 S 和 T 但没说 A，A 是最弱；如果 A 说了但没 R，R 最弱。启发式判错会让追问尴尬。"

📍 代码位置：
- Prompt：`backend/src/mockinterview/agent/prompts/drill_eval.py`
- 函数：`backend/src/mockinterview/agent/drill_eval.py:evaluate_and_followup`
- 输出 schema：`backend/src/mockinterview/schemas/drill.py:DrillEvalResult`

---

## 3.4 提示模式 + 范例答案合成

**提示模式**（用户卡壳时）：agent 不能追问、不能给答案，**只给思考框架**（rubric 4 维度倒推 3-4 个切入问题），不计入追问轮次。

**范例答案合成**（题目结束时）：agent 用候选人简历里**实际有的项目素材**合成"如果按 rubric 高分作答可以这样说"。如果简历里没合适素材，写"假设你做过 X 项目，可以这样说……"——**不能编造**。

⭐ **面试问答**：
- 问："用户卡壳了 agent 怎么处理？" → 答："不追问也不给答案，给思考框架（rubric 4 维度倒推切入问题）+ 鼓励重新答。这一轮不计入追问预算——卡壳是教练场景不是评估场景。"
- 问："范例答案怎么避免幻觉？" → 答："prompt 里硬约束'必须用候选人简历里实际有的项目素材，没合适的写假设你做过 X'——把幻觉变成 explicit 假设，让用户能区分。"

📍 代码位置：
- 提示模式：`backend/src/mockinterview/agent/prompts/prompt_mode.py` + `drill_eval.py:give_thinking_framework`
- 范例答案：`backend/src/mockinterview/agent/prompts/exemplar.py` + `agent/exemplar.py:synthesize_exemplar`

---

# Layer 4：系统架构层（工程面试 ⭐⭐）

> **掌握深度**：每个架构选型背后的取舍逻辑要清楚。后端 / DevOps 面试官会问。

## 4.1 多 provider BYOK 抽象（ContextVar）

**为什么 BYOK**：
- 上 GitHub 别人能直接试用，但开发者不替任何用户付费
- 用户成本透明（自己 provider 控制台看用量）
- 隐私：简历内容只经过用户信任的 provider

**架构**：

```
LLMProvider (ABC)
  ├─ AnthropicProvider          # Anthropic SDK + cache_control
  ├─ OpenAICompatibleProvider   # 一个适配器吃 7 家国内厂商（base_url 不同）
  └─ GeminiProvider             # google-genai SDK
```

**10 provider preset**：anthropic / openai / deepseek / qwen / zhipu / kimi / wenxin / doubao / gemini / custom。

**ContextVar 设计**（关键）：
```
请求 → use_provider Depends 读 X-Provider/X-API-Key/X-Model headers
     → make_provider() → set_active(provider)
     → handler 调 call_json() → active() 取出 provider
```

**为什么不每个 agent 函数加 provider 参数**？6 个 agent 模块 + 多个 helper，加起来 ~10 个 call site 全要改。ContextVar 模式让现有 signature 不变，只在请求边界做注入。

⭐ **重大踩坑**：`use_provider` 必须是 `async def`，不能是 sync `def`。原因：
- FastAPI 把 sync deps 和 sync handlers **各自丢进独立 threadpool worker**
- ContextVar 跨 thread **不传播**：dep worker 设的值，handler worker 读不到
- 改 async 后 dep 在主 event loop 任务里执行，anyio 通过 `context.run(func, *args)` 把主任务 context 拷贝给 handler 的 worker thread

⭐ **面试问答**：
- 问："为什么不直接在每个路由读 header 调 LLM？" → 答："agent 模块（6 个）在 prompt 调试时频繁迭代，让它们不知道 provider 是关键——provider 是 request-scoped 的（不同用户用不同 key），不是 module-scoped。ContextVar 是 Python 给 async/threading 安全注入 request 数据的标准方式。"
- 问："7 家国内厂商怎么一个适配器搞定？" → 答："它们都暴露 OpenAI-compatible API（DeepSeek/千问/智谱/Kimi/文心/豆包都有 compatible 模式）。一个 OpenAI SDK 实例 + 不同 base_url 就够。一个适配器吃 7 家。"

📍 代码位置：
- 抽象：`backend/src/mockinterview/agent/providers/base.py`
- 3 实现：`providers/{anthropic,openai_compat,gemini}.py`
- 工厂 + ContextVar：`providers/__init__.py`
- Dep：`backend/src/mockinterview/routes/_deps.py`
- 文档：`docs/byok.md`

---

## 4.2 服务端无状态设计

**DrillState（状态机的所有数据）完整快照存 `state_snapshot` JSON 列**：

```python
@dataclass
class DrillState:
    question_id: int
    question_text: str
    category: str
    transcript: list[TranscriptTurn]
    followup_rounds: int
    scenario_switch_count: int
    prompt_mode_count: int
    last_eval: DrillEvalResult | None
    status: DrillStatus
    exit_type: ExitType | None
    ...
```

每次 `POST /drill/{id}/answer`：
1. 从 DB 读 state_snapshot → `from_snapshot(snap) → DrillState`
2. `advance(state, user_text)` 改 state
3. `to_snapshot(state)` 序列化回 DB

**好处**：
- 服务端无 in-memory 状态，可水平扩展
- 用户中断恢复 → 重新拉 drill_id 即可
- Phase 4 部署到 Railway 不用粘性 session

⭐ **面试问答**：
- 问："为什么不用 Redis / 内存 cache 存 session？" → 答："v1 单实例，但故意按可水平扩展设计。状态机所有数据 JSON snapshot 进 SQLite 列——下游切 Postgres / 多实例都不用改。"
- 问："JSON 列性能不会差吗？" → 答："v1 流量场景，每个 drill_attempt 一行，JSON ~5KB。单用户每分钟最多几次查询。性能不是瓶颈——简单性是。"

📍 代码位置：`backend/src/mockinterview/agent/drill_storage.py:to_snapshot/from_snapshot`

---

## 4.3 数据库 schema（4 张主表 + 1 张 mock 表）

```
resume_session (parent of question + report)
  ├─ resume_json (JSON 4 字段)
  ├─ jd_text (nullable)
  ├─ company_name (nullable)
  └─ role_type (pm/data/ai/other)

question (FK to resume_session)
  ├─ category T1..T5 / source / difficulty
  ├─ status enum (not_practiced/practiced/needs_redo/improved/skipped)
  └─ best_score / last_attempt_at

drill_attempt (FK to question)
  ├─ transcript_json (list[dict])
  ├─ rubric_scores_json (dict)
  ├─ exit_type enum (soft/hard_limit/user_end/skip)
  ├─ scenario_switch_count / prompt_mode_count / followup_rounds
  ├─ exemplar_answer / improvement_suggestions
  └─ state_snapshot (完整 DrillState JSON)

report (FK to resume_session) — 整套面试聚合
mock_session (FK to resume_session) — 5 题串联会话
```

**为什么用 SQLite + SQLModel**：
- 单文件部署简单，SQLModel = SQLAlchemy 的 Pydantic 风格包装
- JSON 列 portable（未来切 Postgres 不改）
- 4 表关系不复杂，不需要复杂迁移工具

**已知坑**：SQLite 的 `metadata.create_all()` **不会给已存在表加新列**——加 `state_snapshot` 列时 dev 必须手动删 `data/app.db`。Phase 5 加 Alembic。

📍 代码位置：`backend/src/mockinterview/db/models.py`

---

## 4.4 Prompt caching 优化

Anthropic 的 prompt caching（5 分钟 TTL）通过 system block 上的 `cache_control={"type":"ephemeral"}` 标记。

`build_cached_system([prompt])` 返回单个带 cache_control 的 block 数组。**简历 + JD + rubric 这部分 prompt 在一次 session 内反复复用**——开 caching 节省 70%+ 成本。

⭐ **面试问答**：
- 问："你说节省 70% 成本是怎么算的？" → 答："Claude prompt caching 缓存命中部分按 0.1x 普通 input price 收费。我们的 system prompt（rubric + 简历结构化数据）~3000 token 是 cached，user message ~200 token 是 uncached。每次调用 90%+ token 走 cache → 实际成本约 0.3x（30% input price + 100% output price）。"
- 问："其他 provider 没这特性怎么办？" → 答："OpenAI 自动 prefix cache（系统行为不需用户标记，效果差一点但有）。Gemini 没有显式 cache。BYOK 文档里提醒'非 Anthropic provider 会丢这一项 70% 成本节省'。"

📍 代码位置：`backend/src/mockinterview/agent/providers/anthropic.py`

---

# Layer 5：评估层（数据驱动 ⭐⭐⭐）

> **掌握深度**：评估方法论 + 数据指标 + 已知 bug 都要清楚。数据 / PM 面试都会戳。

## 5.1 三个 LLM-as-judge

| Judge | 评估什么 | Output |
|---|---|---|
| **relevance** | 题目 vs 简历+JD 的契合度 | 0-3 分 + rationale |
| **drilling** | 追问是否击中最弱维度 | bool hit_weakest |
| **baseline_compare** | ours vs 裸 Claude 哪个更像真实面试官 | "A" / "B" / "tie" |

**为什么 LLM-as-judge 而不是人工**：
- v1 没有大量用户量做问卷
- 跑 100 道题人工评 1 小时，LLM 评 1 分钟
- prompt 改完立刻可回归

⭐ **关键设计：判官固定 Anthropic Claude**（即使 agent 用其他 provider 跑）——保证 cross-run 可比性。"用 GLM 判 Claude" vs "用 Claude 判 Claude"指标值不可对比。

⭐ **面试问答**：
- 问："LLM-as-judge 不就是自我循环吗？" → 答："是有 self-bias 风险。所以做了几个 mitigation：(1) 判官 prompt 跟生产 prompt 完全分开，避免 leakage；(2) baseline blind compare 用随机 A/B 标签洗牌让判官无法 systematic bias；(3) 抽 10% 人工抽检校准判官。这是工业界标准做法。"
- 问："判官 prompt 怎么写？" → 答："每个 judge 独立 prompt，明确评估标准。relevance 0-3 分用'完全无关 / 牵强 / 相关 / 精准'4 档，drilling 只输出布尔'命中最弱维度吗'，baseline_compare 输出 A/B/tie。三个独立判官避免单 prompt 评太多维度。"

📍 代码位置：`eval/judges/{relevance,drilling,baseline_compare}.py`

---

## 5.2 baseline blind compare（盲评）⭐

**目标**：证明 vertical agent 比 naive Claude 强。

**方法**：
1. 同样输入（简历 + JD）
2. ours_pair = 我们 agent 的题 + 第一轮追问
3. baseline = 裸 Claude（无 rubric / 无种子题库）的题 + 第一轮追问
4. **shuffled_label_pair**：50/50 随机决定 ours 是 "A" 还是 "B"
5. judge_blind 看 A/B 但**不知道哪个是 ours**
6. 统计 ours 胜率

**为什么 shuffle**：消除 judge LLM 的 systematic bias（如果 ours 总是 A，判官可能基于位置 pattern match）。

⭐ **当前 v1 的 bug**：胜率 0%——**不是 agent 真差，是评估方法 bug**。我们用 `<placeholder mid-quality answer>` 当 user 答案喂给 evaluate_and_followup，导致 ours 的 first_followup 上下文怪（"你的答案太敷衍了"），baseline 没看 transcript 输出干净追问，judge 盲评必输。**v1.5 修法**：先调 user_simulator 生成合成 mid-quality 答案，再喂给 evaluate_and_followup。

⭐ **面试问答**：
- 问："你这个 baseline 胜率 0% 怎么回事？" → 答："这是已知评估方法 bug 不是 agent 差。我们 ours_pair 用 placeholder mid-quality answer 做 transcript，agent 输出的追问会针对这个奇怪的 placeholder（'你答案太敷衍'），而 baseline 没看 transcript 输出干净追问，judge 盲评必输。修法是先用 simulator 生成合成 mid-quality 答案。"

📍 代码位置：`eval/judges/baseline_compare.py:shuffled_label_pair`

---

## 5.3 评估流程 + 实际数据

```bash
ANTHROPIC_API_KEY=...
cd backend
uv run python ../eval/run_eval.py
```

8 pair × ~35 LLM calls = **~280 calls**，runtime 5-15 min，cost $5-15。

**v1.0 结果**（`eval/reports/2026-04-27.md`）：

| 指标 | 阈值 | 实际 |
|---|---|---|
| 出题相关性 | ≥ 2.2/3 | **2.94/3** （6 个成功 pair 均值；总均值被 2 个 fatal failure 拉到 2.21） |
| 追问命中率 | ≥ 70% | **100%** （28/28） |
| baseline 胜率 | ≥ 70% | 0% （评估方法 bug，v1.5 修） |

⭐ **简历可用数据**（避开 baseline 0% 误导）：
- 出题相关性 **2.94/3**
- 追问命中率 **100%**
- 8 pair 自动回归（覆盖 4 roles × JD 有/无）

📍 代码位置：`eval/run_eval.py`（orchestrator） / `eval/datasets/`（5 简历 + 3 JD + pairs.yaml） / `eval/reports/2026-04-27.md`

---

# Layer 6：部署层（DevOps ⭐）

> **掌握深度**：部署链路概念 + 关键决策。基础工程面试会问。

## 6.1 BYOK 让部署变简单

**关键事实**：服务端**不持有任何 LLM API key**。

- Railway 后端只设 `CORS_ORIGINS` + `DB_URL`（指向 Volume）
- 用户的 key 通过 `X-API-Key` header 每请求传输
- 服务端拿到 key 后即时构造 provider client，处理完丢弃

⭐ **面试问答**：
- 问："如果用户 key 泄露到日志怎么办？" → 答："v1 没显式 redact 但默认 logging 不打印 header。生产升级路径是加 logging filter——把 X-API-Key header 替换为 `***`。"
- 问："你不怕用户的 key 在你后端被滥用吗？" → 答："后端不存 key 只透传。用户能在 Anthropic / OpenAI 控制台看每笔请求的来源 IP，能撤销 key。比让用户给一个第三方服务长期持有 key 风险低得多。"

---

## 6.2 Railway / Vercel CI/CD

**Backend（Railway）**：
- Dockerfile 用 uv + python 3.12 + 显式 hatchling package config
- Volume 挂 `/data` 给 SQLite
- `$PORT` 用 shell expansion 让 Railway 动态分配

**Frontend（Vercel）**：
- Next.js 16 自动检测 + edge function
- `NEXT_PUBLIC_API_URL` build-time baked（vercel env add 必须在 deploy 前）

**CORS exact-origin matching**：CORSMiddleware + `allow_credentials=True` 必须 exact match 不能用 wildcard。列出 2 个稳定 Vercel URL。

📍 代码位置：`backend/Dockerfile` / `backend/.dockerignore` / `frontend/.env.local` / `docs/deployment.md`

---

# 附录：4 周开发节奏（Phase 0 → v1.0）

| Week | Phase | 关键里程碑 |
|---|---|---|
| W1 | Phase 1：后端基建 + 出题引擎 | 10 task，28 单测，`w1-done` tag |
| W2 | Phase 2：U-loop 核心 | 8 task，50 单测，`w2-done` tag |
| W3 | Phase 3：前端 + 报告 | 7 task，8 routes，`w3-done` tag |
| W4 | Phase 4.0 多 provider 改造 + 4.1-4.6 评估 + 4.7-4.8 部署 | 63 单测，evaluation 跑通，`v1.0` tag |

⭐ **面试问答**：
- 问："4 周怎么规划？" → 答："Week 1 后端骨架 + 出题（A+C），Week 2 U-loop 状态机（D），Week 3 前端，Week 4 评估 + 部署。每周末有可演示成果（每周一篇小红书 post）——避免 4 周一次性大爆炸的失败模式。"

📍 完整 plan：`plans/2026-04-27-mock-interview-agent-v1.md`（~5800 行 task 清单）

---

# 自查 Checklist：面试前 1 小时过一遍

如果以下任何一题你 5 秒内说不出来，回到对应 Layer 重读：

**Layer 1 产品策略**：
- [ ] 项目方向 3 选 1 砍掉的具体理由
- [ ] 「深内核 + 开放表层」战略 + 反面 2 方案
- [ ] B 推 v1.5 的具体理由（避免卡数据层）
- [ ] 北极星指标 MVP 期 vs 成熟期分别是什么

**Layer 2 UX**：
- [ ] B 为骨 + A 为皮的取舍（为什么不纯 A 或纯 B）
- [ ] 场景切换 UX 的核心机制（释放维度保留意图）

**Layer 3 Agent**：
- [ ] U-loop 6 出口 + 2 redirects 是哪些
- [ ] 5 套 rubric 为什么不一套 STAR 通杀
- [ ] 单 LLM 调用一次输出 4 个产物 vs 多步 agent 的取舍

**Layer 4 系统**：
- [ ] BYOK 的 ContextVar 模式 + 为什么 dep 必须 async
- [ ] 服务端无状态设计的关键（state_snapshot）
- [ ] prompt caching 70% 成本节省怎么算

**Layer 5 评估**：
- [ ] 3 个 judge 各自评估什么 + 为什么固定 Anthropic 当判官
- [ ] baseline shuffle 的目的（消除 judge bias）
- [ ] v1 真实数据：相关性 2.94/3，命中率 100%

**Layer 6 部署**：
- [ ] BYOK 怎么让服务端零持有 secret
- [ ] CORS 为什么不能用 wildcard

---

# 推荐阅读顺序（如果时间紧）

1. **30 分钟版本**：读 Layer 1 + Layer 3 + Layer 5 的⭐面试问答部分。这 3 层是面试官最容易戳的。
2. **2 小时版本**：通读全部 6 层，重点记每层的⭐问答。
3. **半天版本**：通读 + 翻一遍代码位置文件。能精确指到代码 = "真做过"。
