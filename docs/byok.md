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
