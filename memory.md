# MockInterview Agent — 进度日志

> 每完成一个 task 在最上方追加一条记录。便于跨 session 快速接上前序工作。
>
> **Source plan**: [plans/2026-04-27-mock-interview-agent-v1.md](plans/2026-04-27-mock-interview-agent-v1.md)
> **Source spec**: [docs/superpowers/specs/2026-04-27-mock-interview-agent-v1-design.md](docs/superpowers/specs/2026-04-27-mock-interview-agent-v1-design.md)
> **立项文档**: [PROJECT.md](PROJECT.md)

## 记录格式

每条记录包含：
- **任务 ID + 名称**（plan 里 Task X.Y 对应）
- **完成时间**（YYYY-MM-DD）
- **做了什么**（1-2 句话摘要）
- **改动的文件**（New / Modified 列出）
- **关键决策 / 坑点**（有则记，无则略）
- **验证方式**（跑什么命令、期望什么输出）
- **Commit hash**（短哈希即可）

---

<!-- 最新记录追加在这条注释下方 -->

## 2026-04-27 · Task 4.5 — run_eval.py orchestrator

**Done**: `eval/run_eval.py` 220 行，把 4.1-4.4 的 dataset / 3 judge / simulator 与 backend 出题引擎串联起来。每个 pair：(1) 读简历 + JD → `parse_resume_text` 调 backend Claude prompt 转结构化 → `generate_questions` 出 12 题；(2) 12 题逐个调 `relevance.score_question` 打契合度；(3) 取前 3 道 T1 题，每题 2 轮模拟 U-loop（`user_simulator.simulate_answer` 中等用户答 + `evaluate_and_followup` agent 评 + `drilling.judge_followup` 判命中最弱）；(4) 第一道 T1 题做 baseline_compare 盲评。每个 LLM 调用都 try/except 兜底，单点失败不影响后续 pair。Markdown 报告写到 `eval/reports/<YYYY-MM-DD>.md`，含 Summary（3 个核心指标 + 阈值）/ Per-pair detail 表 / Raw JSON。

**Files**:
- New: `eval/run_eval.py`

**Decisions / gotchas**:
- 跑法：`cd backend && env -u VIRTUAL_ENV uv run python ../eval/run_eval.py`（需 ANTHROPIC_API_KEY）—— backend venv 里跑因为要 import backend modules，eval 自己的 venv 是为子任务（不被这个脚本用）
- `sys.path.insert` 顺序：backend/src 先（line 19）→ eval/ 后（line 26）—— 否则 backend 模块找不到
- `parse_resume_text` 故意复用 backend 的 prompt（apples-to-apples eval）—— 评估的是端到端 pipeline 不是某段
- 每个 pair 估算 LLM 调用：1 (resume parse) + 1 (gen) + 12 (relevance) + 6×3 = 18 (drilling sim+eval+judge) + 3 (baseline compare) ≈ 35 calls/pair；8 pair × 35 = ~280 calls；Opus 4.7 + caching 估 $5-15
- 已知小坑：(a) `OUT.mkdir(exist_ok=True)` 在 module load 时执行——只 import 也会创建 reports/；(b) `parse_resume_text` 每个 pair 调一次不缓存结构化结果——v1 acceptable，未来若成本敏感可加 disk cache
- `<placeholder mid-quality answer>` 在 baseline compare 的 ours_pair 生成里——这是有意 stub，让 ours pair 的 first_followup 也由 evaluate_and_followup 产生（与 baseline pair 同样调 LLM 一次），保持公平比较

**Verify**: `import run_eval` 在 backend venv 通过；待 Task 4.6 跑真 API

**Commit**: `a6bd04b`

---

## 2026-04-27 · Task 4.4 — Baseline comparison judge

**Done**: `eval/judges/baseline_compare.py` 3 函数：(1) `baseline_pair(client,*,resume,jd)` 用裸 Claude（无 rubric / 无种子题库）出题 + 第一轮追问，作为 baseline；(2) `judge_blind(client,*,resume,jd,a_pair,b_pair)` 盲评 A/B 哪个更像真实面试，返 `{winner, rationale}`；(3) `shuffled_label_pair(ours, baseline)` 50/50 随机 A/B 标签让评审无法 pattern match。这是 v1 最强简历金句"vs baseline 盲评胜率 X%"的数据源。

**Files**:
- New: `eval/judges/baseline_compare.py`

**Decisions / gotchas**:
- 标签随机 shuffle 是盲评 validity 的关键——否则 judge LLM 可能 systematic bias 倾向某一侧
- baseline 故意用极简 prompt（"基于简历+JD 提问"），不传任何 rubric / 种子题库 / 5 类题型分布——对比的是 vertical agent 设计 vs 通用对话能力
- 跑评估时 (Task 4.5)：每个 pair 调一次 baseline_pair + 一次 judge_blind = 2 次 LLM 调用，加上 ours_pair（来自 backend 出题引擎）
- 模型选 Opus 4.7 评审（不降级到 Sonnet）—— 评估 validity 比成本重要

**Verify**: 文件存在，3 函数齐；待 Task 4.5 端到端验证

**Commit**: `de821fb`

---

## 2026-04-27 · Task 4.3 — User simulator + drilling judge

**Done**: `eval/simulators/user_simulator.py` `simulate_answer(client, *, resume, question, transcript)`：LLM 扮"中等质量"候选人答题（rubric 5-7/12 分定位，故意漏 baseline/归因/业务意义），不卡壳/不主动结束/不要求换场景，让 agent 追问质量被实际暴露。`eval/judges/drilling.py` `judge_followup(client, *, question, rubric_dims, last_answer, followup)`：判断面试官某一轮追问是否击中候选人答案最弱维度，返 `{"hit_weakest": bool, "rationale": "..."}`。

**Files**:
- New: `eval/simulators/__init__.py`, `eval/simulators/user_simulator.py`, `eval/judges/drilling.py`

**Decisions / gotchas**:
- 模拟用户的"中等质量"刻意校准：太强 agent 没法追问、太弱所有维度都低无法 discriminative
- 模拟用户**故意不卡壳/不主动结束/不要求换场景**——这条评估专测追问命中率，其他 UX 路径单独评（Phase 4 后续可加）
- Drilling judge 的 prompt 同样精简，重点是 `hit_weakest` 布尔结果（用于命中率分子分母）

**Verify**: 文件存在；待 Task 4.5 编排时端到端验证

**Commit**: `e393cf2`

---

## 2026-04-27 · Task 4.2 — Relevance judge

**Done**: `eval/judges/relevance.py` `score_question(client, *, resume, jd, question)` 函数：用 Claude 4.7 给每道生成题打 0-3 分契合度（0=完全无关 / 1=牵强 / 2=相关 / 3=精准引用具体项目）。系统 prompt 带 `cache_control` ephemeral 缓存（同 pair 内多题复用）；resume 截 2000 chars，JD 截 1200 chars 控成本。

**Files**:
- New: `eval/judges/__init__.py`, `eval/judges/relevance.py`

**Decisions / gotchas**:
- eval 用独立的 `Anthropic()` client，不 import backend 的 `client.py`——eval 是 self-contained 子项目
- model id `claude-opus-4-7` 硬编码：未来若调评分模型版本，这里是单点修改
- 没写单测：eval helper 在 Task 4.5 的 `run_eval.py` 端到端测

**Verify**: 文件存在；待 Task 4.5 编排时端到端验证

**Commit**: `c22fb23`

---

## 2026-04-27 · Task 4.1 — Eval dataset curation（Phase 4 起步）

**Done**: 建 `eval/` 评估子项目（uv-managed，与 backend 分离）：5 份合成简历（self_pm/friend_pm/friend_data/anon_ai/anon_other，每份 ~770-960 chars，含 NTU 数据科学硕士 / 字节-腾讯实习 / Shopee 数据科学家 / AI 产品 / 四大咨询五种画像，每份带 SYNTHETIC PLACEHOLDER 注释）+ 3 份合成 JD（PM 字节 / 数据 Shopee / AI alpha）+ pairs.yaml 8 个评估配对（覆盖 4 个 role × JD 有/无变种 + 1 个 PM 跨域 AI alpha 边界 case）+ pyproject.toml（anthropic/pyyaml/pydantic/rich）+ .gitignore（.venv/__pycache__/reports/uv.lock）。`uv sync` 装了 21 个包成功。

**Files**:
- New: `eval/pyproject.toml`, `eval/.gitignore`, `eval/datasets/pairs.yaml`, `eval/datasets/resumes/{self_pm,friend_pm,friend_data,anon_ai,anon_other}.txt`, `eval/datasets/jds/{pm_bytedance,data_shopee,ai_alpha}.txt`（共 11 文件）

**Decisions / gotchas**:
- 用户没提供真实简历——先用合成数据让 pipeline 可立即跑；用户面试季再 swap 真实脱敏内容
- 简历内容刻意贴近真实（带量化结果如"GMV +18%" "AUC 0.83"），让出题引擎的反向挖题能力被实际测到
- `eval/` 是独立 uv 项目（自己的 pyproject.toml + .venv），不污染 backend
- `uv.lock` 不入 git（eval 是 dev 工具不部署，锁文件加噪音）
- 8 个 pair 包含 1 个 cross-domain 边界 case：`pm_alpha_self`（senior PM 简历 vs AI 公司 JD），测出题引擎在简历-JD 不完全对齐时的退化模式

**Verify**: 11 文件 + `eval/.venv/` 安装成功（21 个 deps）；`pairs.yaml` 8 个配对覆盖 4 roles + JD 有/无变种

**Commit**: `4bad10c`

---

## 2026-04-27 · Phase 3 完成 + Task 3.7 — Mock report page

### Task 3.7 内容

**Done**: `/mock/[id]/report` 路由：顶部"整套面试报告" + 平均分 X.X/12 + 返回题库；ScoreBarChart（每题得分柱状图，Y 域 [0, 12]）；2 列布局：左 高光（≥9 题列表 / 空时显示"本场没有满分题——下次冲刺！"），右 短板（rubric 维度均分 < 2，含来源 category）；下方 下一步建议（next_steps ul 列表）+ 逐题汇总（每行链接到 `/report/{drill_id}` 单题报告页）。`pnpm build` 8 routes 成功。

**Files**:
- New: `frontend/src/components/score-bar-chart.tsx`, `frontend/src/app/mock/[id]/report/page.tsx`

**Decisions / gotchas**:
- ScoreBarChart 复用 recharts（Task 3.5 装的依赖）；与 RadarChart 同等地位
- 逐题汇总每行 `Link` 到单题报告页——给"看完整套报告 → 钻进某一题细节"的导航闭环
- 报告页是 client component，`params Promise` + `use()`，无 useSearchParams 不需 Suspense

**Verify**: `cd frontend && pnpm build` → `Compiled successfully`，8 routes

**Commit**: `caf872c`

### Phase 3 总结

- ✅ 7 个 task 全部完成（Task 3.1-3.7）+ Task 3.6 顺手补的后端 mock endpoints
- ✅ 后端：52 单测全过；前端：build clean 0 TS error
- ✅ 8 个前端路由：`/`（上传）→ `/library?session=...`（题库）→ `/drill/[id]`（单题演练，id=question_id）→ `/report/[id]`（单题报告，id=drill_id）/ `/mock?session=...`（mock 入口）→ `/mock/[id]`（mock 驱动）→ `/mock/[id]/report`（整套报告）
- ✅ 后端新增 endpoints：`POST /mock`, `GET /mock/{id}`, `POST /mock/{id}/advance`, `GET /mock/{id}/report`, `GET /reports/mock/{id}` alias
- ✅ MockSession 表 + mock_aggregator 模块（按 category / 维度均值聚合，生成 highlights / weaknesses / next_steps 中文文案）
- ✅ git tag `w3-done`

下一步：进入 **Phase 4 Week 4** —— 评估 + 部署 + 收尾（9 个 task）：
1. 评估集（5 简历 + 3 JD + pairs.yaml）
2. relevance judge
3. user simulator + drilling judge
4. baseline_compare judge
5. run_eval.py orchestrator
6. 跑评估 + 调 prompt 1-2 轮（**这一步需要真 ANTHROPIC_API_KEY**，是 v1 唯一阻塞性的 LLM 调用环节）
7. backend Dockerfile + Railway 部署
8. Vercel frontend 部署
9. README + 简历金句 + 小红书素材

Phase 4 Task 4.6（跑评估调 prompt）和 Task 4.7-4.8（部署）是**用户必须参与**的环节，不能 100% subagent 化——需要 API key + Vercel/Railway 账户。

---

## 2026-04-27 · Task 3.6 — Mock interview mode (5 题串联)

**Done**: 同时改 backend + frontend。Backend：加 `MockSession` 表（`question_ids` JSON / `drill_attempt_ids` JSON / `current_index` / `status` / 时间戳）+ `routes/mock.py` 4 endpoint（`POST /mock` 起会话挑 5 题优先 5 个不同 category，`GET /mock/{id}`、`POST /mock/{id}/advance` 推进当前 drill_attempt_id 到列表 + index++ + 全完结时 status="ended"，`GET /mock/{id}/report` 拉聚合）+ `agent/mock_aggregator.py` 聚合逻辑（按 category 平均分、识别 highlights ≥9、识别 weakness 维度均值<2 排序、生成 next_steps 文案）+ `/reports/mock/{id}` alias。2 单测全过共 52 passed。Frontend：`/mock` 入口页（自动起会话跳详情）+ `/mock/[id]` 驱动页（依次起 drill / 答 / 答完 advance 到下一题 / 全完跳报告）。`pnpm build` 7 routes。

**Files**:
- Modified: `backend/src/mockinterview/db/models.py`（+ MockSession 表）, `backend/src/mockinterview/routes/reports.py`（+ /reports/mock/{id} alias）, `backend/src/mockinterview/main.py`（注册 mock router）
- New: `backend/src/mockinterview/routes/mock.py`, `backend/src/mockinterview/agent/mock_aggregator.py`, `backend/tests/test_routes_mock.py`, `frontend/src/app/mock/page.tsx`, `frontend/src/app/mock/[id]/page.tsx`

**Decisions / gotchas**:
- 新增表（不是改现有表的列）—— SQLite `metadata.create_all` 自动加新表，**不需要删 app.db**（与 Task 2.7 的 `state_snapshot` 加列那次不同）
- 起会话挑题策略：先按 status / id 排序得到候选，**第一阶段**优先挑 5 个不同 category（保证 mock 覆盖广），**第二阶段**用其余题填到 5 道凑齐
- 聚合规则：highlights = total_score ≥ 9 的题列表；weaknesses = rubric 维度均分 < 2 的，按 avg 排序取前 5；next_steps = top 3 weakness 拼成"重点重练 [类目] 中维度「key」（均值 X.X/3）"中文文案
- ⚠️ Driver 页指向 `/mock/{id}/report`——Task 3.7 补
- 入口页 `useSearchParams` 包了 Suspense；driver 用 `params Promise` 不需 Suspense
- mock_aggregator 的 `weaknesses` 排序后取前 5：避免维度过多导致报告杂乱

**Verify**:
- `cd backend && uv run pytest -v` → `52 passed`
- `cd frontend && pnpm build` → `Compiled successfully`，7 routes

**Commit**: `7139cc1`

---

## 2026-04-27 · Task 3.5 — Single-question report page (radar chart)

**Done**: 装 `recharts ^3.8.1`（与 React 19.2.4 无 peer dep 冲突）。`/report/[id]` 路由（id = drill_id）：顶部 题目 + category + 退出方式/追问轮数/场景切换次数/求提示次数信息条 + "返回题库" 按钮；2 列布局：左 RadarChart（rubric 4 维度评分，0-3 域）+ 总分（X/12 + 优秀/良好/合格/需改进 评级），右 改进建议 ol；下方 范例答案 Card（whitespace-pre-wrap）+ 完整 transcript（TranscriptView 包 ChatInterface）。`pnpm build` 5 路由成功。

**Files**:
- New: `frontend/src/app/report/[id]/page.tsx`, `frontend/src/components/radar-chart.tsx`, `frontend/src/components/transcript-view.tsx`
- Modified: `frontend/package.json`（+ recharts ^3.8.1）, `frontend/pnpm-lock.yaml`

**Decisions / gotchas**:
- 评级阈值与 spec §6.1 对齐：≥11 优秀 / ≥9 良好（软退出阈值）/ ≥6 合格 / else 需改进
- RadarChart `"use client"`（recharts 是 client-only），所以 `/report/[id]` 路由是动态（`ƒ`）—— SSR 不渲染 chart，CSR 才出
- TranscriptView 是 ChatInterface 的薄 wrapper，目的是给 report 页面留布局灵活性（未来可以切换 transcript 渲染样式）
- recharts 3.x 与 React 19 兼容性：装的时候 0 warning，build clean——稳

**Verify**: `cd frontend && pnpm build` → `Compiled successfully`，5 routes（含新 `/report/[id]`）

**Commit**: `aef4044`

---

## 2026-04-27 · Task 3.4 — Drill page (chat UI)

**Done**: `/drill/[id]` 路由（id = question_id，进页面后调 `startDrill` 起 session）。`ChatInterface` 组件：消息气泡（user 右对齐 primary 色 / agent 左对齐 muted 色）+ 自动滚动（`useEffect` on transcript）+ scenario_switch 加 amber ring + prompt_mode 加 blue ring + 顶部 emoji 标签（"↔ 换场景" / "💡 思考框架"）。底部 Textarea + 4 个快捷按钮（跳过 / 换场景 / 求提示 / 结束）—— 按钮**只填充输入框**不直接发送（用户可编辑后再发）。题目 ENDED 后 1.2s 跳 `/report/{drill_id}`。`pnpm build` 4 路由成功。

**Files**:
- New: `frontend/src/components/chat-interface.tsx`, `frontend/src/app/drill/[id]/page.tsx`

**Decisions / gotchas**:
- Next.js 16 App Router 参数现在是 `params: Promise<{id: string}>`，要 `use(params)` 解包——React 19 标准 pattern
- 快捷按钮"换场景"按钮填的是"能换个例子吗"——故意命中 Task 2.6 修补过的 `换一个/换个/再换` regex，这是端到端契合的关键
- 4 路由（/、/library、/drill/[id] 动态、/_not-found）；`/report/[drill_id]` Task 3.5 加，1.2s redirect 当前会 404
- ChatInterface 设计可在 Task 3.5（报告 transcript view）和 Task 3.6（mock 模式）复用——单一职责的小组件

**Verify**: `cd frontend && pnpm build` → `Compiled successfully`，4 routes

**Commit**: `507e7b6`

---

## 2026-04-27 · Task 3.3 — Library page

**Done**: `/library` 路由：QuestionCard（5 状态颜色 / category & difficulty badge / 最高分 / 最近练习时间）+ LibraryStatsBar（顶部 4 数字：题库 / 未练 / 已练 / 待重练）+ T1-T5 分类按钮筛选。卡片点击跳 `/drill/{id}`，"开始模拟面试" 按钮跳 `/mock?session=...`。`pnpm build` 1.1s 0 错误。

**Files**:
- New: `frontend/src/components/question-card.tsx`, `frontend/src/components/library-stats-bar.tsx`, `frontend/src/app/library/page.tsx`

**Decisions / gotchas**:
- ⚠️ **Next.js 16 必须把 `useSearchParams` 包进 `<Suspense>`**，否则 build 会失败"Missing Suspense boundary"。结构：`LibraryPage` default export = Suspense wrapper + fallback；`LibraryView` 内部组件实际用 hook。下游用 `useSearchParams` 的页面（Task 3.6 mock）也要复制这个 pattern
- QuestionCard 的 `STATUS_VARIANT` 把 `improved` 映射到 `default`（同 `practiced`）：UI 上区分不大，下游若想要金色 IMPROVED 视觉标识可加 ring
- 5 个状态有色彩区分：未练 outline / 已练 default / 待重练 destructive / 已改进 default / 已跳过 secondary

**Verify**: `cd frontend && pnpm build` → `Compiled successfully in 1095ms`，3 routes（/、/library、/_not-found）

**Commit**: `dce5d58`

---

## 2026-04-27 · Task 3.2 — Upload page

**Done**: 替换 `frontend/src/app/page.tsx` 的占位为 4 段式上传表单：UploadZone（拖拽 + click，仅接 PDF）+ RoleSelector（4 卡片：产品/数据/AI/其他）+ JD textarea（可选）+ 公司 input（可选）。提交按钮在 file && role 都填后激活，busy 时显示"解析中…可能需要 30-60 秒"，错误用 `text-destructive` 红色。成功后 `router.push("/library?session={id}")`（route Task 3.3 加）。`pnpm build` 1.1s 0 错误。

**Files**:
- Modified: `frontend/src/app/page.tsx`
- New: `frontend/src/components/role-selector.tsx`, `frontend/src/components/upload-zone.tsx`

**Decisions / gotchas**:
- 复用已有 shadcn primitives（Button/Input/Label/Textarea）+ 已装的 `cn` util，无需 `pnpm dlx shadcn add`
- UploadZone 拖拽视觉反馈：`dragOver` state + Tailwind `border-primary bg-primary/5`
- 提交流程内联了 `uploadResume` + `generateQuestions` 两个 API 串联——简化首屏 UX，不需要中间状态页面
- /library 路由不存在（Task 3.3 加）——点击"开始挖题"目前会 404 后跳转，build 不报错（Next.js 16 客户端路由 lazy）

**Verify**: `cd frontend && pnpm build` → `Compiled successfully in 1104ms`

**Commit**: `27b3b04`

---

## 2026-04-27 · Task 3.1 — TS types + complete API client（Phase 3 起步）

**Done**: `frontend/src/lib/types.ts` 10 个 type 与 backend Pydantic schema 一一对应（Category/Difficulty/RoleType/QuestionStatus/ExitType + ResumeUploadResponse/Question/TranscriptTurn/DrillResponse/SingleReport/Rubric/RubricDimension/MockSession/MockReport）。`frontend/src/lib/api.ts` 重写：保留 ApiError + isJsonBody（Task 1.6 修复），加 `jsonRequest<T>` 内部 helper，加 10 个 typed wrapper（uploadResume / generateQuestions / listQuestions / startDrill / answerDrill / getDrillReport / startMock / getMock / getMockReport + 保留 api/health）。`pnpm build` 0 TS error 通过。

**Files**:
- New: `frontend/src/lib/types.ts`
- Modified: `frontend/src/lib/api.ts`

**Decisions / gotchas**:
- mock 相关 3 个 wrapper（`startMock` / `getMock` / `getMockReport`）和 2 个 type（`MockSession` / `MockReport`）引用了**还不存在**的后端 endpoint——Task 3.6 才加后端。前端先提前定义保持一致编译，是 plan 有意安排
- `uploadResume` 故意绕过 `jsonRequest`：FormData 上传需要浏览器自动管理 multipart Content-Type 边界，不能注 `application/json` 头
- 类型对齐验证：backend 的 datetime 序列化为 ISO string → frontend 用 `string` 而非 `Date`；nullable 字段（best_score / last_attempt_at）用 `T | null`
- 用户简历 PDF（`吴亦菲_简历_南洋理工大学_27届.pdf`）在 repo root 未入 git——后续考虑 `.gitignore` 加 `*.pdf` 防止意外提交简历隐私

**Verify**: `cd frontend && pnpm build` → `Compiled successfully in 1.4s`

**Commit**: `334e8b9`

---

## 2026-04-27 · Phase 2 完成 + Task 2.8 — Single-question report endpoint

### Task 2.8 内容

**Done**: `routes/reports.py` 新增 `GET /reports/drill/{drill_id}` endpoint，聚合 DrillAttempt 持久化数据 + Question 元信息 + rubric YAML 配置（按 `q.category` 实时从 YAML 取） → 返 `SingleReport` Pydantic 模型（14 字段：drill_id / question_id / question_text / category / transcript / rubric / rubric_scores / total_score / exit_type / scenario_switch_count / prompt_mode_count / followup_rounds / exemplar_answer / improvement_suggestions）。1 单测端到端覆盖（起 drill → 软退出答 → 拉报告）。

**Files**:
- New: `backend/src/mockinterview/routes/reports.py`, `backend/tests/test_routes_reports.py`
- Modified: `backend/src/mockinterview/main.py`（注册 reports router）

**Decisions / gotchas**:
- `exit_type` 在 fresh persist 时是 `ExitType.SOFT` enum，从 JSON load 时是 string——用 `.value if hasattr(...) else ...` 双路守卫（spec verbatim）
- `load_rubric` 的 lru_cache：第一次请求读 YAML 后续请求走内存——同时满足 spec "loaded at request time" 意图和性能
- Phase 3 前端的 radar chart / report 页面将消费这个 endpoint

**Verify**: `cd backend && uv run pytest -v` → `50 passed in 3.59s`

**Commit**: `67984e5`

### Phase 2 总结

- ✅ 8 个 task 全部完成（Task 2.1-2.8 + 1 个 Task 2.1 regex 回填）
- ✅ 50 单测全过；Phase 1 26 单测 + Phase 2 24 单测
- ✅ U-loop 完整功能：6 exits（USER_END / SKIP / SOFT / HARD_LIMIT）+ 2 redirects（STUCK 提示模式 / SWITCH_SCENARIO 场景切换）+ budget caps（switch ≤2 / followup ≤3 / soft threshold 9）
- ✅ HTTP 链路：`POST /drill` → `POST /drill/{id}/answer` × N → `GET /reports/drill/{id}`
- ✅ 服务端无状态（state_snapshot JSON 列），Phase 4 部署可水平扩展
- ✅ git tag `w2-done`
- ⏳ 已记录的待办（不阻塞）：
  - Schema 改动后老 app.db 需手动删（Phase 4 加 Alembic 或文档化）
  - 测试 conftest 共享 dev DB engine，测试与开发环境耦合（Phase 3 加更多测试时切 in-memory 并 override `get_session`）

下一步：进入 **Phase 3 Week 3** —— 前端 + 报告（7 个 task：Next.js 16 页面 + shadcn 组件 + Recharts 雷达图 / bar chart + 整套面试模式 5 题串联）。

---

## 2026-04-27 · Task 2.7 — Drill API endpoints + persistence

**Done**: 3 个 HTTP endpoint：`POST /drill`（起会话）、`POST /drill/{id}/answer`（推进）、`GET /drill/{id}`（读）。`agent/drill_storage.py` 纯 (de)serialization：`to_snapshot(DrillState) → dict` + `from_snapshot(dict) → DrillState` 互逆。`DrillAttempt` 加 `state_snapshot` JSON 列存完整 state——服务端无状态，每次请求重新 hydrate。题目 ENDED 时：finalize fields (exit_type, total_score) + 非 skip exit 调 `synthesize_exemplar` + 更新 `Question.status`/`best_score`。3 单测全过，全套 49 passed。

**Files**:
- Modified: `backend/src/mockinterview/db/models.py`（加 `state_snapshot: dict | None`）, `backend/src/mockinterview/main.py`（注册 drill router）
- New: `backend/src/mockinterview/agent/drill_storage.py`, `backend/src/mockinterview/routes/drill.py`, `backend/tests/test_routes_drill.py`

**Decisions / gotchas**:
- ⚠️ **SQLite schema migration 限制**：`metadata.create_all()` 跳过已存在的表——给 `drill_attempt` 加 `state_snapshot` 后，老 `data/app.db` 不会自动加列。**任何复用旧 app.db 的人必须删 `backend/data/app.db` 才能拿到新 schema**。Phase 4 部署前考虑 (a) 加 Alembic 迁移工具，或 (b) 文档化"v1 单用户、schema 改动时手动删 db"
- ⚠️ **测试 DB 隔离问题**：当前 conftest 用 `db.session.engine`（真实 `data/app.db`），不是 in-memory engine——测试会污染 dev DB（创建临时 ResumeSession / Question / DrillAttempt 行）。Code reviewer 之前在 Task 1.2 也提过这个，目前 OK 因为测试都正确清理（每次新建 ResumeSession），但**Task 2.8+ 加更多测试时考虑 conftest 改用 in-memory engine 且 override `get_session` dep**
- 服务端无状态设计：DrillState 完整 snapshot 进 `state_snapshot` 列，每次 `POST /drill/{id}/answer` 反序列化 → `advance()` → 重新序列化。这样可以水平扩展（Phase 4 部署时不会因为多实例而坏）
- ENDED 时只对 non-skip exit 合成 exemplar：跳过题没必要给范例答案
- 题目状态映射：`SKIP` → `SKIPPED`；`>=9` → 之前最高 ≥9 时 `IMPROVED` 否则 `PRACTICED`；其他 → `NEEDS_REDO`

**Verify**: `cd backend && uv run pytest -v` → `49 passed`

**Commit**: `de62e87`

---

## 2026-04-27 · Task 2.6 — Drill state machine（U-loop 核心 boss task）

**Done**: 写 `agent/drill_loop.py` ~135 行：`DrillState` dataclass（11 字段）+ `DrillStatus` enum + `start_drill(*,question_id,question_text,category,resume_json,original_intent)` 起 session 返初始 state + `advance(state, user_text)` 状态机驱动函数。后者按下面 6 个 exit/redirect 路径之一处理输入：

1. **END**（`UserSignal.END`）→ `exit_type=USER_END`，状态机停
2. **SKIP**（`UserSignal.SKIP`）→ `exit_type=SKIP`，状态机停
3. **STUCK**（`UserSignal.STUCK`）→ 调 `give_thinking_framework`，加 `kind="prompt_mode"` transcript turn，**不增 followup_rounds**，`prompt_mode_count++`
4. **SWITCH_SCENARIO**（`UserSignal.SWITCH_SCENARIO` 且 `scenario_switch_count<2`）→ 调 `propose_scenario_switch`，加 `kind="scenario_switch"` turn，**重置 followup_rounds 到 0**，`scenario_switch_count++`
5. **SOFT exit**（normal answer + `total_score >= 9`）→ `exit_type=SOFT`，状态机停
6. **HARD_LIMIT**（normal answer + `followup_rounds >= 3`）→ `exit_type=HARD_LIMIT`，状态机停

如果 `scenario_switch_count == 2` 时再触发 SWITCH 信号，**fall through 到 normal eval**（"再换一个"被当作答案让 LLM 评分），budget 不再增加。

9 单测覆盖所有 6 路径 + start_drill 初始化 + budget cap，全套 46 passed。

**Files**:
- New: `backend/src/mockinterview/agent/drill_loop.py`, `backend/tests/test_drill_loop.py`
- Modified: `backend/src/mockinterview/agent/user_signals.py`（**Task 2.1 bug fix**：原 SWITCH_SCENARIO 模式要求 `换.*?例子` 或 `换.*?场景`，漏了"能换一个吗"这类常见说法；补加 `r"换一个"`, `r"换个"`, `r"再换"` 三条模式。Task 2.1 原 5 单测仍全过）

**Decisions / gotchas**:
- 状态机是**纯 logic 模块**，不含持久化/DB 调用；Task 2.7 才接 DB
- 4 helper（`classify` / `evaluate_and_followup` / `propose_scenario_switch` / `give_thinking_framework`）在 `drill_loop` 模块顶部 import，测试用 `patch("mockinterview.agent.drill_loop.<name>", ...)` mock（不是 patch 原始定义位置）
- `DrillState` 是 mutable dataclass，`advance()` 直接修改并返回 self；这是状态机习惯用法
- `_append_user` helper 把 user 消息按当前 `followup_rounds` 编号 append 到 transcript（注意：scenario_switch 路径不增 round，user 消息仍按 round=0 编号）
- 常量 `MAX_FOLLOWUPS=3`, `MAX_SWITCHES=2`, `SOFT_THRESHOLD=9` 全提到模块顶部，便于 Phase 4 评估调优时改

**Verify**: `cd backend && uv run pytest tests/test_drill_loop.py tests/test_user_signals.py -v` → `14 passed`；全套 `46 passed`

**Commit**: `42ab9ba`

---

## 2026-04-27 · Task 2.5 — Exemplar answer synthesizer

**Done**: 写 `agent/prompts/exemplar.py`（system 教 agent 用候选人简历素材合成"rubric 高分答案"+3 条具体改进建议）、`agent/exemplar.py`（`synthesize_exemplar(*,category,question_text,resume_json,transcript)` 返 `tuple[str, list[str]]`）。1 单测 mock 通过，全套 37 passed。

**Files**:
- New: `backend/src/mockinterview/agent/prompts/exemplar.py`, `backend/src/mockinterview/agent/exemplar.py`, `backend/tests/test_exemplar.py`

**Decisions / gotchas**:
- 这是 U-loop 5 个 building block 的最后一个。Task 2.6 状态机会在题目结束时（soft / hard_limit / user_end exit，**不含 skip**）调用本 helper
- 单独 `agent/exemplar.py` 模块（不并入 drill_eval.py）—— 避免 drill_eval.py 膨胀，保持单一职责
- 验证了 `.format(resume_json=json.dumps(...))` 不会因 JSON 内容含 `{` `}` 报错——`str.format` 不会重处理已替换的值
- 维度展示用 `label (description)` 比单 label 更详细（不像 Task 2.4 prompt mode 怕泄漏评分标准——这里题目已结束，给出范例答案的目的就是展示标准）

**Verify**: `cd backend && uv run pytest tests/test_exemplar.py -v` → `1 passed`；全套 `37 passed`

**Commit**: `29df382`

---

## 2026-04-27 · Task 2.4 — Prompt mode (思考框架)

**Done**: 写 `agent/prompts/prompt_mode.py`（system 教 agent "卡壳时不追问、不给答案，只给思考框架"），在 `agent/drill_eval.py` 追加 `give_thinking_framework(*,category,question_text,last_user_text)`：从 rubric 取 4 维度 label 拼成"维度1, 维度2, ..."传给 LLM，返字符串 hint。1 单测 mock 通过，全套 36 passed。

**Files**:
- New: `backend/src/mockinterview/agent/prompts/prompt_mode.py`, `backend/tests/test_prompt_mode.py`
- Modified: `backend/src/mockinterview/agent/drill_eval.py`（追加 1 import + 1 function；现在共 3 公开函数：evaluate_and_followup / propose_scenario_switch / give_thinking_framework）

**Decisions / gotchas**:
- 卡壳信号（Task 2.1 分类为 STUCK）→ Task 2.6 状态机调用本 helper，给思考框架后**不计入追问轮次**（spec §5.3 #5）
- 不直接 expose rubric 维度的 description（避免泄露评分标准），只 expose label 让 LLM 自己改写成自然口吻的切入问题
- 同样的 keyword-only 模式保持一致

**Verify**: `cd backend && uv run pytest tests/test_prompt_mode.py -v` → `1 passed`；全套 `36 passed`

**Commit**: `5048838`

---

## 2026-04-27 · Task 2.3 — Scenario switch helper（D 灵魂）

**Done**: 写 `agent/prompts/scenario_switch.py`（system 教 agent "释放场景维度，保留考察意图"；user template 输入题面/原意图/最后答案/已切换次数），在 `agent/drill_eval.py` 追加 `propose_scenario_switch(*,question_text,original_intent,last_user_answer,prior_switches)` 单 LLM 调用返字符串 prompt。1 单测 mock 通过，全套 35 passed 无回归。

**Files**:
- New: `backend/src/mockinterview/agent/prompts/scenario_switch.py`, `backend/tests/test_scenario_switch.py`
- Modified: `backend/src/mockinterview/agent/drill_eval.py`（追加 import + 1 function，不动原有代码）

**Decisions / gotchas**:
- 这是 v1 区别于通用对话工具的核心 UX：agent 主动识别"用户例子撑不住考察意图"时给台阶（"换个项目里的例子？"），不放弃考察意图但允许换场景维度
- 触发方有两种：用户主动（Task 2.1 classify 出 SWITCH_SCENARIO 信号）+ agent 主动（Task 2.6 状态机检测某轮 rubric 总分极低 + diagnosis 提示"例子撑不住"时调用）
- 函数签名 keyword-only（`*,`）：未来 Task 2.6 会按名传 4 个参数，避免位置漂移
- prompt 里的 JSON 示例 `{"prompt": "..."}` 是单花括号——`SCENARIO_SWITCH_SYSTEM` 不经过 `.format()`，单花括号正确（同 2.2 的 nuance）

**Verify**: `cd backend && uv run pytest tests/test_scenario_switch.py -v` → `1 passed`；全套 `35 passed`

**Commit**: `033885f`

---

## 2026-04-27 · Task 2.2 — Drill eval module（U-loop 大脑）

**Done**: 写 `agent/prompts/drill_eval.py`（system + user template）、`schemas/drill.py`（`DrillEvalResult` 4 字段 + `TranscriptTurn` 默认 `kind="normal"`）、`agent/drill_eval.py`（`evaluate_and_followup(category, question_text, transcript)` 单 LLM 调用 + `_format_rubric` / `_format_transcript` 两个私有 helper）。1 单测 mock 通过，全套 34 passed。

**Files**:
- New: `backend/src/mockinterview/{schemas/drill,agent/prompts/drill_eval,agent/drill_eval}.py`, `backend/tests/test_drill_eval.py`

**Decisions / gotchas**:
- 一次 LLM 调用同时输出 `{scores, total_score, weakest_dimension, weakness_diagnosis, next_followup}` —— 这是 U-loop 状态机每一轮的核心驱动
- `_format_transcript` 输出格式 `[round] 面试官/候选人 [tag]: text`，`kind` 字段未来会被 Task 2.3-2.4 的 scenario_switch / prompt_mode tag 利用
- ⚠️ **小坑（不阻塞）**：`DRILL_EVAL_SYSTEM` 里的 `{{...}}` JSON schema 示例其实**没必要**双花括号——这个常量只走 `build_cached_system`，不经 `.format()`。Claude 会看到字面 `{{` `}}`，应该仍能输出正确单花括号 JSON（指令明确"严格按 JSON schema 输出"），但 prompt 文本读起来怪。**Phase 4 评估时若 JSON 解析率不达标再修**
- `_format_rubric` 利用 Task 1.7 的 YAML 结构（`dimensions[].key/label/description` + `score_levels` dict）—— 跨 task 复用 config，不重复硬编码
- `transcript` 数据流方向：Task 2.6 状态机维护 `list[TranscriptTurn]`，每次 user 答完后传给本模块；返回的 `next_followup` 又被状态机 append 回 transcript

**Verify**: `cd backend && uv run pytest tests/test_drill_eval.py -v` → `1 passed`；全套 `34 passed`

**Commit**: `fa7373b`

---

## 2026-04-27 · Task 2.1 — User signal classifier（Phase 2 起步）

**Done**: `agent/user_signals.py` ~30 行纯正则分类器：5 类信号（END / SKIP / STUCK / SWITCH_SCENARIO / ANSWER fallback），按 `_PATTERNS` 列表顺序匹配（SKIP > STUCK > SWITCH_SCENARIO > END > ANSWER）。5 单测全过。

**Files**:
- New: `backend/src/mockinterview/agent/user_signals.py`, `backend/tests/test_user_signals.py`

**Decisions / gotchas**:
- 跳过创建 `agent/prompts/user_signals.py`（plan 原列出但 v1 纯正则，不需要 LLM 调用）—— v1.5 加 LLM-based ambiguity resolution 时再创建
- 模式顺序非常关键：用户输入"跳过这道我没思路"（同时含"跳过"和"没思路"），按 SKIP-first 原则返 SKIP；这是有意行为
- `text.strip().lower()` 必须在 match 前应用，因为 `\bskip\b` `\bhint\b` 是英文 word-boundary，需要 lowercase 才能命中
- Phase 2 第一个 task 完成；下游 Task 2.6 状态机会 import `classify` 决定每条用户输入走哪条 exit/redirect 路径

**Verify**: `cd backend && uv run pytest tests/test_user_signals.py -v` → `5 passed in 0.01s`

**Commit**: `d89f30f`

---

## 2026-04-27 · Phase 1 完成 + Task 1.10 — POST /questions/generate + CRUD

### Task 1.10 内容

**Done**: 写 `routes/questions.py` 4 个 endpoint：`POST /questions/generate`（404 if session 不存在 / 502 if 出题引擎返空 / 200 + 12 道题入库）、`GET /questions`（按 resume_session_id + 可选 category/status 筛选）、`GET /questions/{id}`、`PATCH /questions/{id}/status`。`schemas/api.py` 提供 `QuestionRead` / `GenerateRequest` / `QuestionStatusUpdate` 三个 API-shaped Pydantic 模型（与 db.models.Question 字段对齐但独立）。5 单测覆盖 happy path / category 筛选 / PATCH 改状态 / 空列表 502 guard / 未知 session 404。

**Files**:
- New: `backend/src/mockinterview/{schemas/api,routes/questions}.py`, `backend/tests/test_routes_questions.py`
- Modified: `backend/src/mockinterview/main.py`（注册 questions router）

**Decisions / gotchas**:
- 已落实 Task 1.9 review flag 的"空列表 guard"——LLM 返 0 题时返 502 而不是 sliently 返 200 + 空列表
- `QuestionRead` 与 `Question` ORM 字段一一对齐，但不共用——API schema 与 DB schema 解耦，未来字段重命名/新增时不影响外部契约
- 跳过 subagent review（pattern 与 Task 1.6 routes/resume.py 完全一致，且 5 单测含 happy/error/edge）

**Verify**: `cd backend && uv run pytest -v` → `28 passed in 0.07s`

**Commit**: `4b9b165`

### Phase 1 总结

- ✅ 10 个 task 全部完成（Task 1.1-1.10）
- ✅ 28 单测全过；前端 `pnpm build` 通过
- ✅ Backend 完整链路：上传简历 PDF → pdfplumber 抽文本 → Claude 结构化解析 → ResumeSession 入库 → question gen engine 出 12 题 → Question 表入库 → CRUD 可读可改
- ✅ git tag `w1-done`
- ⏳ 未做（有意推迟）：
  - 真 e2e smoke test（需真 ANTHROPIC_API_KEY + 真 PDF）——用户首次面试季用时跑一遍即可
  - 30 题/岗位完整种子库 curation——v1.5 / 用户面试季补
  - 微小 cleanup：`_format_seeds` 里的 magic 12（题库扩到 ≥30 时此切片才生效）、api.ts 里的 "string body 视为 JSON" 约定 JSDoc

**14 个 commit 含 Phase 1**：8d7fbbf → 4594dfc → e093c6b → 924b92e → 2cae489 → 33b3044 → f8c18f1 → f611300 → 38a8ceb → 1fb174e → 8d53925 → 4b9b165 + 4 个 memory log + 1 个 init/.gitignore

下一步：进入 **Phase 2 Week 2** —— U-loop 单题核心（最重的一周，8 个 task：user signal classifier / drill eval / scenario switch / prompt mode / exemplar / state machine / drill API / single-question report endpoint）。

---

## 2026-04-27 · Task 1.9 — Question generation engine（Phase 1 核心）

**Done**: 写 `agent/prompts/question_gen.py`（~50 行 Chinese system prompt + `ROLE_LABEL` + `ROLE_ANGLE` 4 岗位查表 + user template）、`schemas/question.py`（`Category`/`Difficulty` Literal 类型 + `GeneratedQuestion`/`QuestionList` 模型）、`agent/question_gen.py`（`generate_questions(*,role,resume_json,jd_text,company_name)` 单 LLM 调用 + structured output；私有 `_distribution(has_jd)` 返 {T1:4,T2:2,T3:3,T4:2,T5:1}=12 / 无 JD 时 {T1:5,T2:3,T3:0,T4:2,T5:1}=11）。2 单测覆盖 happy path + 无 JD 分布分支。

**Files**:
- New: `backend/src/mockinterview/{schemas/question,agent/prompts/question_gen,agent/question_gen}.py`, `backend/tests/test_question_gen.py`

**Decisions / gotchas**:
- System prompt 末尾的 `{{"questions": [...]}}` 是有意 `.format()` 转义——单 `{` 是 placeholder, 双 `{{` 是 literal。10 个 placeholder × format() 一次成型，跑通验证
- `generate_questions` keyword-only（`*,`）：避免 Task 1.10 路由层位置参数漂移
- `build_cached_system([system])` 把 .format 后的 system prompt 包成单 block 列表，自动给最后一块加 `cache_control={"type":"ephemeral"}` —— 简历 + JD 不变时缓存命中
- `json.dumps(resume_json, ensure_ascii=False, indent=2)` 中文不被转义、缩进 2 让 Claude 易解析（成本可接受）
- `has_jd = bool(jd_text and jd_text.strip())` 同时处理 None/空串/空白
- ⚠️ **Task 1.10 路由层注意**：`QuestionList.questions = Field(default_factory=list)` 是宽松验证——若 model 输出 `{"questions": []}` 也会通过；route 层应加长度 ≥ 1 守卫，或在 API 边界返 500 + 重试
- 已知小 cleanup（不阻塞）：`_format_seeds` 里的 `max(n*5, 12)` 是为更大题库设计的，当前 6 题/岗位下 slicing 实际是 no-op；当题库扩到 30 时此切片才生效

**Verify**: `cd backend && uv run pytest tests/test_question_gen.py -v` → `2 passed`；全套 `23 passed`

**Commit**: `8d53925`

---

## 2026-04-27 · Task 1.8 — Seed question banks (pm/data/ai/other)

**Done**: 写 4 份种子题库 YAML（pm/data/ai 各 6 题、other 3 题），覆盖 北极星 / case / trade-off / 实验设计 / SQL / metric / AI eval / RAG / 通用行为题等角度。`agent/seed_bank.py` 12 行 loader（同 rubrics.py 风格，lru_cache + ROLES 列表）。5 单测全过（4 parametrized + 1 unknown role）。

**Files**:
- New: `backend/src/mockinterview/configs/seed_questions/{pm,data,ai,other}.yaml`, `backend/src/mockinterview/agent/seed_bank.py`, `backend/tests/test_seed_bank.py`

**Decisions / gotchas**:
- 用户选择 plan 折中方案 C：v1 只 ship 6 题/核心岗位（不补到 30），剩余 24 题/岗位的 curation 推到 v1.5 / 用户面试季补
- 各岗位 6 题已覆盖至少 5-6 个不同 angle tag，T4 题型生成器从这里抽样作为候选池
- lru_cache 返回的是同一个 list 引用——下游消费方不应 mutate；目前无任何代码 mutate，OK
- 同样跳过 subagent review（pure content + 12 行 loader），21/21 全套测试过即可

**Verify**: `cd backend && uv run pytest -v` → `21 passed`

**Commit**: `1fb174e`

---

## 2026-04-27 · Task 1.7 — 5 Rubric YAML configs

**Done**: 写 5 份 YAML（`backend/src/mockinterview/configs/rubrics/{t1_star,t2_quant,t3_jd_align,t4_structured,t5_motivation}.yaml`），每份含 category / name / 4 dimensions（key + label + description）/ score_levels（0-3）/ threshold_complete=9。`agent/rubrics.py` 12 行 loader：`load_rubric(category)` 带 lru_cache + `all_rubrics()` 返 5 份。2 测试全过。

**Files**:
- New: `backend/src/mockinterview/configs/rubrics/{t1_star,t2_quant,t3_jd_align,t4_structured,t5_motivation}.yaml`, `backend/src/mockinterview/agent/rubrics.py`, `backend/tests/test_rubrics.py`

**Decisions / gotchas**:
- `score_levels` 的 key 被 PyYAML 解析为 `int` 0-3（不是 str）——下游 prompt template 拼接时记得 key 类型
- 5 套 rubric 的 dimension key 是 prompt 和 DrillAttempt.rubric_scores_json 的稳定标识符，**不能改**：T1: situation/task/action/result, T2: baseline/attribution/significance/business_meaning, T3: case_support/framework/feasibility/reflection, T4: dimensions/priority/edge_cases/falsifiable, T5: specificity/coherence/non_cliche/reflection
- 跳过单独 subagent review（task 是纯 YAML + 12 行 loader）：自验通过 grep 确认 5 份文件 category/keys/threshold 全对，16/16 tests 全过

**Verify**: `cd backend && uv run pytest tests/test_rubrics.py -v` → `2 passed in 0.01s`；全套 `16 passed`

**Commit**: `38a8ceb`

---

## 2026-04-27 · Task 1.6 — POST /resume + 5 deferred robustness fixes (2 commits)

**Done**: 实现 `POST /resume` HTTP endpoint（multipart 上传 PDF + role_type + 可选 JD/公司），并清算 Task 1.3/1.5 累积的 5 个 robustness item。两个 commit 分前后端：

**Commit A (`f8c18f1`) — 后端**：
- `resume_parser.py` 重写：定义 `ResumeParseError` 自定义异常、`extract_pdf_text` 加 empty-bytes guard 并把 pdfplumber 异常包成 `ResumeParseError`、image-only PDF 给"看似扫描件"友好提示、user template 用 `.replace("{resume_text}", text)` 取代 `.format`（避免简历含 `{xxx}` 时炸 KeyError）
- 新 `routes/resume.py`：分别 400 处理 invalid role / empty file / `ResumeParseError`，成功返 200 + 5 字段
- `main.py` 注册 router；4 个新 route 测试 + 1 个新 empty-bytes 测试 + 1 个更新过的 empty-text 测试

**Commit B (`f611300`) — 前端**：
- `api.ts` 重写：`ApiError extends Error` 带 `status` + `body` 字段、`isJsonBody` 判别函数（FormData/Blob/URLSearchParams/ArrayBuffer 不注入 `Content-Type`）、非 2xx 时先 JSON 解析失败再 fallback text、抛 `ApiError`

**Files**:
- Modified: `backend/src/mockinterview/{agent/resume_parser,main}.py`, `backend/tests/test_resume_parser.py`, `frontend/src/lib/api.ts`
- New: `backend/src/mockinterview/routes/{__init__,resume}.py`, `backend/tests/test_routes_resume.py`

**Decisions / gotchas**:
- `extract_pdf_text` 用宽 `except Exception`：pdfplumber 没有公开异常层级（混用 `PSEOF`/`PDFSyntaxError`/通用 Exception），宽 catch 是当前最佳实践。未来加日志时记录原始 type
- 路由是 sync `def`（不是 `async def`），所以 `file.file.read()` 是 sync 读——FastAPI 会在 threadpool 跑 sync handler，event loop 不会被阻塞。如未来 handler 加 I/O，再统一切 async + `await file.read()`
- `get_settings()` 在 route body 里直接调（不走 `Depends(get_settings)`）：`lru_cache` 让两者等价，但走 Depends 在测试 override 上更优——目前测试 mock 的是 `parse_resume`，影响有限，**Phase 1 收尾时若有时间可重构**
- `api.ts` 的 `isJsonBody` 对纯字符串 body 默认返 `true`（约定"字符串 body = JSON"）——若未来传 form-encoded 字符串需调用方显式覆盖 `Content-Type`，加 JSDoc 说明（**这条记下来，Task 1.7+ 任意时机加 1 行注释即可**）
- ⚠️ 上述两个 followup 体量都是 1 行注释级，不开新 task，等下一次 touch 这两个文件时顺手加

**Verify**:
- `cd backend && uv run pytest -v` → `14 passed in 0.04s`
- `cd frontend && pnpm build` → `Compiled successfully in 1002ms`

**Commits**: `f8c18f1` (backend), `f611300` (frontend)

---

## 2026-04-27 · Task 1.5 — Resume parser (PDF → structured JSON)

**Done**: 加 `agent/prompts/resume_parse.py`（中文 system prompt，4 字段 + 5 规则）、`schemas/resume.py`（5 个 Pydantic 模型，仅 4 类字段，显式排除证书/奖项/语言/兴趣）、`agent/resume_parser.py`（`extract_pdf_text` 用 pdfplumber，`parse_resume` 协调 PDF→文本→Claude→`ResumeStructured.model_validate`）。2 单测全 mock（monkeypatch 模块级 `extract_pdf_text` + patch 模块导入的 `call_json`）。

**Files**:
- New: `backend/src/mockinterview/{schemas/__init__,schemas/resume,agent/prompts/__init__,agent/prompts/resume_parse,agent/resume_parser}.py`, `backend/tests/test_resume_parser.py`

**Decisions / gotchas**:
- Pydantic v2 处理裸 `list = []` 默认值是安全的（每次实例化 deep-copy），所以 `Basic.education = []` 和其他用 `Field(default_factory=list)` 的混合写法都正确——保持与 plan verbatim 一致
- `outcomes`/`role` 默认空字符串：spec §3 明确"不强制 outcomes，agent 出题时把缺 outcomes 当 feature"——保留
- 测试 mock 策略：`monkeypatch.setattr(resume_parser, "extract_pdf_text", fake)` + `patch("...resume_parser.call_json", ...)`——前者改模块属性、后者改导入名，两者互不冲突
- ⚠️ **Task 1.6 接 PDF HTTP endpoint 时一并修以下 robustness 项**（reviewer flag 的 minor，全部推迟到 1.6 boundary 处理）：
  1. 把 pdfplumber 的 `PDFSyntaxError`/`PSException` 包成 `ResumeParseError`，HTTP 层返 400
  2. `pdf_bytes==b""` 守卫（在 `extract_pdf_text` 顶部 `if not pdf_bytes: raise ValueError`）
  3. image-only PDF 的友好提示（"PDF 看似扫描件，无法抽取文本，请粘贴文本"）
  4. `.format(resume_text=text)` 改 `.replace("{resume_text}", text)` 或 `string.Template`，避免简历文本含 `{xxx}` 时炸 KeyError
  5. 加上 Task 1.3 留的 api.ts FormData + ApiError 两个坑——一并 1.6 修

**Verify**: `cd backend && uv run pytest tests/test_resume_parser.py -v` → `2 passed in 0.25s`

**Commit**: `33b3044`

---

## 2026-04-27 · Task 1.4 — Anthropic client wrapper with prompt caching

**Done**: 写 `backend/src/mockinterview/agent/client.py`（45 行）：`get_client()` lru_cache 单例、`build_cached_system(parts)` 把字符串列表转成 system text block 数组并给最后一块加 `cache_control={"type":"ephemeral"}`、`parse_json_response(text)` 处理 ```json ``` 围栏或裸 JSON、`call_json(...)` 一站式调用 + 解析。3 单测全 mock，不打 API。

**Files**:
- New: `backend/src/mockinterview/agent/__init__.py`, `backend/src/mockinterview/agent/client.py`, `backend/tests/test_agent_client.py`

**Decisions / gotchas**:
- 验证 Anthropic SDK 0.97.0 的 `{"type":"ephemeral"}` cache_control 格式是当前正确格式（未来若调长 TTL 可加 `"ttl":"1h"`）
- `b.text` 访问：SDK content 是 union（TextBlock/ThinkingBlock/ToolUseBlock），先用 `b.type=="text"` 过滤再取 `.text` 才安全——已实现
- 已知小坑（暂不处理，影响小且后续 task 有自然修复）：
  - `_JSON_FENCE.search` 返第一个 match——如果 model 输出"思考块 + 最终答案块"两个围栏，会取错的；rubric 类提示通常只一个围栏，先不动
  - `get_client()` lru_cache 跨测试不重置——Task 1.5+ 用 mock 时通过 monkeypatch `call_json` 绕过，不需重置 client
  - `call_json` 本身没单测——Task 1.5 起被 mock 调用，覆盖间接达成
- code reviewer 误把 docstring 当 spec 偏差（review prompt 我截断了 spec，原 task 含 docstring）—— 无实际问题

**Verify**: `cd backend && uv run pytest tests/test_agent_client.py -v` → `3 passed in 0.18s`

**Commit**: `2cae489`

---

## 2026-04-27 · Task 1.3 — Frontend skeleton (Next.js 16 + shadcn)

**Done**: `pnpm dlx create-next-app` 起 `frontend/`（Next.js 16.2.4 + React 19.2.4 + TypeScript + Tailwind v4 + App Router + src dir + Turbopack + 无 ESLint + pnpm），shadcn init 后 add 9 个 UI 组件（button/card/input/textarea/label/badge/progress/tabs/dialog），首页换成项目占位文案，lib/api.ts 写了 fetch 包装器。`pnpm build` 通过，31 文件入 commit。

**Files**:
- New: `frontend/`（含 31 个文件，主要为 next/shadcn 自动生成）
  - 手写：`frontend/src/app/page.tsx`、`frontend/src/lib/api.ts`
  - 自动：`package.json`、`pnpm-lock.yaml`、`tsconfig.json`、`components.json`、`src/components/ui/*`（9 个）、`AGENTS.md`、`CLAUDE.md` 等

**Decisions / gotchas**:
- shadcn 现在用 `@base-ui/react`（不是老的 Radix）—— 是新版 shadcn 的默认 registry
- `frontend/AGENTS.md` 和 `frontend/CLAUDE.md` 是 create-next-app 自动生成的 Next.js 16 breaking-change 提示，留在 frontend 根（agent 工具会查找包根目录），不要移动
- shadcn CLI 写在 `dependencies` 而不是 `devDependencies`（创建工具默认行为，未来清理时可调整，暂留）
- pnpm warning 提到 `msw@2.13.6` 是 shadcn CLI 的传递依赖（registry mocking 用），不是直接依赖，无需处理
- `.DS_Store` 被 root `.gitignore` 屏蔽，未入 commit
- ⚠️ **TODO 给 Task 1.6 接 PDF 上传时修复 api.ts 两个已知坑**：
  1. `Content-Type: application/json` 是无条件注入，`FormData` body 上传会被覆盖导致 FastAPI 422——改为根据 body 类型条件注入
  2. `throw new Error(${r.status} ${await r.text()})` 把 FastAPI 的结构化 `{"detail":...}` JSON 拼成单行 string，调用方拿不到 status/detail——定义 `ApiError extends Error` 带 status/body 字段
  这两点是 plan verbatim 引入的小 footgun，Task 1.3 spec 不改；Task 1.6 第一个 commit 修。

**Verify**: `cd frontend && pnpm build` → `✓ Compiled successfully in 1133ms`

**Commit**: `924b92e`

---

## 2026-04-27 · Task 1.2 — Database models (4 tables) + session

**Done**: 实现 spec §10 的 4 张 SQLModel 表（ResumeSession / Question / DrillAttempt / Report）+ 2 个枚举（QuestionStatus / ExitType），`db/session.py` 提供 engine + `init_db` + `get_session` 依赖；`main.py` 用 lifespan 模式在启动时建表。3 个 round-trip 测试 + 原有 health 测试共 4 passed。

**Files**:
- New: `backend/src/mockinterview/db/{__init__,models,session}.py`, `backend/tests/test_db_models.py`
- Modified: `backend/src/mockinterview/main.py`（替换为 lifespan 模式）, `backend/tests/conftest.py`（fixture 改 context-manager 让 lifespan 跑起来）, `plans/2026-04-27-mock-interview-agent-v1.md`（Task 1.2 代码块更新为 timezone-aware datetime）

**Decisions / gotchas**:
- 5 个 `dict`/`list` JSON 列统一用 `sa_column=Column(JSON)`（跨 DB 可移植，未来切 Postgres 不用改）
- 所有 FK + 高频筛选字段（user_id / role_type / status）都加了 index
- Code reviewer 抓出 2 个 important 立刻修复（commit `e093c6b`）：
  - I1: `datetime.utcnow()` 在 Python 3.12+ 已 deprecated，全部替换为 `datetime.now(timezone.utc)`，plan 文档也同步更新避免后续 task 复制粘贴时复活老用法
  - M5: `conftest.py` 的 `client` fixture 原本用裸 `TestClient(app)`，FastAPI lifespan 不会触发；改成 `with TestClient(app) as c: yield c`，否则后续 DB 路由测试会报 "no such table"
- 推迟项（reviewer 提到但不阻塞 Task 1.3）：共享 db_session fixture（I2）、把 mkdir 移进 init_db（I3）、给 total_score 加 0-12 范围约束（M2）、把 category/difficulty 改成 Enum（M3）

**Verify**: `cd backend && uv run pytest -W error::DeprecationWarning -v` → `4 passed, 0 utcnow warnings`

**Commits**: `4594dfc` (initial schema) → `e093c6b` (timezone + lifespan fix)

---

## 2026-04-27 · Task 1.1 — Initialize backend project skeleton

**Done**: 用 uv 初始化 `backend/` Python 项目骨架，搭起 FastAPI 应用 + `/health` endpoint + pytest 配置（含 `live` marker 跳过实 API 调用）。

**Files**:
- New: `backend/pyproject.toml`, `backend/.python-version`, `backend/uv.lock`, `backend/src/mockinterview/{__init__,main,config}.py`, `backend/tests/{conftest,test_health}.py`

**Decisions / gotchas**:
- `uv init` 默认在 `backend/` 内嵌套创建 `backend/mockinterview/`（含 pyproject 和 src），需手动 flatten 一层后再覆盖 pyproject.toml。下次类似 task 注意。
- 工具链：`brew install uv pnpm` 先安装（`uv` 0.11.7, `pnpm` 10.33.2）。Python 用 uv 装的 3.12.13（系统 Python 是 3.14，但 .python-version 把项目锁到 3.12）。
- code reviewer 提了 3 条 Important 是 forward-looking 给后续 task 的预警，**不需要现在改**：
  - `CORS_ORIGINS` env 解析（plan Task 4.7 会加 field_validator）
  - `anthropic_api_key=""` 默认值（Task 1.4 接 API 时再处理）
  - `claude_model="claude-opus-4-7"` 是 2026-04 当前 Opus 4.7 的合法 alias，无需改
- `uv.lock` 已 commit（应用类项目应锁，库类项目应 ignore）

**Verify**: `cd backend && uv run pytest tests/test_health.py` → `1 passed in 0.00s`

**Commit**: `8d7fbbf`

---

---

## 起点（Phase 0 已完成）

- **2026-04-27** · 立项文档 [PROJECT.md](PROJECT.md)（产品策略 + 范围决策）
- **2026-04-27** · v1 设计文档 [docs/superpowers/specs/2026-04-27-mock-interview-agent-v1-design.md](docs/superpowers/specs/2026-04-27-mock-interview-agent-v1-design.md)（13 章节）
- **2026-04-27** · 实施计划 [plans/2026-04-27-mock-interview-agent-v1.md](plans/2026-04-27-mock-interview-agent-v1.md)（4 phase × 4 周）
- **2026-04-27** · git init + .gitignore + 设计文档与计划文档已 commit
