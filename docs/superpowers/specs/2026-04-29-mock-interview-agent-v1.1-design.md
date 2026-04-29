# MockInterview Agent v1.1 设计文档

| 字段 | 内容 |
|---|---|
| 版本 | v1.1 |
| 日期 | 2026-04-29 |
| 前置版本 | v1.0（已 ship；Live: https://mockinterview-agent.vercel.app） |
| 设计方法 | 沿用 v1 brainstorming → writing-plans → subagent-driven-development 工作流 |
| 状态 | 待实施（用户已批准设计稿） |

---

## §0. v1.1 顶层叙事

v1.0 ship 后用户的两大高频痛点：**配置切换成本高 + 输入门槛偏高**。v1.1 用三个互相支撑的小 feature 同时降这两条——多组保存让"换 provider 比效果"成本归零、连接测试让"踩 JSON 解析坑"在 setup 阶段就暴露、语音输入让回答门槛降到接近真实面试。三个 feature 共享一条主线：**让 BYOK 体验从"可用"升级到"称手"**。BYOK 服务器零持有 key 的硬约束完全不动。

**v1.1 完整范围（10 项）**：

核心三件套：
1. 多组 provider 配置保存与切换
2. 连接测试（最小 token 验证 provider+model+key 可用 + JSON 输出能力）
3. 语音输入（speech-to-text，文本最终落 textarea）

辅助配套（Tier S 纳入项）：
4. localStorage 数据丢失警告 banner
5. 全局语音识别语言开关（zh-CN / zh-TW / en-US）
6. 配置导出 / 导入 JSON
7. 顶部导航快速切换器
8. 默认配置 ⭐ 标记
9. API key 显隐切换通用组件
10. BYOK 不变量 self-check 写入文档

---

## §1. Feature 1：多组配置保存与切换

### 1.1 数据模型（前端 only，存 localStorage）

```ts
// frontend/src/lib/provider-config.ts
type SavedConfig = {
  id: string;              // uuid v4，内部使用，不暴露给用户
  name: string;            // 用户起的名字（trim 后非空，不强制全局唯一）
  provider: ProviderKind;  // 沿用 v1.0 的 10 种
  apiKey: string;          // 沿用 BYOK，仍仅存浏览器
  model: string;
  baseUrl: string;
  createdAt: number;       // ms timestamp
  lastTestedAt: number | null;       // 上次连接测试时间
  lastTestStatus: "ok" | "fail" | null;
};

type ProviderConfigStore = {
  configs: SavedConfig[];
  activeId: string | null;   // 当前使用中
  defaultId: string | null;  // 删除 active 时自动 fallback 到这个；可与 activeId 一致
};

// 独立 key（与 provider 无关的 UI 偏好）
type UiPrefs = {
  speechLang: "zh-CN" | "zh-TW" | "en-US";  // v1.1 仅三选一
};
```

localStorage 键名：
- 旧：`mockinterview.providerConfig`（v1.0 单 config，保留 90 天作 fallback）
- 新：`mockinterview.providerStore`（新结构）
- 新：`mockinterview.uiPrefs`（UI 偏好）

### 1.2 v1.0 → v1.1 静默迁移

启动时检测：

1. 如果 `mockinterview.providerStore` 存在 → 直接用
2. 如果只有 `mockinterview.providerConfig`（v1.0 旧用户）→ 包成单 config 数组：
   ```ts
   {
     configs: [{
       id: uuidv4(),
       name: "默认配置",
       ...旧字段,
       createdAt: Date.now(),
       lastTestedAt: null,
       lastTestStatus: null,
     }],
     activeId: <id>,
     defaultId: <id>,
   }
   ```
3. 旧 key 保留不删（90 天回滚兼容）

### 1.3 Setup 页面布局

`/setup` 改造为**两栏**：

- **顶部 banner**（蓝色 info 样式，不可关闭）：「⚠️ 配置仅存于此浏览器。换浏览器或清缓存会全部丢失，建议导出 JSON 备份」
- **左侧 saved config 列表**（卡片）：
  - 字段：用户起的 name、provider 图标、model、状态点（绿=lastTestStatus=ok / 灰=null / 红=fail）、⭐（如果是 defaultId）
  - actions：「使用」「编辑」「设为默认」「复制」「删除」
- **右侧 编辑表单**：
  - 沿用 v1.0 三段：选 Provider / 粘 Key / Model + Base URL
  - Key 输入用 §2.5 的 `<SecretInput>` 通用组件（password type + 👁 显隐切换）
  - 新增「配置名称」字段（必填）
  - 底部 actions：「保存」「保存并测试连接」「取消」
  - 新增配置时左侧选「+ 号卡片」，编辑时左侧选具体卡片
- **底部独立小区块**：语音识别语言（zh-CN / zh-TW / en-US 单选）+ 简短说明
- **底部第二个独立小区块**：「导出全部配置 JSON」按钮 + 「导入 JSON」上传按钮

### 1.4 切换激活 config 的行为

- 左侧「使用」按钮 → `activeId = <id>` → 顶部 toast「已切换到 <name>」→ 不强制重测
- 若该 config 的 `lastTestStatus === "fail"` → 切换前弹确认框「这个配置上次测试失败，确定使用？」
- 删除 active config → 若 `defaultId` 存在且不同则自动切到 defaultId；否则切到列表第一个；列表空了则跳 onboarding `/setup?next=...`

### 1.5 配置导出/导入

- **导出**：`JSON.stringify({ version: "v1.1", configs: [...], exportedAt: now })` 触发浏览器下载 `mockinterview-configs-YYYY-MM-DD.json`
- **导入**：上传 JSON → 校验 version 字段 → 与现有 configs **merge by id**（同 id 覆盖、新 id 追加）→ 不自动改 activeId
- 导出文件含明文 key——**导出时弹确认框警告**「文件含 API key 明文，请妥善保管」

### 1.6 顶部导航快速切换器

`<ConfigSwitcher>` 组件嵌入 `frontend/src/app/layout.tsx` 顶部，所有页面可见：

- 显示当前 active config 的 name + provider 图标 + 状态点
- 点击 → dropdown 列出全部 configs，每条点击直接切换
- 底部「管理配置 →」跳 `/setup`

### 1.7 兼容性

- `lib/api.ts` 的 `providerHeaders()` 改为读 `getActiveConfig()` —— active id 找 SavedConfig → 取 4 个 X-\* 字段
- 旧 export `getProviderConfig()` / `setProviderConfig()` 标记 deprecated 但仍能用，内部委托新 store

### 1.8 BYOK 影响

✅ **完全不破坏**——所有新增数据全在客户端 localStorage，后端零改动以承载多 config。X-\* header 透传协议不变，后端 `use_provider` Depends 没感知到上游有多组配置。

---

## §2. Feature 2：连接测试

### 2.1 后端新增 endpoint

```python
# backend/src/mockinterview/routes/provider.py（新文件）
from fastapi import APIRouter, Depends
from mockinterview.routes._deps import use_provider
from mockinterview.agent.providers import get_active

router = APIRouter()

@router.post("/provider/test")
async def test_provider(
    _: None = Depends(use_provider),
) -> ProviderTestResult:
    """用最小 token 验证 provider+model+key 可用且能产出 JSON。"""
    p = get_active()
    return await p.test_connection()
```

### 2.2 ProviderTestResult schema

```python
class ProviderTestResult(BaseModel):
    ok: bool
    category: Literal["ok", "network", "auth", "rate_limit", "json_format", "unknown"]
    http_status: int | None       # 下游 provider 真实 HTTP 状态
    provider_message: str | None  # 下游 provider error message 原文
    raw_response: str | None      # JSON 解析失败时返回 body 前 500 字符
    elapsed_ms: int               # 端到端耗时
```

### 2.3 测试 prompt（跨 10 provider 统一）

```
System: You are a connection test endpoint. Reply ONLY with valid JSON: {"ok": true, "echo": "<the user message verbatim>"}. No prose, no markdown, no code fence.
User: ping
max_tokens: 30
temperature: 0
```

每个 `LLMProvider` 子类实现 `test_connection()`，**独立于 `generate()`** 写——确保 max_tokens=30 严格生效，避免某些 provider 在通用 generate 路径下不传 max_tokens 的情况。

### 2.4 错误分类逻辑

| Category | 触发条件 | http_status |
|---|---|---|
| `ok` | HTTP 200 + body 可解析 JSON + 含 `ok: true` | 200 |
| `network` | requests 异常 / DNS / connection refused / 5xx | 502/503/504/None |
| `auth` | 401 / 403 | 401/403 |
| `rate_limit` | 429 | 429 |
| `json_format` | HTTP 200 但 body 非 JSON / 缺 `ok` 字段 | 200 |
| `unknown` | 其他（4xx 非 401/403/429） | 4xx/* |

### 2.5 SecretInput 通用组件

`frontend/src/components/secret-input.tsx`——独立组件，setup 页 key 字段 + 编辑表单 key 字段都用：

```tsx
type SecretInputProps = {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
};
// 内部：type=password 默认，加 👁 toggle 切换 type=text
```

### 2.6 连接测试 Dialog

`frontend/src/components/connection-test-dialog.tsx`：

- **测试中**：spinner + 「正在调用 <provider> 的 <model>…」+ 实时计时（HH:mm:ss）
- **成功**：✅ + 「连接 OK ($elapsed ms)」+ 自动 2 秒关弹窗
- **失败**：❌ + **三段式精确报错**：
  1. **类别标题**（中文）：
     - `network` → 「网络不通」
     - `auth` → 「认证失败」
     - `rate_limit` → 「触发速率限制」
     - `json_format` → 「模型 JSON 输出不规范」
     - `unknown` → 「未知错误」
  2. **HTTP status + provider message**（等宽字体、可一键复制）
  3. **行动建议**（按 category 文案，中性）：
     - `network` → 「请检查 base_url 是否正确，或 provider 服务可能临时不可用」
     - `auth` → 「key 可能无效、过期或没有该 model 的访问权限」
     - `rate_limit` → 「触发限流。可能是当前账户配额或并发限制，请稍后重试或检查 provider 控制台」
     - `json_format` → 「该 model 在 JSON 输出上不可靠，agent 模块解析时容易失败。建议换 model 或换 provider 后重测」+ 折叠区显示 raw response 前 500 字符
     - `unknown` → 「请截图本弹窗反馈：https://github.com/sereeein/MockInterview-Agent/issues」

### 2.7 测试触发与状态联动

- Setup 编辑表单底部「保存并测试连接」按钮（除「保存」「取消」外的第三个 action）
- 「测试连接」也可在不保存的情况下独立调用（按钮另存为「先测试」）
- 测试通过 → `lastTestedAt: Date.now()`, `lastTestStatus: "ok"`
- 测试失败 → `lastTestStatus: "fail"`，**仍允许保存**（用户可以保存未通过的配置；切换到时会被警告，§1.4）
- 任何字段被编辑 → `lastTestStatus` 自动重置为 `null`（避免假绿点欺骗）

---

## §3. Feature 3：语音输入

### 3.1 组件抽象

`frontend/src/components/voice-input.tsx`：

```tsx
type VoiceInputProps = {
  onTranscript: (text: string, isFinal: boolean) => void;
  onError: (msg: string) => void;
  disabled?: boolean;
  lang?: string;   // 默认从 uiPrefs.speechLang 读
};
```

drill 页和 mock 页**用同一个组件**。

### 3.2 Web Speech API 封装

```ts
// frontend/src/lib/speech.ts
export type SpeechSupport =
  | { supported: true }
  | { supported: false; reason: "no-api" | "not-secure-context" };

export function detectSpeechSupport(): SpeechSupport;

export type Recognizer = {
  start(): void;
  stop(): void;
};

export function createRecognizer(opts: {
  lang: string;
  onResult: (text: string, isFinal: boolean) => void;
  onError: (errorCode: string) => void;
  onEnd: () => void;
}): Recognizer;
```

封装关键决策：
- 用 `(window as any).webkitSpeechRecognition || (window as any).SpeechRecognition`
- `continuous: true`（用户停顿不自动终止）
- `interimResults: true`（边说边显示）
- `maxAlternatives: 1`

### 3.3 UX：点击切换 mode

| 状态 | 按钮外观 | textarea 行为 |
|---|---|---|
| **Idle** | 🎙 灰色图标 | 用户键盘正常输入 |
| **Recording** | 🔴 红点 + 脉冲动画 + tooltip "再次点击停止" | interim 文字以**浅灰**拼到末尾；final 文字转黑 |
| **Stopping** | spinner 0.3s | textarea 短暂锁定 |
| **Error** | 灰色 + 红 ⚠ | textarea 上方红字 3s 内淡出 |

**自动停止**：用户再次点击 / Web Speech API 自身 onend / textarea 失焦超过 30 秒。**不做静默检测**。

### 3.4 错误兜底文案

| 错误 | 用户看到 |
|---|---|
| `detectSpeechSupport()` not supported | **按钮不渲染** |
| `NotAllowedError`（permission denied） | 「需要麦克风权限。在浏览器地址栏左侧点击🔒重新授权」 |
| `network`（中国大陆 Chrome 不可达 Google） | 「语音识别需要联网到识别服务，当前网络不可用。请用键盘输入」 |
| `no-speech` | 静默忽略，自动停 |
| 其他 unknown | 「语音识别出错：<原始 errorCode>。请用键盘输入」 |

### 3.5 集成位置

[drill/[id]/page.tsx:46](frontend/src/app/drill/[id]/page.tsx#L46) 既有 Textarea 改造为 `relative` 容器，`<VoiceInput>` 绝对定位 `right-2 bottom-2`。Mock 页 [mock/[id]/page.tsx](frontend/src/app/mock/[id]/page.tsx) 同样处理。

### 3.6 全局语言开关

`UiPrefs.speechLang` 在 setup 页底部独立小区块单选：「中文（普通话）/ 中文（台湾）/ English（US）」。语音输入组件初始化时读取此值。

### 3.7 BYOK 影响

✅ **完全不破坏**——音频从不进我们的后端。Web Speech API 是浏览器调用系统/Google STT，全程在客户端。后端零改动。

### 3.8 未来 v1.2 升级路径（保留口子）

`<VoiceInput>` 组件接口设计成可替换实现——未来加 BYOK Whisper 兜底时（C 方案），仅替换 `lib/speech.ts` 的实现，不动调用方。

---

## §4. 跨 feature 共同事项

### 4.1 测试策略

| 层 | 做什么 |
|---|---|
| **后端单测** | `provider/test` endpoint 6 类返回（ok / network / auth / rate_limit / json_format / unknown）mock；3 个 provider impl 各 1 个 happy path 单测 |
| **后端集成** | 沿用 v1.0 的真 LLM fixture（仅 Anthropic key 在 CI），加 1 条 `test_provider_test_anthropic_real_key` 验证 prompt 设计实际能产出 JSON |
| **前端**（沿用 v1.0 节奏，无单测框架） | 每 task 手动 smoke test；§6 ship 清单端到端手测 |

**verification gate**：63 后端测试 + v1.1 后端新增 ≥ 9 个测试全过。前端走 lint + typecheck + 手测三件套。

### 4.2 部署影响

- **后端**：新增 `provider.py` route + provider impl 加 `test_connection`。需要重新 build Docker image 推 Railway，旧 v1.0 流量在 deploy 期间约 30s 间隔不可用——可接受
- **前端**：纯 Next.js 16 增量改动，Vercel preview → prod，零 schema 迁移
- **localStorage migration**：在 `provider-config.ts` 启动检测 + 静默升级，保留旧 key 90 天

### 4.3 BYOK 不变量验证

写入 `docs/byok.md` 新增段落「v1.1 BYOK self-check」：

> v1.1 新增三个核心 feature 后，BYOK 仍成立的证据：
> - 多组 config 全部存在客户端 localStorage —— `git grep "save.*api.*key.*db" backend/` 应返回 0
> - 连接测试 endpoint 复用 `use_provider` Depends，key 走 header 透传，请求结束即丢弃
> - 语音 STT 在浏览器本地完成，音频从不进后端 —— `grep "audio" backend/src/mockinterview/routes/` 应只命中 0 条业务路径

### 4.4 放弃了什么 + 为什么（v1.1 简历叙事）

| 放弃 | 理由 |
|---|---|
| 后端账号体系 + 云端 config 同步 | 破坏 BYOK 零运营成本叙事；用户 100% 单设备使用，跨设备同步价值低；v1.1 是迭代不是重构 |
| 连接测试跑迷你 question_gen | token 成本是 JSON ping 的 4 倍 + 跨 10 provider 超时风险更高；JSON ping 已覆盖 agent 6 个模块的统一 JSON 输出约束 |
| Whisper / 云 STT 兜底 | 引入新 BYOK 维度（额外 STT key）+ 后端 audio endpoint，工程量等同独立 v1.5 feature；Web Speech API 50-60% 可用率 + 优雅降级已能讲清差异化故事；v1.2 留口子可补 |
| 语音"按住说话" | 面试场景需要键盘修改原文，按住反人类；点击切换支持打字+语音混合输入 |
| 浏览器原生 TTS 朗读题目 | 中文音色机械感强，可能 ship 后被吐槽；与语音输入耦合度不如导出/导入紧；v1.2 候选 |
| 静默自动停止录音 | 检测复杂度引入收益不明；v1.1 依赖用户手动停 + textarea 失焦超时兜底 |

### 4.5 Out-of-scope（明确不做，记录 v1.5+ 候选）

- 多人协作 / 共享配置 / 团队空间（V3.0 体量）
- TTS 朗读题目（v1.2 候选）
- BYOK Whisper 云 STT 兜底（v1.2 候选）
- Token usage 仪表盘（Phase 5 P0 已立项，独立做）
- 连接测试历史 / 趋势图（over-engineering）
- 配置加密（明文 localStorage 是 BYOK 透明性的一部分）

---

## §5. 任务切分

每个 task 末尾「self-check + smoke test + 等用户 confirm」三段式 gate。**用户 confirm 才进下一个 task**。

### T1 — 前端数据模型升级（~2h）

**改动**：
- 重写 `frontend/src/lib/provider-config.ts`：`SavedConfig` / `ProviderConfigStore` / `getActiveConfig` / `addConfig` / `updateConfig` / `deleteConfig` / `setActive` / `setDefault` / migration
- 新建 `frontend/src/lib/ui-prefs.ts`：`UiPrefs` get/set
- 修改 `frontend/src/lib/api.ts` 的 `providerHeaders()` 读 active
**self-check**：
- `cd frontend && npx tsc --noEmit`
- `cd frontend && npx next lint`（如未配置则跳过）

**smoke test**：本地 dev server 跑通 v1.0 旧用户访问 → 自动迁移到新结构（DevTools 看 localStorage 验证）→ 现有 drill 流程不破

### T2 — 后端连接测试 endpoint（~2h）

**改动**：
- 新建 `backend/src/mockinterview/routes/provider.py`
- 新增 `ProviderTestResult` Pydantic schema（5 类 category + ok）
- 给 `agent/providers/anthropic.py` / `openai_compat.py` / `gemini.py` 各加 `test_connection() -> ProviderTestResult`，**独立于 generate()**
- `app.py` 注册 router
- 单测：6 类返回 mock + 1 真 LLM happy path（Anthropic key）

**self-check**：
- `cd backend && uv run pytest`（63 + 新增 ≥ 7 个测试全过）

**smoke test**：本地 backend 跑起来，`curl POST /provider/test` 用真 Anthropic key + claude-haiku-4-5 测一次返回 ok

### T3 — 前端连接测试 UI 组件（~1.5h）

**改动**：
- 新建 `frontend/src/components/secret-input.tsx`（password type + 👁 toggle）
- 新建 `frontend/src/components/connection-test-dialog.tsx`（spinner / 成功 / 5 类失败渲染）
- `lib/api.ts` 加 `testProvider()` 调用 `/provider/test`

**self-check**：
- `cd frontend && npx tsc --noEmit`

**smoke test**：临时挂在某页面手动调用 dialog 5 次（每次塞不同的 ProviderTestResult mock），目测 5 类错误 UI 都能渲染

### T4 — 前端 setup 页大改（~3h）

**改动**：
- 重写 `frontend/src/app/setup/page.tsx`：左右栏布局 + banner
- 左侧：saved config 列表卡片 + CRUD actions + ⭐ 默认标记 + 状态点
- 右侧：编辑表单 + name 字段 + secret-input + 「保存」「保存并测试」「取消」
- 底部：语音语言选择 + 导出/导入 JSON
- 集成 T3 的 ConnectionTestDialog
- 删除最后一个 config → 跳 onboarding

**self-check**：
- `cd frontend && npx tsc --noEmit`

**smoke test**：完整 flow——新建/编辑/复制/删除/切换 4 组 config + 导出 JSON + 清 localStorage + 导入 JSON + 切换默认 + 测试连接成功 / 失败两条路径

### T5 — 前端语音输入（~2h）

**改动**：
- 新建 `frontend/src/lib/speech.ts`（detectSpeechSupport / createRecognizer）
- 新建 `frontend/src/components/voice-input.tsx`
- 修改 `frontend/src/app/drill/[id]/page.tsx`：textarea 包 relative + 嵌入 voice-input
- 修改 `frontend/src/app/mock/[id]/page.tsx`：同上
- 错误兜底文案

**self-check**：
- `cd frontend && npx tsc --noEmit`

**smoke test**：drill 页 + mock 页各跑一次：点击 🎙 → 录音（Chrome macOS）→ 浅灰 interim → 黑色 final → 再次点击停 → 修改 → 发送；Firefox 验证按钮不渲染

### T6 — 顶部切换器 + 收尾（~1.5h）

**改动**：
- 新建 `frontend/src/components/config-switcher.tsx`
- 修改 `frontend/src/app/layout.tsx` 嵌入到顶部
- 编辑 `docs/byok.md` 加 v1.1 self-check 段落
- 完整 §6 ship 清单端到端验证
- 追加 `memory.md` 顶部 v1.1 ship entry
- `git tag v1.1 && git push --tags`

**self-check**：
- 全后端测试 + 全前端 lint/typecheck 全过
- BYOK self-check 两条 grep 验证 0 命中

**smoke test**：§6 ship 清单全打勾

---

## §6. ship 清单

- [ ] 6 个 task 顺序完成 + 每步 user-confirm gate 通过
- [ ] 后端 63+ 测试全过 + v1.1 后端新增 ≥ 9 个测试；前端 typecheck 全过
- [ ] Vercel preview deploy 绿
- [ ] 旧 v1.0 用户访问 → 自动 migration 无感升级
- [ ] 连接测试 5 类错误（含 429）UI 都能正确渲染
- [ ] 语音输入在 Chrome（macOS）实测可用；Firefox 实测 fallback 不渲染按钮
- [ ] 导出 JSON → 清 localStorage → 导入 JSON 恢复
- [ ] 顶部切换器在所有页面可见
- [ ] BYOK self-check（两条 grep 0 命中）
- [ ] git tag v1.1 + push
- [ ] memory.md 顶部新 entry：v1.1 ship 摘要

---

## 附录：关键耦合 / 实施约束

1. **frontend/AGENTS.md 强制**：Next.js 16 有 breaking change vs 训练数据；写代码前必读 `node_modules/next/dist/docs/` 相关章节
2. **每 task 末必须追加 memory.md entry**（沿用 v1.0 工作流）：task ID / 完成时间绝对日期 / 改动文件 / 决策 / 验证命令 / commit hash
3. **每 task 末停下等 user confirm 才进下一个**——auto mode 也不例外
4. **BYOK 不变量**——任何改动后服务器仍 0 持有 key；所有新 feature 不引入 server-side key 持久化
