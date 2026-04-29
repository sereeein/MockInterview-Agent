# BYOK 架构说明

MockInterview Agent **不持有任何 API key**——每个用户用自己的 key 调 LLM。

## 这意味着什么

- 你打开 demo URL → 第一次访问跳到 `/setup` 让你粘自己的 key
- key 存在你浏览器的 localStorage（不会进我的服务器）
- 每次请求把 key 作为 `X-API-Key` header 透传给 backend → backend 即时构造 Provider client → 调 LLM
- 用完关浏览器或在 `/setup` 点"清空"就行

## 为什么这么设计

1. **零运营成本**：开发者（我）不替任何用户付费——上传 100 份简历也不会让我的 Anthropic 账单爆
2. **用户自控**：成本透明（用户能在自己 provider 控制台看到 token 用量）
3. **隐私**：简历内容只经过你信任的 provider 的服务器
4. **可扩展**：用户可以选自己最便宜的 provider（比如 DeepSeek 大概是 Anthropic 的 1/30 价格）

## 支持的 10 个 Provider

| Provider | 默认模型 | 类型 | 备注 |
|---|---|---|---|
| Anthropic Claude | `claude-opus-4-7` | 原生 | 推荐——prompt 调优在这上面，效果最稳 |
| OpenAI | `gpt-4-turbo` | 原生 | — |
| DeepSeek | `deepseek-chat` | OpenAI-compat | 国内可访问，便宜 |
| 通义千问 | `qwen-max` | OpenAI-compat (DashScope) | 阿里云 |
| 智谱 GLM | `glm-4-plus` | OpenAI-compat | — |
| Kimi (Moonshot) | `moonshot-v1-32k` | OpenAI-compat | 长上下文友好 |
| 文心一言 | `ernie-4.0-turbo-8k` | OpenAI-compat (千帆 v2) | 百度 |
| 豆包 | `doubao-pro-32k` | OpenAI-compat (火山方舟) | 字节 |
| Google Gemini | `gemini-2.0-flash-exp` | 原生 (google-genai) | — |
| Custom | 任意 | OpenAI-compat | 粘任何兼容的 base_url + key + model |

## 注意事项

- prompt 在 Claude 上调优。换其他 provider 时质量可能略降（具体多少要跑 eval 测）
- prompt caching 是 Anthropic 独有特性——其他 provider 没有这一项 70% 成本节省
- v1 还没做 token usage 统计（每次请求实际消耗多少 token 不在 UI 上显示）—— 用户在自己 provider 控制台看

## 工程实现要点

- Backend：`agent/providers/` 包定义 `LLMProvider` ABC + 3 实现（Anthropic / OpenAI-compat / Gemini）
- ContextVar `_active`：每个请求由 `routes/_deps.py:use_provider` Depends 设值
- 6 个既有 agent 模块 (drill_eval / question_gen / resume_parser / exemplar / mock_aggregator / drill_loop) 完全没改 signature
- Frontend：`/setup` 页 + localStorage + `lib/api.ts` 注 4 个 X-* header；401 自动跳回 /setup

详见 [`docs/superpowers/specs/`](superpowers/specs/) 设计文档。

## v1.1 BYOK self-check

v1.1 新增三个核心 feature（多组配置 / 连接测试 / 语音输入）+ 七个辅助配套
项后，BYOK 服务器零持有 key 的硬约束**仍完全成立**。证据：

### 1. 多组配置全部存在客户端 localStorage
- 所有保存的 `SavedConfig[]` 在浏览器 `localStorage["mockinterview.providerStore"]`
- 后端**没有**任何 user / config / api_key 表或字段
- 验证：`git grep -E "save.*api.*key|store.*api.*key|persist.*api.*key" backend/`
  应该 0 命中（没有 server-side key 持久化代码）
- 验证：`git grep -E "user_id|account_id|auth.*token" backend/src/mockinterview/db/`
  应仅命中 1 处：`db/models.py` 的 `user_id: int = Field(default=1, index=True)`
  ——v1.0 遗留的 stub field（单用户模式占位 + 未来扩展预留），**不存任何 key**，
  当前永远是 1

### 2. 连接测试 endpoint 不持有 key
- `POST /provider/test` 复用 `use_provider` Depends（[backend/src/mockinterview/routes/_deps.py](../backend/src/mockinterview/routes/_deps.py)）
- key 走 `X-API-Key` header 透传，请求结束 ContextVar 自动重置 → 内存中也不留
- 验证：`grep -A5 "use_provider" backend/src/mockinterview/routes/_deps.py`
  确认 key 仅作为 SDK client 构造参数，不写文件不入库

### 3. 语音 STT 在浏览器本地完成
- Web Speech API 是浏览器调系统/Google/Apple STT，**音频从不进 mockinterview 的后端**
- 验证：`grep -r "audio\|speech\|stt\|whisper" backend/src/mockinterview/routes/`
  应该 0 命中（后端没有 audio endpoint）
- 验证：`grep -r "FormData.*audio\|MediaRecorder" frontend/src/lib/api.ts`
  应该 0 命中（前端 API client 不传输 audio 数据）

### 4. 配置导出文件为客户端动作
- `导出 JSON` 在前端用 `URL.createObjectURL(Blob)` 触发浏览器下载
- 文件**不经过任何 mockinterview 服务器**——即使你导出 100MB key 列表，
  bandwidth 在你和你浏览器之间发生
- 文件含明文 key，是你本地的责任（导出对话框已警告）

### v1.1 没有破坏的不变量

- ✅ 服务器零持有 key（v1.0 + v1.1 同样成立）
- ✅ 服务器零运营成本（v1.0 + v1.1 同样成立——加 `/provider/test` 也不消耗
  开发者的额度，因为它仍是用用户自己的 key 调用）
- ✅ 用户成本完全透明（同 v1.0）
- ✅ 用户可选最便宜 provider（v1.1 多组保存让这条更称手——一键切换比不同
  价位 provider）

### v1.1 引入的新 trade-off

- ⚠️ **localStorage 易失性**：v1.0 已是 localStorage，v1.1 没有恶化但**多组
  保存让损失更显著**（v1.0 丢一组 vs v1.1 可能丢 N 组）。Mitigation: setup
  页 banner + 导入/导出 JSON
- ⚠️ **导出文件含明文 key**：v1.0 没这个 surface，v1.1 导出对话框已警告
  「文件含明文 API key，请妥善保管，不要上传到任何公开平台」
