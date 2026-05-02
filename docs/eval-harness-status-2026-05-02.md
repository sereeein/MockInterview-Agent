# Eval Harness 项目状态 + 路线图（2026-05-02）

> 本文档由 2026-05-02 工作 session 末尾产出，作为跨 session 接续的权威状态快照。
> **当前位置**：Phase 0/1/2/3 全部完成，停在 🚦 流程门 2 等待用户拍板 Phase 4 走精简 C / 完整 C / 暂停。

---

## 整体计划地图（9 phase）

```
Phase 0 — Minimal harness                     [✓ 完成]  ~1 day
Phase 1 — Baseline 测量                       [✓ 完成]  ~0.5 day（三轮迭代）
🚦 流程门 1 — N 决策                          [✓ 通过]  N=50 per case post-fix（用户拍）
Phase 2 — A 修复实施（json-repair + retry）   [✓ 完成]  ~0.5 day
Phase 3 — A 验证                              [✓ 完成]  ~0.5 day
🚦 流程门 2 — 精简 C / 完整 C / 暂停          [⏸ 等待]  ← 当前位置
Phase 4 — 设计 C（call_with_schema）          [○ 未开始]
Phase 5 — MiMo 验证                           [○ 未开始]
Phase 6 — Tier 1 实施                         [○ 未开始]
Phase 7 — Tier 2/3 fallback                  [○ 未开始]
Phase 8 — 切换 generate_questions             [○ 未开始]
Phase 9 — 跨 provider 验证                    [○ 未开始]
```

---

# Part 1 — 已完成

## Phase 0：Minimal Harness（[detail in memory.md](../memory.md)）

7 个子任务全过，~1100 LoC，跑通真 LLM smoke。

### 文件落盘

```
eval/
├── __init__.py                 ← 空，让 eval 可作 package（python -m eval.harness.cli）
├── .gitignore                  ← 加了 runs/
├── harness/
│   ├── __init__.py
│   ├── schemas.py              ← 5 个 dataclass + ProviderCapabilities + dump/load helper
│   ├── trace.py                ← TraceCapturer + TracingProvider 包装 active provider
│   ├── loader.py               ← 读 pairs.yaml，--case / --role 过滤
│   ├── runner.py               ← run_attempt + run_case + failure 分类
│   ├── aggregator.py           ← 跨 attempt 聚合 + Wilson CI
│   ├── significance.py         ← 纯 Python: Wilson + Fisher's exact + 80% power N
│   └── cli.py                  ← argparse 全骨架（run / show / stats / diff / promote），run/stats 已 wire
├── runs/                       ← gitignored；每次 run 写入 runs/<run_id>/
└── diagnostics/
    └── A_validation_2026-05-02.md  ← Phase 3 验证报告
```

### 关键设计决策

- `run_id` 格式：`<UTC ISO YYYY-MM-DDTHHMMSS>-<git-short-7>`，秒粒度（曾因分钟粒度撞过一次）
- `tier` 枚举永久 `tier1 | tier2 | tier3`（绝不引入 tier1.5），能力差异通过 `ProviderCapabilities` 4 boolean 表达
- ContextVar `_last_parse_record` 通道：provider 内部 parse 后透出 raw_text + status + repair_summary 给 trace 层用
- 所有 forward-compat 字段（`baseline_run_id` / `prompt_versions` / `code_versions` / `fix_under_test` / `experiment_arm`）在 minimal 阶段填 null，完整 harness 时直接用

### 调用方式

```bash
cd backend && env -u VIRTUAL_ENV PYTHONPATH=.. \
    [MOCK_PROVIDER=deepseek] \
    uv run python -m eval.harness.cli \
    run --case <id>... --repeat <N> --intent "<why this run>"
```

---

## Phase 1：Baseline 测量（三轮才拿到干净数据）

### 第一轮（Anthropic, 信用耗尽中断）

- 跑了一半被 BadRequest 截断
- pm_alpha_self 4/4 失败（在 4 attempts 里全失败）
- 这个数据曾误导成"100% 失败" — 实际是小 N 抖动

### 第二轮（Anthropic 充值后 fresh N=10）

| Case | 失败率 | Wilson 95% CI |
|---|---|---|
| `pm_alpha_self` | 4/10 = 40% | [17%, 69%] |
| `other_no_jd` | 4/10 = 40% | [17%, 69%] |

发现：**bug 在多道题独立触发**（line 4 / 22 / 40 等位置），per-question ~5%，pm_alpha_self 不是确定性失败也不罕见。

### 第三轮（DeepSeek N=10）

| Case | 失败率 | Wilson 95% CI |
|---|---|---|
| `pm_alpha_self` | 7/10 = 70% | [40%, 89%] |
| `other_no_jd` | 1/10 = 10% | [2%, 40%] |
| **Pooled** | **8/20 = 40%** | **[22%, 61%]** |

**关键发现**：失败模式跨 provider 完全相同（都是 `Expecting ',' delimiter` 在 question_gen 不同位置），强证据 fix 通用。

### 流程门 1 决策

用户拍 **N=50 per case post-fix（充裕版）**，pooled framing：
- pre 8/20 vs post 0/100 → Fisher's p ≈ 1×10⁻⁶
- post 0/100 → Wilson 上界 3.7%
- LLM 成本估算 ~$1（DeepSeek 比 Anthropic 便宜 20-40 倍）

---

## Phase 2：A 修复实施

### 改动文件

| 文件 | 改动 |
|---|---|
| `backend/pyproject.toml` | + `json-repair>=0.59` |
| `backend/uv.lock` | 自动 |
| `backend/src/mockinterview/agent/client.py` | **重写**：parse_json_response 加 json-repair fallback；ContextVar 通道发布 ParseRecord；call_json 加 max_retries=1 + 修正消息 |
| `backend/tests/test_agent_client.py` | 3 → 12 tests，含真实失败模式 + retry 上下界 |
| `eval/harness/trace.py` | TracingProvider 调 `consume_last_parse_record` 填 raw_text + status |
| `eval/harness/cli.py` | _make_run_id 改秒粒度；支持 `<PROVIDER>_API_KEY` 自动识别 |
| `eval/harness/schemas.py` | forward-compat 注释更新 run_id 格式 |

### 关键设计决策

1. **ContextVar 通道 vs 改 provider 接口**：选 ContextVar — 不需改 3 个 provider 实现签名
2. **Retry 用 user-role 修正轮**而非 system-role 追加 — 后者很多 OpenAI-compat provider 不允许 multi-system
3. **移除 `_clean_json_payload` 中文引号替换**（这是 Phase 3 才发现的真正修复点 — 见下）
4. **json-repair 配置**：`repair_json(text, return_objects=True)` 直接返回 dict；非 dict 视为失败让 caller retry

### 验证

- 12 unit tests 全过（含 `test_parse_json_response_repairs_unescaped_quote` 直接覆盖真实失败模式）
- 全 backend 测试套件 97 passed, 1 skipped
- 真 LLM sanity（pm_alpha_self N=3）3/3 success

---

## Phase 3：A 验证

### 核心数字

| | Pre-fix (N=20 pooled) | Post-fix (N=100 pooled) |
|---|---|---|
| 失败率 | **40%** | **0%** |
| Wilson 95% CI 失败率 | [22%, 61%] | **[0%, 3.7%]** |
| 与 pre Fisher's exact | — | **p = 1.5 × 10⁻⁷** |

### 流程门 2 三阈值（用户已松到 5%）

| 阈值 | 实测 | ✓ |
|---|---|---|
| `other_no_jd` post-fix 失败率 ≤ 5% | 0% (Wilson 上界 7.1%) | ✓ |
| 6 stable case 无 regression | 18/18 = 100% | ✓ |
| retry 触发率 ≤ 5% | **0/100 = 0%** | ✓ |

**全过 → 推荐精简 C 路径。**

### 意外发现：真正修好 bug 的不是 json-repair

100 次 post-fix attempts：**0 次触发 json-repair fallback**，**0 次 retry**。

真正的 fix 是 **Phase 2 顺手移除的 `_clean_json_payload` 中文引号替换**（旧版 `.replace("“", '"').replace("”", '"')` 把字符串值里合法的中文引号变成 unescaped ASCII quote，**自己制造了非法 JSON**）。

这是一个 latent bug，以"best-effort cleanup"的名义混进来。诊断它本身就是更耐讲的故事。

json-repair + retry 现在是 **defense-in-depth** —— 给没遇见过的边缘场景兜底。

### 文件落盘

- 报告：[eval/diagnostics/A_validation_2026-05-02.md](../eval/diagnostics/A_validation_2026-05-02.md)
- 数据 runs：
  - Phase 1 Anthropic baseline：`eval/runs/2026-05-02T0356-d034a2a/`
  - Phase 1 DeepSeek baseline：`eval/runs/2026-05-02T0419-d034a2a/`
  - **Phase 3 post-fix N=50**：`eval/runs/2026-05-02T043721-d034a2a/`
  - **Phase 3 regression N=18**：`eval/runs/2026-05-02T043732-d034a2a/`

### 简历可写性 — 第一个真正的强 bullet

> Diagnosed structurally repeatable JSON parse failure on adversarial inputs across two LLM providers (Claude Opus 4.7, DeepSeek-Chat) — root cause was a latent over-aggressive Chinese-quote cleanup that corrupted valid JSON strings. Reduced attempt-level failure rate from 40% (pre-fix, N=20 pooled) to 0% (post-fix, N=100 pooled, 95% Wilson CI [0%, 3.7%]; Fisher's exact p = 1.5 × 10⁻⁷). Shipped json-repair + retry as a provider-agnostic defense-in-depth layer alongside the root-cause fix.

---

## 总成本对账

| 项 | LLM cost |
|---|---|
| Step 1 dump（pre-harness） | ~$0.50 |
| Phase 0 smoke（×2） | ~$0.80 |
| Phase 1 Anthropic baseline（含中断那次） | ~$6 |
| Phase 1 DeepSeek smoke | ~$0.01 |
| Phase 1 DeepSeek baseline | ~$0.20 |
| Phase 2 sanity check | ~$0.02 |
| Phase 3 post-fix N=50 + regression | ~$1.20 |
| **合计** | **~$9（区间 $7-12）** |

精确数字看 [Anthropic Console](https://console.anthropic.com/settings/usage) + [DeepSeek Platform](https://platform.deepseek.com/usage) 的 today/this-month 用量。

---

# Part 2 — 未完成

## 当前决策点

🚦 流程门 2 三条阈值全过，需要用户在 4 个选项里拍板才能继续：

| 选项 | 投入 | 收益 | 风险 |
|---|---|---|---|
| **(a) 精简 C** ← 推荐 | ~5-7 工作日 | BYOK 一致性 + v1.5 前瞻 + bullet 升级到"shipped abstraction" | MiMo 注册 + tool_choice=auto 兼容性需实测 |
| (b) 暂停投简历 | 0 | 当前 bullet 已是强 bullet | 错过升级窗口 |
| (c) 完整 C（5 家 Tier 1） | ~10-12 工作日 | "6 provider 适配" — AI 工程岗最爱 | 单 user 工程量大 |
| (d) 直接前置 Phase 5（验 MiMo）| ~0.5-1 日 | 快速拿 cross-provider 第三家数据 | 不构成完整方案 |

---

## 选项 (a) 精简 C 详细计划

### Phase 4 — 设计 C（编码 5-6h）

| ID | 子任务 | 估时 |
|---|---|---|
| **T4.0** | QuestionList Pydantic schema → OpenAI strict mode 验证（required 全字段、`additionalProperties: false`、no `$ref`、no recursive） | 1.5h |
| T4.1 | `providers/base.py` 加 `call_with_schema` + `capabilities` + `tier` abstract methods | 0.5h |
| T4.2 | 写 `docs/byok-tiers.md`（capability 矩阵 + 用户分档） | 1h |
| T4.3 | 决定错误语义：schema 验证失败 → A 层 retry vs raise | 0.5h |
| T4.4 | **Anthropic tool_use × cache_control 兼容性测试**（cache_read_input_tokens 比例验证） | 1.5h |
| **T4.4.x** | 🚦 流程门 3：cache hit rate 降幅 > 20% 停下重新设计 cache 策略 | — |

### Phase 5 — MiMo 验证（编码 2h + 注册）

| ID | 子任务 | 估时 |
|---|---|---|
| T5.1 | 注册 platform.xiaomimimo.com + API key + 充值 | ~30min（外部） |
| T5.2 | 加 MiMo 到 `PROVIDER_PRESETS`（OpenAI-compat 复用，capabilities 标 `force_tool_call=false`） | 30min |
| T5.3 | smoke test：单 chat 通 base_url + auth | 30min |
| T5.4 | **关键测试**：N=10 次 `tools=[record_questions]` + `tool_choice="auto"` 看 tool-call 实际触发率 | 1h |
| T5.5 | sanity check provider 内部三步 fallback（tool→json_object→text+repair）按设计工作 | 30min |

### Phase 6 — 精简 C Tier 1（编码 4h）

| ID | 子任务 | 估时 |
|---|---|---|
| T6.1 | Anthropic `call_with_schema` 用 tool_use + force tool_choice | 2h |
| T6.6 | MiMo `call_with_schema`（含三步 fallback） | 1.5h |
| T6.8 | 这 2 家的单测（mock 响应） | 0.5h |

### Phase 7 — Tier 2/3 默认 fallback（编码 1h）

| ID | 子任务 | 估时 |
|---|---|---|
| T7.2 | Tier 3 default：`call_with_schema` 调 `call_json` + repair → 应用到 Wenxin/custom + 其他未单独实现的 | 1h |

精简 C 时跳过 T7.1（Qwen/Zhipu/Kimi 不实现 Tier 2 helper，继续走现有 call_json 路径）。

### Phase 8 — 切换调用点 + 集成（编码 2h）

| ID | 子任务 | 估时 |
|---|---|---|
| T8.1 | `generate_questions` 切到 `call_with_schema` | 30min |
| T8.2 | 现有单测调整 | 1h |
| T8.3 | trace 字段补 tool_calls / tier capture | 30min |

### Phase 9 — 跨 provider 验证（编码 2h + LLM wallclock）

| ID | 子任务 | 估时 |
|---|---|---|
| T9.1 | Anthropic 跑 4 case × N（按流程门 1 算的 N） | 0.5h 编码 + ~1h wallclock |
| T9.2 | MiMo 跑同样（轻量 N） | 0.5h + ~1h wallclock |
| T9.3 | 写 `eval/diagnostics/AC_validation_final.md` | 1h |

### 精简 C 总计

| Phase | 编码 | LLM wallclock |
|---|---|---|
| 4 设计 | 5-6h | ~10min cache test |
| 5 MiMo | 3h | ~30min |
| 6 Tier 1 | 4h | — |
| 7 Tier 2/3 | 1h | — |
| 8 集成 | 2h | — |
| 9 验证 | 2h | ~2-3h |
| **合计** | **~17-18h** | **~3h** |

按 4h/day 有效编码 ≈ **5 个工作日 ≈ 1 周**。

### 精简 C 完成后简历 bullet

> "Designed schema-enforced output abstraction (capability-flag-driven `call_with_schema` interface) and shipped Tier-1 implementation for Anthropic + MiMo with internal fallback for tool_choice=auto limitation. Validated **<0.5% [目标待验证]** structured-output failure rate across providers via dual-layer defense (schema enforcement at provider + json-repair at parse layer)."

> ⚠️ **`<0.5%` 是 Phase 9 完成后的目标，非已验证结论**。Phase 3 已验证的是 DeepSeek 上 0/100 → Wilson [0%, 3.7%]；Phase 9 跑完 Anthropic + MiMo 后才会有真实跨 provider 数字。简历投递前请用实测值替换。

---

## 选项 (c) 完整 C 详细计划

精简 C 的基础上 Phase 6 扩到 5 家：

| ID | 子任务 | 估时（额外）|
|---|---|---|
| T6.2 | OpenAI `call_with_schema` 用 response_format=json_schema | 1.5h |
| T6.3 | OpenAI-compat 基类抽 helper（DeepSeek/Doubao/MiMo 共用） | 1h |
| T6.4 | DeepSeek（复用 helper） | 1h |
| T6.5 | Doubao（复用 helper） | 1.5h |
| T6.7 | Gemini `call_with_schema` 用 responseSchema | 2h |
| T7.1 | Tier 2 helper 应用到 Qwen/Zhipu/Kimi | 2h |
| T9.1 | Phase 9 扩到 6 家 provider 验证 | +2h 编码 + ~3h wallclock |

完整 C 总计：**~25 工作时数 + ~6h LLM wait** ≈ **8 个工作日 ≈ 2 周**。

完整 C 完成后简历 bullet：

> "Designed schema-enforced output abstraction across 6 LLM providers (Anthropic tool_use, OpenAI/DeepSeek/Doubao response_format strict, Gemini responseSchema, MiMo with tool_choice fallback chain). Achieved **<0.5% [目标待验证]** structured-output failure rate via dual-layer defense, validated with N=Z stratified resampling × {pm, data, ai} role × {jd, no-jd} matrix."

> ⚠️ **`<0.5%` 和 `N=Z` 都是 Phase 9 完成后的目标占位，非已验证结论**。Phase 9 跑完才能填实测数字（N=Z 替换为真实 N，<0.5% 替换为真实 Wilson 上界）。投简历前必须实测覆盖。

---

## 选项 (d) 单独前置 Phase 5（不进 C）

只做 Phase 5（注册 + smoke + N=10 baseline + tool_call 触发率测试）：

- 工程量：~3-4h 编码 + 注册时间
- LLM 成本：~$0.50（MiMo 充值最小额度）
- 收益：拿到 cross-provider 第三家数据（Anthropic + DeepSeek + MiMo），bullet 加 "validated across 3 providers"
- 不构成完整 C 方案，但是个低成本 quick win

---

## 还需注意的状态项

### 资产清单（不要丢）

- `memory.md` — 跨 session 进度日志（包含 Phase 0/1/2/3 详细记录）
- `eval/diagnostics/A_validation_2026-05-02.md` — Phase 3 报告（简历数据来源）
- `eval/runs/2026-05-02T0419-d034a2a/` — DeepSeek pre-fix N=10 baseline
- `eval/runs/2026-05-02T043721-d034a2a/` — Post-fix N=50 主验证
- `eval/runs/2026-05-02T043732-d034a2a/` — Regression N=18

### git 状态（未 commit）

```
Modified:
 M backend/pyproject.toml                              ← + json-repair
 M backend/src/mockinterview/agent/client.py           ← 重写 parse + retry
 M backend/tests/test_agent_client.py                  ← 3 → 12 tests
 M backend/uv.lock
 M eval/.gitignore                                     ← + runs/
 M memory.md                                           ← Phase 0/1/2 进度日志

Untracked:
?? eval/__init__.py                                    ← 让 eval 成 package
?? eval/diagnostics/                                   ← Phase 3 验证报告
?? eval/harness/                                       ← Minimal harness 全部源码
```

未 commit 是有意为之 — 用户的 standing rule 是只在用户明确请求时才 commit。后续 session 启动可以请求 commit Phase 0+1+2+3 整体作为一个里程碑。

### 已知风险 / 待办

1. `consume_last_parse_record` 是 ContextVar 通道，**线程穿透行为没单测过**（FastAPI 用 anyio 跨 thread 时是否传播）。当前没影响因为 harness 是单线程脚本调用，但 Phase 6+ 切换到 prod 调用路径时要验证一次
2. trace.json 的 `cost_estimate_usd` 仍是 0.0 占位 — provider 未透出 token usage，Phase 4+ 可能要加 usage 抽取
3. `eval/run_eval.py`（旧 orchestrator）暂未删除 — 用户先前指示"逐步迁，不破坏"，等完整 harness 时机再清理
4. eval/__init__.py 命名 `eval` 与 builtin `eval()` 不冲突（builtin 不走 import 系统），但要注意 `python -m eval.harness.cli` 必须从 repo root 跑或加 PYTHONPATH=..

---

## 流程门状态总览

| 流程门 | 触发位置 | 状态 |
|---|---|---|
| 🚦 1 — N 决策 | Phase 1 末 | ✓ 通过（用户拍 N=50） |
| 🚦 2 — 精简/完整 C | Phase 3 末 | ⏸ **当前位置** — 三条阈值全过，等用户拍方向 |
| 🚦 3 — Cache hit 降幅 | Phase 4 T4.4.x | 未到（C 启动后才会触发） |
