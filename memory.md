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
