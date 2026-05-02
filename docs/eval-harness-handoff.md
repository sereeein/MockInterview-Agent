# 跨 Session 接续提示词 — Eval Harness 项目

**用法**：开新 session 时把下面 ╔══ 到 ══╗ 之间的内容整段贴给 Claude，它会读完所有引用文件并接上前一个 session 的状态。

---

## 长版（推荐 — 完整背景）

```
╔══════════════════════════════════════════════════════════════════════════╗

我在继续 MockInterview Agent 项目的 eval harness 升级工作。这是跨 session
的接续，请先读以下三个文件理解完整状态再回应：

1. docs/eval-harness-status-2026-05-02.md
   ← 项目级状态快照：已完成 phase 详情 + 未完成 phase 详细计划 + 流程门状态

2. memory.md（最上方两条记录）
   ← 跨 session 进度日志，第 1 条 = Phase 1+2 实施细节，第 2 条 = Phase 0
      详情。下方更早的 v1.0 / v1.1 记录是项目背景，不是当前任务。

3. eval/diagnostics/A_validation_2026-05-02.md
   ← Phase 3 验证报告，是当前简历强 bullet 的数据源。

读完后用一段话给我复述：
- 我们在哪个 phase？
- 上一个 session 末尾停在哪个流程门？
- 用户（我）需要在什么决策点拍板才能继续？
- 当前最强简历 bullet 是什么？

复述无误后，等我拍板下一步走哪条路径（精简 C / 完整 C / 暂停 / 直接前置 Phase 5）。

---

约束：
- 不要在 git commit 加任何 AI co-author（参 ~/.claude/CLAUDE.md）
- 每完成一个 task 必须追加一条 memory.md 记录
- 范围决策时优先 UX 完整度（不是默认砍功能保速度）
- 流程门必须停下等我 review，不要一路冲到底
- 当前未 commit 的改动是 Phase 0+1+2+3 整体里程碑，下次 session 可以请示
  我后一起 commit

╚══════════════════════════════════════════════════════════════════════════╝
```

---

## 短版（如果上下文紧 / 想快速 dive 在）

```
╔══════════════════════════════════════════════════════════════════════════╗

接续 MockInterview eval harness 工作。先读：

  docs/eval-harness-status-2026-05-02.md

然后告诉我：当前位置 = 流程门几？需要我决策什么？

注意：不加 AI co-author，每 task 末尾追加 memory.md 记录。

╚══════════════════════════════════════════════════════════════════════════╝
```

---

## 极简版（只是要继续之前的思路，不需要详细复述）

```
╔══════════════════════════════════════════════════════════════════════════╗

继续 MockInterview eval harness。读 docs/eval-harness-status-2026-05-02.md
理解现状，然后 [ 你想要的具体动作，例如 "走精简 C，从 Phase 4 T4.0 开始" ]。

╚══════════════════════════════════════════════════════════════════════════╝
```

---

## 验证 Claude 真的接上了的检查清单

新 session 给提示词后，Claude 应该能正确回答：

| 问题 | 正确答案要点 |
|---|---|
| 当前在哪个 phase？ | Phase 0/1/2/3 已完成，**停在流程门 2** |
| 上一个 session 末尾停在哪？ | 等用户在 4 个选项里拍板（精简 C / 完整 C / 暂停 / 前置 Phase 5）|
| 流程门 2 三阈值通过了吗？ | 全过（post-fix 0% < 5%；regression 18/18；retry 0%）|
| 推荐走哪条路径？ | 精简 C（Anthropic + MiMo Tier 1） |
| 简历最强 bullet 是？ | "Diagnosed structurally repeatable JSON parse failure ... 40% → 0% ... Fisher's p=1.5×10⁻⁷ ..." |
| Phase 3 真正修好 bug 的是什么？ | 移除 `_clean_json_payload` 中文引号替换（latent bug），不是 json-repair |
| 下一步开始动手前要等什么？ | 用户拍板路径选项 |

如果它复述错了某一项 — 不要继续动手，纠正它再继续。这是接续质量的快速健全检查。

---

## 给新 session 提供的快捷命令清单

跑 harness 的标准命令（让新 Claude 知道直接用）：

```bash
# 运行 N 次 attempt（DeepSeek，跑 phase 1+ baseline 用）
cd backend && env -u VIRTUAL_ENV PYTHONPATH=.. MOCK_PROVIDER=deepseek \
    uv run python -m eval.harness.cli run \
    --case <id>... --repeat <N> --intent "<why>"

# 运行 N 次 attempt（Anthropic 默认）
cd backend && env -u VIRTUAL_ENV PYTHONPATH=.. \
    uv run python -m eval.harness.cli run \
    --case <id>... --repeat <N> --intent "<why>"

# 重新聚合（不重跑 LLM）
cd backend && env -u VIRTUAL_ENV PYTHONPATH=.. \
    uv run python -m eval.harness.cli stats <run_id>

# 跑后端单测
cd backend && env -u VIRTUAL_ENV uv run pytest tests/test_agent_client.py -x

# 跑全测试套件
cd backend && env -u VIRTUAL_ENV uv run pytest
```

API key 配置：`backend/.env` 里的 `ANTHROPIC_API_KEY` 和 `DEEPSEEK_API_KEY`，
cli.py 会按 `MOCK_PROVIDER` 自动选对应的 `<PROVIDER>_API_KEY`。

---

## 文件位置速查

| 想看 | 路径 |
|---|---|
| 项目状态 + 路线图 | `docs/eval-harness-status-2026-05-02.md` |
| 跨 session 进度日志 | `memory.md` |
| Phase 3 验证报告（简历数据源） | `eval/diagnostics/A_validation_2026-05-02.md` |
| Phase 3 主数据 run | `eval/runs/2026-05-02T043721-d034a2a/` |
| Phase 3 regression run | `eval/runs/2026-05-02T043732-d034a2a/` |
| Phase 1 DeepSeek baseline | `eval/runs/2026-05-02T0419-d034a2a/` |
| Harness 源码 | `eval/harness/` |
| parse 修复源码 | `backend/src/mockinterview/agent/client.py` |
| parse 修复单测 | `backend/tests/test_agent_client.py` |
| 学习指南（项目 6 层架构） | `docs/learning-guide.md` |
