export type ProviderKind =
  | "anthropic"
  | "openai"
  | "deepseek"
  | "qwen"
  | "zhipu"
  | "kimi"
  | "wenxin"
  | "doubao"
  | "gemini"
  | "custom";

export interface ProviderPreset {
  key: ProviderKind;
  label: string;
  defaultModel: string;
  defaultBaseUrl: string;
  needsBaseUrl: boolean;
  keyHint: string;
  acquireUrl?: string;
  notes?: string;
}

export const PROVIDER_PRESETS: ProviderPreset[] = [
  {
    key: "anthropic",
    label: "Anthropic Claude（推荐，prompt 调优最佳）",
    defaultModel: "claude-opus-4-7",
    defaultBaseUrl: "",
    needsBaseUrl: false,
    keyHint: "sk-ant-...",
    acquireUrl: "https://console.anthropic.com/settings/keys",
    notes: "本项目 prompt 在 Claude 上调优，默认推荐。",
  },
  {
    key: "openai",
    label: "OpenAI",
    defaultModel: "gpt-4-turbo",
    defaultBaseUrl: "",
    needsBaseUrl: false,
    keyHint: "sk-...",
    acquireUrl: "https://platform.openai.com/api-keys",
  },
  {
    key: "deepseek",
    label: "DeepSeek",
    defaultModel: "deepseek-chat",
    defaultBaseUrl: "https://api.deepseek.com/v1",
    needsBaseUrl: false,
    keyHint: "sk-...",
    acquireUrl: "https://platform.deepseek.com/api_keys",
  },
  {
    key: "qwen",
    label: "通义千问 (DashScope)",
    defaultModel: "qwen-max",
    defaultBaseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    needsBaseUrl: false,
    keyHint: "sk-...",
    acquireUrl: "https://bailian.console.aliyun.com/?apiKey=1",
  },
  {
    key: "zhipu",
    label: "智谱 GLM",
    defaultModel: "glm-4-plus",
    defaultBaseUrl: "https://open.bigmodel.cn/api/paas/v4",
    needsBaseUrl: false,
    keyHint: "...",
    acquireUrl: "https://bigmodel.cn/usercenter/proj-mgmt/apikeys",
  },
  {
    key: "kimi",
    label: "Kimi (Moonshot)",
    defaultModel: "moonshot-v1-32k",
    defaultBaseUrl: "https://api.moonshot.cn/v1",
    needsBaseUrl: false,
    keyHint: "sk-...",
    acquireUrl: "https://platform.moonshot.cn/console/api-keys",
  },
  {
    key: "wenxin",
    label: "文心一言（千帆）",
    defaultModel: "ernie-4.0-turbo-8k",
    defaultBaseUrl: "https://qianfan.baidubce.com/v2",
    needsBaseUrl: false,
    keyHint: "...",
    acquireUrl: "https://console.bce.baidu.com/iam/#/iam/apikey/list",
  },
  {
    key: "doubao",
    label: "豆包（火山方舟）",
    defaultModel: "doubao-pro-32k",
    defaultBaseUrl: "https://ark.cn-beijing.volces.com/api/v3",
    needsBaseUrl: false,
    keyHint: "...",
    acquireUrl: "https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey",
  },
  {
    key: "gemini",
    label: "Google Gemini",
    defaultModel: "gemini-2.0-flash-exp",
    defaultBaseUrl: "",
    needsBaseUrl: false,
    keyHint: "...",
    acquireUrl: "https://aistudio.google.com/app/apikey",
  },
  {
    key: "custom",
    label: "自定义（OpenAI-compatible）",
    defaultModel: "",
    defaultBaseUrl: "",
    needsBaseUrl: true,
    keyHint: "...",
    notes: "粘贴任何兼容 OpenAI Chat Completions API 的服务的 base URL + key + model。",
  },
];

export interface ProviderConfig {
  provider: ProviderKind;
  apiKey: string;
  model: string;
  baseUrl: string;
}

const STORAGE_KEY = "mockinterview.providerConfig";

export function getProviderConfig(): ProviderConfig | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ProviderConfig;
    if (!parsed.provider || !parsed.apiKey) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function setProviderConfig(config: ProviderConfig): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
}

export function clearProviderConfig(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}

export function findPreset(key: ProviderKind): ProviderPreset {
  return PROVIDER_PRESETS.find((p) => p.key === key) ?? PROVIDER_PRESETS[0];
}
