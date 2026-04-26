# MockInterview Agent v1 设计文档

> 阶段 2 产出：把 PROJECT.md 立项决策落到可执行的 v1 工程设计。
> 配套立项文档：`PROJECT.md`（产品策略与范围决策）。
> 本文档落地以下立项决策：A 垂直定位 + C 简历反向挖题 + D 多轮追问的 v1 核心引擎。

---

## 0. 概览

**一句话定位**：为产品 / 数据 / AI 求职者打造的、基于个人简历反向挖题并能多轮追问的 AI 面试演练 agent。

**v1 目标**：4 周内由 1 人独立交付一个**已部署上线**、能服务真实使用、自带评估证据的核心引擎。

**v1 范围**：A（垂直定位）+ C（简历反向挖题）+ D（多轮追问）。
**v1 不做**：B 候选人情报（v1.5）、语音/视频模拟、账号体系、PDF 导出、多次演练对比视图。

**核心差异化**：
1. 基于个人简历**反向挖题**，不是题库匹配
2. **多轮追问**深挖到 STAR/Rubric 完整
3. **场景切换 UX**——agent 主动识别用户例子薄弱时给台阶（"换个项目/校园/生活的例子"），保留考察意图、释放场景维度
4. 五类岗位差异化 rubric（不是一套 STAR 套所有题）

---

## 1. 用户故事 & 核心使用流程

### 1.1 折中使用单元：B 为骨 + A 为皮

- **核心入口（B 形态，日常用）**：进题库 → 挑一道题 → 进 U-loop 深挖 → 题目状态更新（已练 / 待重练 / 改进）
- **薄包装入口（A 形态，仪式感）**：点"模拟面试" → agent 从题库自动挑 5 道连续走 → 整套报告

工程上：单题演练是原子能力，整套模式 = 串联 + 包装，开发顺序天然解耦。

### 1.2 一次完整流程

```
用户上传简历 PDF
        ↓
后端 PDF 抽文本 + Claude 结构化解析 → 4 类字段（basic/projects/work_experience/skills）
        ↓
用户填写：目标岗位类型（必选）、JD（可选）、公司名（可选）
        ↓
出题引擎一次 LLM 调用 → 12 道题 + 元数据入题库
        ↓
进入题库总览页（卡片网格 + 状态筛选 + rubric 维度全局统计）
        ↓
两条入口：
  ├─ 选一道题 → U-loop 演练 → 单题报告
  └─ 「模拟面试」5 题串联 → 整套面试报告
```

---

## 2. 输入设计

### 2.1 必选 vs 可选

| 输入 | 必选 | 说明 |
|---|---|---|
| 简历 PDF | ✓ | 反向挖题原料 |
| 岗位类型（PM / 数据 / AI / 其他） | ✓ | A 垂直路由开关 |
| JD | 可选 | 有则 T3 类生成；无则略过 T3，T1/T2 各加 1 道补足 |
| 公司名 | 可选 | v1 不接 B 数据，仅作为报告标签 |

### 2.2 简历输入格式

**v1 直接做完整方案**：PDF 上传 + Claude 智能结构化解析（pdfplumber 抽文本 + 一次 Claude structured output 调用产出 JSON）。

**为什么不选纯文本粘贴**：用户体验优先；用现代 LLM structured output，工程量 1-3 天可控；与"产品级质感"的 v1 定位一致。

---

## 3. 简历结构化字段 Schema

```json
{
  "basic": {
    "name": "string",
    "education": [
      {"school": "...", "degree": "...", "major": "...", "graduation": "..."}
    ]
  },
  "projects": [
    {"title", "period", "role", "description", "outcomes"}
  ],
  "work_experience": [
    {"company", "title", "period", "responsibilities", "outcomes"}
  ],
  "skills": ["..."]
}
```

**显式排除**：证书、奖项、论文、语言能力、兴趣爱好、推荐人。这些字段对反向挖题贡献微小，加进来增加结构化错误率。

**核心字段**：`projects` 与 `work_experience`（反向挖题素材池）。每条强制要求 `description` + `outcomes`。

**outcomes 缺失处理**：v1 不强制补全；agent 在出题阶段把"缺少量化结果"作为考察点（"如果让你重新写这条简历，你会怎么把结果量化？"），缺失反而成为 feature。

---

## 4. 出题引擎

### 4.1 一次生成 12 道题，分 5 类

| 类别 | 占比 | 来源 | 示例（PM） | 示例（数据） |
|---|---|---|---|---|
| **T1 项目深挖** | 4 | projects + work_experience.description | "X feature 的决策依据 + trade-off？" | "用户分群项目里为什么选 K-means？怎么验证？" |
| **T2 outcomes 追问** | 2 | work_experience.outcomes 量化数据 | "GMV +30% 怎么算的？baseline、归因、显著性？" | "AUC 0.85 业务上意味着什么？怎么 calibrate？" |
| **T3 JD 能力对齐** | 3 | JD 关键词 ✕ 简历项目 | JD 提"用户增长"→"以你某项目为例谈用户增长策略" | JD 提"实验设计"→"假设要验证 X，A/B 怎么搭、样本量？" |
| **T4 岗位通用题** | 2 | 种子题库 | 北极星指标、case 题 | metric 设计、SQL 思路 |
| **T5 行为/动机** | 1 | 通用模板 | "为什么投这家"、"职业规划" | 同左 |

**JD 缺失分支**：T3 略过，T1/T2 各加 1 道补足；总数仍 ~10-12。

### 4.2 岗位差异化（A）的工程实现

**通用 prompt 模板 + 岗位插槽**（不是写四套独立 prompt）：

```
通用出题模板（永远不变）
  + 插槽 A：T4 种子题库（PM 30 / 数据 30 / AI 30 / 其他空）
  + 插槽 B：挖题角度提示词
       PM：决策依据 / 北极星指标 / 用户洞察 / trade-off
       数据：方法严谨度 / 量化与归因 / 可解释性
       AI：评估指标 / 数据规模化 / hallucination & 安全
       其他：通用 STAR 框架
```

新加岗位 = 加插槽，不动主逻辑。

### 4.3 题库元数据

每道题除题面外存：
- `category`: T1-T5
- `source`: 来源说明（"反推自 [项目名]" / "对齐 JD 关键词 [...]" / "PM 通用题：北极星"）
- `difficulty`: 简单 / 中等 / 难（agent 自评）
- `status`: 未练 / 已练 / 待重练 / 已改进 / 未练-跳过
- `created_at`: 时间戳

`source` 是用户信任来源——让用户看到"为什么我要练这道"。

### 4.4 实现：单次 LLM 调用 + structured output

把简历结构化 + JD + 岗位类型一次喂给 Claude 4.7 Opus，让它一次输出 12 道题（JSON）。**不**多步 agent 串联——出题是 generation 任务，单次更稳。Agent 含量集中在下游 U-loop。

---

## 5. U-loop 机制（核心 Agent 含量）

### 5.1 五套 Rubric（不是一套 STAR 套所有题）

| 题类 | Rubric | 4 个维度 |
|---|---|---|
| T1 项目深挖 | STAR | Situation / Task / Action / Result |
| T2 outcomes 追问 | 量化严谨度 | Baseline 明确 / 归因清晰 / 显著性意识 / 业务意义 |
| T3 JD 能力对齐 | STAR + 框架 | 案例支撑 / 框架化思考 / 落地可行性 / 复盘视角 |
| T4 岗位通用题 | 结构化思考 | 拆解维度完整 / 优先级合理 / 风险/边界 / 可证伪 |
| T5 行为动机题 | 自洽 + 真诚 | 动机具体 / 与履历自洽 / 非套话 / 包含反思 |

每维度 0-3 分，总分 12，**≥ 9 算"完整"**可结束。

Rubric 是 hardcoded YAML 配置（5 套，每套 4 维度 + 评分指引），LLM 只负责按 rubric 打分 + 找最弱维度。

### 5.2 评估 + 追问生成（一次调用）

每轮用户答完后调用 LLM 一次，structured output 输出：

```json
{
  "scores": {"维度1": 2, "维度2": 1, "维度3": 0, "维度4": 3},
  "weakest_dimension": "维度3",
  "weakness_diagnosis": "用户没说明 baseline 怎么定的",
  "next_followup": "你说 GMV +30%，这个 baseline 是去年同期还是上月环比？"
}
```

启发式（"按 STAR 顺序补缺"）不可靠——最弱维度上下文相关。让 LLM 在同一次调用里完成评估 + 挑选 + 追问生成。

### 5.3 退出与重定向机制（三类信号）

**A. 结束类**（彻底关闭本题）：
1. 软退出（首选）：rubric 总分 ≥ 9 → agent 主动结束、给好评
2. 硬上限：最多 3 轮追问，未达 9 分维度直接写进改进建议
3. 用户主动结束："我答完了 / 下一题"

**B. 重定向类**（不结束本题，跳出当前轨道）：

4. 跳过本题："跳过 / 这题不会" → 标记"未练-跳过"，进下一题
5. 求提示（卡壳）："不知道 / 没思路 / 给点提示" → 提示模式：给思考框架（如"试试从用户场景、决策依据、量化结果三个角度切入"），不计入追问轮次
6. **换场景**（关键 UX）：
   - **用户主动**："举不出 / 这个例子太薄 / 能换一个吗"
   - **agent 主动**：识别用户例子撑不住考察意图（如问"实习中的领导力"用户答"帮同事改 PPT"）时主动给台阶
   - 机制：**释放场景维度（实习/项目/校园/生活），保留考察意图（领导力/决策/数据驱动）**
   - 必要时进一步松绑到相邻意图（"领导力" → "主动推动事情发生"）
   - 预算：场景切换重置 1 轮追问预算，同题最多切换 2 次（防止无限漂移）

**为什么场景切换是 D 区别于通用对话工具的核心**：通用工具不会主动识别"用户例子撑不住"并给台阶——要么死磕、要么放弃。

### 5.4 单题完整流程

```
出题
  ↓
用户答（第 1 轮）
  ↓
LLM 评估 rubric + 挑最弱维度 + 生成追问/触发结束
  ├─ 总分 ≥ 9 → 软退出 → 给评价
  ├─ 用户卡壳信号 → 提示模式（不计轮次）
  ├─ 用户主动结束/跳过 → 立即结束
  ├─ 用户/agent 触发场景切换 → 重置 1 轮预算（最多 2 次）
  └─ 不完整且未达上限 → 输出追问 → 用户答（下一轮）
  ↓
（最多 3 轮追问，否则硬退出）
  ↓
输出本题报告：rubric 各维度分数 + 改进建议 + 范例答案 + 状态更新
```

**范例答案**：题目结束时由 agent 根据题面 + 简历项目数据合成"如果你按 rubric 高分作答，可以这样说"的参考答案。

---

## 6. 输出形态：三种报告

### 6.1 单题报告

| 模块 | 内容 |
|---|---|
| 题面 + 元数据 | 题目、类别、来源、难度 |
| 对话 transcript | 用户每轮答 + agent 每轮追问（含场景切换提示）的完整记录 |
| Rubric 评分 | 4 维度分数 + 雷达图 + 总分 + 评级（优秀/良好/合格/需改进） |
| 改进建议 | 3 条具体可操作（不是"加强结构化思维"的废话） |
| 范例答案 | agent 合成的 rubric 高分版本 |
| 状态变更 | 已练（≥9）/ 待重练（<9）/ 未练-跳过 |

transcript 必须保留——既是用户复盘素材，也是简历演示最有说服力的证据。

### 6.2 题库总览（资产视图）

- 卡片网格：每题一卡，显示题面摘要 / 类别 tag / 状态 / 最高分 / 上次练习时间
- 筛选 & 排序：按类别 / 状态 / "最差分优先"
- 顶部统计条：未练 X / 已练 Y / 待重练 Z；rubric 4 维度全局平均分（看哪个维度反复失分）

### 6.3 整套面试报告（A 模式包装）

5 题连续答完后聚合：
- 总览：平均分、各类别平均分、用时、雷达图（5 题各类别均值）
- 高光 & 短板：哪几题答得好、哪几个 rubric 维度反复失分
- 下一步建议：基于短板维度从题库推荐重点重练
- 逐题汇总：每题分数 + 简评，可展开看完整 6.1

### 6.4 v1 不做

- ✗ 导出图片 / PDF / 分享卡片（用户截图即可，v1.5 再加）
- ✗ 进度趋势图（使用次数不足）
- ✗ 多次演练同题对比视图（v1.5）

### 6.5 工程实现

报告 = 结构化 JSON 数据 + Markdown 渲染。两张图：雷达图（4 维度）+ Bar chart（5 题分数对比，仅整套）。前端用 Recharts。

---

## 7. 技术栈

### 7.1 整体

```
前端: Next.js 16 (App Router) + shadcn/ui + Tailwind + Recharts
后端: Python FastAPI + Anthropic SDK (Claude 4.7 Opus) + SQLModel
持久化: SQLite
Agent 实现: 手写状态机 + structured output (Claude tool use / JSON schema)
```

### 7.2 各层选型理由

- **Agent 框架**：手写状态机。U-loop 状态机简单（5 类出口 + 3 轮上限），手写完全够；零框架学习成本；调试透明；首次做 agent 不被 LangChain/LangGraph 抽象层坑住
- **LLM**：Claude 4.7 Opus（开发期），上线后成本敏感切 Sonnet 4.6。**必须开 prompt caching**：简历 + JD + rubric 配置在一次 session 里反复复用，节省 70%+ 成本
- **前端**：Next.js + shadcn 出真产品质感（小红书演示、简历叙事都需要）；配合 v0 / Claude Code 写前端门槛低
- **后端**：Python（开发者舒适区，prompt 调试最快）；FastAPI + Pydantic 与 Claude structured output 天然契合
- **持久化**：SQLite + SQLModel；4 表（`resume_session` / `question` / `drill_attempt` / `report`）；未来迁 Postgres 平滑

### 7.3 部署（v1 必做，不留 v1.5）

- 前端：Vercel
- 后端：Railway / Fly.io（FastAPI 单容器）
- DB：SQLite 文件挂 Railway volume
- 配置：Claude API key、CORS、域名（v1 用 Vercel 默认域名即可）

部署在 Week 4 排 1 天专门窗口。

---

## 8. 评估方法

### 8.1 三个核心目的

1. **回归保护**：每次 prompt 改动后，新版本是否退化？
2. **垂直化证据**：MockInterview Agent vs 裸 Claude 对话的盲评胜率（简历金句源头）
3. **使用价值证明**：开发者本人面试季实战命中率（v1 之后持续追踪）

### 8.2 评估集

- **5 份真简历**：开发者本人 1 + 朋友 2（PM/数据各一）+ 网上脱敏样本 2（AI/其他）
- **3 份真 JD**：从招聘平台扒（PM/数据/AI 各一）
- **配对**：8-10 个有意义的简历-JD-岗位组合 → ~100 道生成题样本

### 8.3 自动评估 Pipeline（`eval/run_eval.py`）

| 评估项 | 方法 | 目标值 |
|---|---|---|
| 出题相关性 | 评分员 LLM 看（题 + 简历 + JD），打 0-3 分 | 平均 ≥ 2.2 |
| 追问深度有效性 | 跑 20 段模拟 U-loop（LLM 模拟用户给"中等质量"答），评分员看追问是否每轮击中最弱维度 | 命中率 ≥ 70% |
| 场景切换触发 | 5 段"用户例子明显薄弱"模拟答，看 agent 是否主动建议换场景 | 触发率 ≥ 80% |

### 8.4 vs 裸 Claude 盲评

- 5 个题目场景，同样输入
- 裸 Claude（通用 prompt） vs MockInterview Agent
- 评分员 LLM 盲评："哪个更像真实面试官的提问？哪个追问更深？"
- 目标：MockInterview Agent 胜率 ≥ 70%

→ 简历金句："vs baseline 盲评胜率 X%"。

### 8.5 实战命中率（v1 后持续追踪）

每次真实面试后填表：被问到的 N 道题里，agent 提前练过/预测过的占比。
→ 简历金句："在真实秋招 N 场面试中，agent 提前预演命中率 X%"。

### 8.6 工程结构

```
eval/
├── datasets/
│   ├── resumes/          # 5 份脱敏简历
│   ├── jds/              # 3 份 JD
│   └── pairs.yaml        # 简历-JD-岗位配对
├── judges/
│   ├── relevance.py
│   ├── drilling.py
│   └── baseline_compare.py
├── run_eval.py
└── reports/              # 每次评估输出 markdown 报告
```

---

## 9. 4 周开发日历

### Week 1 / 基础设施 + 出题引擎

| 日 | 任务 |
|---|---|
| Mon | mono repo 骨架 + Next.js + FastAPI + SQLModel 4 表 schema + Git/GitHub |
| Tue | PDF 上传 endpoint + pdfplumber 抽文本 + Claude 结构化解析 |
| Wed | 5 套 rubric YAML 配置 + 4 个岗位插槽种子题库（curate 30 题/岗） |
| Thu | 出题引擎 LLM 调用（structured output 12 道题 + 元数据），处理 JD 有/无分支 |
| Fri | 题库 CRUD endpoints + 题目 status 状态机 |
| **末** | **交付**：API 跑通 简历 → 出题 → 入库 |

### Week 2 / U-loop 单题（最重的一周）

| 日 | 任务 |
|---|---|
| Mon | U-loop 状态机骨架 + `POST /drill/{id}/answer` |
| Tue | 评估 + 追问生成 prompt（一次调用输 scores + weakest + diagnosis + next_followup） |
| Wed | 6 个退出/重定向出口判定（软退出/硬上限/主动结束/跳过/提示/换场景） |
| Thu | 场景切换 prompt + 范例答案合成 prompt |
| Fri | drill_attempt + report 持久化 + 单题端到端跑通 |
| **末** | **交付**：API 完整跑一道 U-loop，6 种出口都能触发 |

### Week 3 / 前端 + 报告

| 日 | 任务 |
|---|---|
| Mon | Next.js + shadcn 骨架；简历上传页；前后端联调 |
| Tue | 题库总览页（卡片网格 + 筛选 + 顶部统计） |
| Wed | 单题演练页（聊天 UI + 流式输出 + Markdown 渲染） |
| Thu | 单题报告页（雷达图 + 4 维度 + transcript + 范例答案 + 改进建议） |
| Fri | 整套模式包装（开始 → 5 题串联 → 整套报告） |
| **末** | **交付**：本地完整流程跑通，自己用一次 |

### Week 4 / 评估 + 部署 + 收尾

| 日 | 任务 |
|---|---|
| Mon | 收集 5 简历 + 3 JD + 配对；写 eval/datasets/pairs.yaml |
| Tue | 评估 pipeline（3 个 judge：relevance / drilling / baseline-compare） |
| Wed | 跑评估 + 人工抽检 + prompt 调优 1 轮 |
| Thu | **部署**：Vercel 前端 + Railway 后端 + Claude API key env + DB volume |
| Fri | 简历金句汇总 + 小红书 demo 视频 + 截图 + README |
| **末** | **交付**：上线 + 评估报告 + 简历金句 + 小红书 4 条进度 |

### 风险预案

| 风险 | 应对 |
|---|---|
| Week 2 溢出（U-loop 比预想复杂） | 砍 Week 4 小红书素材到必要 demo 视频 + 1 张截图 |
| Week 3 前端慢（Next.js 不熟） | 整套模式 A 包装挪 Week 4，单题流程优先 |
| Week 4 部署卡住 | 本地跑 + 录视频；部署延到第 5 周 buffer |
| 评估发现质量不达标 | 优先调出题/追问 prompt（最高 ROI），不追求 100% 维度达标 |

### 简历叙事节奏（每周末发小红书 1 条）

- W1：「我做了个 AI 面试 agent。第 1 周搞定简历智能解析」+ 解析字段截图
- W2：「agent 现在能多轮追问，连'例子太薄能换一个吗'都识别」+ 场景切换对话截图
- W3：「前端跑起来了：题库 / 单题演练 / 完整模拟面试 / 雷达图报告」+ UI 截图集
- W4：「线上版已部署，对比裸 Claude 在 PM 场景盲评胜率 X%」+ 评估报告 + demo 视频

---

## 10. 数据库 Schema

```sql
-- 一次"上传简历"会话（关联 4 表的根）
resume_session(
  id, user_id (v1 单用户固定 1),
  resume_json,              -- 结构化简历 4 字段
  jd_text,                  -- 可空
  company_name,             -- 可空
  role_type,                -- pm / data / ai / other
  created_at
)

-- 题库
question(
  id, resume_session_id,
  category,                 -- T1..T5
  text,                     -- 题面
  source,                   -- 来源说明
  difficulty,               -- easy/medium/hard
  status,                   -- not_practiced / practiced / needs_redo / improved / skipped
  best_score,               -- 历史最高分
  last_attempt_at,
  created_at
)

-- 单次 U-loop 演练记录
drill_attempt(
  id, question_id,
  transcript_json,          -- [{role, text, round}, ...]
  rubric_scores_json,       -- 最终各维度分
  total_score,              -- 0-12
  exit_type,                -- 终止状态：soft / hard_limit / user_end / skip
  scenario_switch_count,    -- 0/1/2，本题场景切换次数（loop 内事件，不是终止状态）
  prompt_mode_count,        -- 本题进入提示模式的次数（loop 内事件，不是终止状态）
  followup_rounds,          -- 实际追问轮数（不含场景切换重置和提示模式回合）
  exemplar_answer,          -- agent 合成的范例答案
  improvement_suggestions,  -- 3 条改进建议
  started_at, ended_at
)

-- 整套面试报告（A 模式包装聚合）
report(
  id, resume_session_id,
  drill_attempt_ids_json,   -- 5 个 drill_attempt 的 id
  total_avg_score,
  category_avg_scores_json,
  highlights_json,
  weaknesses_json,
  next_steps_json,
  created_at
)
```

v1 单用户、无登录；`user_id` 字段保留以便未来扩展。

---

## 11. 非目标（明确不做）

- ✗ 网申自动填表
- ✗ 岗位聚合 / 招聘信息爬虫
- ✗ B 候选人情报数据层（v1.5）
- ✗ 非核心岗位精细化体验（仅走通用兜底）
- ✗ 语音 / 视频面试模拟
- ✗ 账号体系 / 登录注册
- ✗ 报告导出（图片/PDF/分享卡片）
- ✗ 进度趋势图、多次演练同题对比

---

## 12. 已知前提与约束

- 开发者：1 人、4 周、agent 经验为零、调过 LLM API、Python 舒适区
- 求职方向：产品 / 数据
- 主开发环境：Claude Code
- LLM 成本：必须开 prompt caching；开发期 Opus 4.7，上线后视成本切 Sonnet 4.6
- 数据来源：用户输入（简历 PDF + JD 文本）；无外部爬虫

---

## 13. 核心设计原则（决策时回看）

1. **YAGNI**：v1 只做 A+C+D 必需；任何加 1 周以上工程量的功能必须挑战必要性
2. **UX 完整度优先于 MVP 砍功能**：开发者已表态愿为体验加分投入工程时间
3. **场景切换 UX 是 D 的灵魂**——不能因为时间紧就砍掉
4. **5 套 rubric 不是奢侈品**——一套 STAR 套所有题会让评估和追问不专业
5. **Agent 含量集中在 U-loop**——出题用单次调用，不要为了"看起来很 agent"加多步
6. **每周末必须有可演示成果**——4 周一次性大爆炸是失败模式
