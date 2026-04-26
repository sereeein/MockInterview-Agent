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
