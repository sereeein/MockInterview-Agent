# Phase 3 — A Validation Report (2026-05-02)

**Provider under test**: DeepSeek (`deepseek-chat`) via `MOCK_PROVIDER=deepseek`
**Judge provider**: not used in Phase 3 (judges deferred to full harness phase)
**Code state**: phase-2 post-fix (`backend/src/mockinterview/agent/client.py` rewritten with json-repair fallback + retry)

## Headline result

| | Pre-fix (Phase 1) | Post-fix (Phase 3) | Δ |
|---|---|---|---|
| `pm_alpha_self` failure rate | 7/10 = 70% | **0/50 = 0%** | -70 pp |
| `other_no_jd` failure rate | 1/10 = 10% | **0/50 = 0%** | -10 pp |
| **Pooled failure rate** | **8/20 = 40%** | **0/100 = 0%** | **-40 pp** |
| Pooled + regression | — | **0/118 = 0%** | — |

**Pooled Fisher's exact (pre 8/20 vs post 0/100): p = 1.5 × 10⁻⁷** — highly significant.

## Wilson 95% CIs on post-fix failure rate

| Cohort | k/n | 95% CI |
|---|---|---|
| `pm_alpha_self` post-fix | 0/50 | [0.0%, 7.1%] |
| `other_no_jd` post-fix | 0/50 | [0.0%, 7.1%] |
| Pooled post-fix (validation only) | 0/100 | **[0.0%, 3.7%]** |
| Pooled + regression | 0/118 | [0.0%, 3.2%] |

Upper bound 3.7% on pooled — **clearly below the 5% target** the user set at flow gate 1.

## Per-case Fisher's exact

| Case | Test | p-value | Significant? |
|---|---|---|---|
| `pm_alpha_self` | pre 7/10 fail vs post 0/50 fail | **3.1 × 10⁻⁷** | ✓✓✓ |
| `other_no_jd` | pre 1/10 fail vs post 0/50 fail | 0.17 | ✗ (low pre-fix rate; expected per Phase 1 design — see *pooled framing*) |
| Pooled | pre 8/20 fail vs post 0/100 fail | **1.5 × 10⁻⁷** | ✓✓✓ |

`other_no_jd` was always going to be statistically weak alone (10% pre-fix rate over N=10 → low effect size).
The pooled framing was specified at flow gate 1 to handle exactly this — and it does.

## Regression check (6 previously-stable cases on DeepSeek)

| Case | n | succ/n | Wilson 95% CI |
|---|---|---|---|
| `pm_bytedance_self` | 3 | 3/3 | [44%, 100%] |
| `pm_no_jd_friend` | 3 | 3/3 | [44%, 100%] |
| `data_shopee_friend` | 3 | 3/3 | [44%, 100%] |
| `ai_no_jd` | 3 | 3/3 | [44%, 100%] |
| `ai_alpha` | 3 | 3/3 | [44%, 100%] |
| `data_no_jd` | 3 | 3/3 | [44%, 100%] |
| **Pooled** | **18** | **18/18** | **[82%, 100%]** |

No regression observed. Wilson CIs are wide due to N=3 per case (cost-saving choice; pooled CI [82%, 100%] is the meaningful number).

## Retry & repair statistics (post-fix only)

Across 100 validation attempts × 2 LLM calls each = 200 LLM calls:

| Metric | Count | Rate |
|---|---|---|
| Calls per attempt = 2 (no retry) | 100/100 | 100% |
| Calls per attempt > 2 (retry triggered) | 0/100 | 0% |
| `parse_status: repaired` (json-repair invoked) | 0/200 | 0% |
| `parse_status: success` (clean json.loads) | 200/200 | 100% |

**json-repair fallback was never invoked in the post-fix run.** This is a notable finding —
see "Honest interpretation" below.

## Honest interpretation: what actually fixed it

We expected json-repair to do the heavy lifting on the failure cases. **It didn't have to.**
Zero of the 100 post-fix attempts triggered the repair path or the retry path.

Two changes were shipped together in Phase 2 inside [`backend/src/mockinterview/agent/client.py`](../../backend/src/mockinterview/agent/client.py):

1. **Removed Chinese curly-quote replacement from `_clean_json_payload`**
   The old cleanup had `.replace("“", '"').replace("”", '"')` running unconditionally on
   every payload. When a model legitimately used Chinese curly quotes inside a string
   value (`"text": "他说“你好”"`), the replacement converted them to ASCII quotes,
   creating *unescaped quotes inside a JSON string* — which then broke parse.
   This was a latent bug introduced as a "best-effort cleanup."
2. **Added json-repair fallback + retry** as a defense-in-depth safety net.

Because (1) addressed the actual root cause and (2) was never needed in 100 attempts,
the most likely interpretation is that **(1) was the real fix** and **(2) is now sitting
as belt-and-suspenders for edge cases we haven't seen yet**.

This doesn't weaken the result — failure rate genuinely dropped from 40% pooled to 0%.
But it changes the bullet's framing: the diagnostic insight (latent over-aggressive cleanup
breaking valid JSON) is the strongest part of the story, not the json-repair library swap.

We did not re-run pre-fix with only change (1) and only change (2) separately to attribute
the effect — that experiment would cost another 100 attempts and carry no Phase-3-decision
value. The combined effect is what we're shipping.

## Flow gate 2 criteria

Per the design doc §五 P3.5 (after the user's flow-gate-2 threshold loosening from 2% to 5%):

| Criterion | Threshold | Observed | Met? |
|---|---|---|---|
| `other_no_jd` post-fix failure rate | ≤ 5% | 0% (Wilson upper 7.1%) | ✓ |
| 6 stable case regression | none | 18/18 success, no regression | ✓ |
| retry trigger rate (A-layer re-prompt) | ≤ 5% | 0/100 = 0% | ✓ |

**All three thresholds met → recommend simplified C path** (Anthropic + MiMo Tier 1 only,
skip OpenAI/Gemini/DeepSeek/Doubao).

## Cost & duration

- LLM calls: 200 (validation) + 36 (regression) = **236 DeepSeek calls** ≈ **~$1.20**
- Wallclock: ~50 min (validation, parallel with regression ~9 min)

Compare to original Anthropic-based estimate of ~$24 — **20× cheaper** by switching to DeepSeek for the agent-under-test (judges remain on Anthropic in future phases).

## Run IDs (for replay)

- Phase 1 baseline (Anthropic, partial): `2026-05-02T0348-d034a2a` (credit-exhausted; pm_alpha_self attempts 1-4 are valid pre-fix Anthropic data)
- Phase 1 baseline (Anthropic, fresh): `2026-05-02T0356-d034a2a`
- Phase 1 baseline (DeepSeek): `2026-05-02T0419-d034a2a` *(note: minute-collision with this run's smoke test — pre-fix)*
- Phase 2 sanity: `2026-05-02T043455-d034a2a`
- **Phase 3 post-fix N=50**: `2026-05-02T043721-d034a2a`
- **Phase 3 regression**: `2026-05-02T043732-d034a2a`

## Artifacts

- Code change: [backend/src/mockinterview/agent/client.py](../../backend/src/mockinterview/agent/client.py)
- Tests: [backend/tests/test_agent_client.py](../../backend/tests/test_agent_client.py) (12 tests, all passing)
- Full backend test suite: 97 passed, 1 skipped post-fix

## Resume bullet (post Phase 3)

> Diagnosed structurally repeatable JSON parse failure on adversarial inputs across two
> LLM providers (Claude Opus 4.7, DeepSeek-Chat) — root cause was a latent over-aggressive
> Chinese-quote cleanup that corrupted valid JSON strings. Reduced attempt-level failure
> rate from 40% (pre-fix, N=20 pooled) to 0% (post-fix, N=100 pooled, 95% Wilson CI [0%, 3.7%];
> Fisher's exact p = 1.5 × 10⁻⁷). Shipped json-repair + retry as a provider-agnostic
> defense-in-depth layer alongside the root-cause fix.
