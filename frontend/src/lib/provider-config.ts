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

export function findPreset(key: ProviderKind): ProviderPreset {
  return PROVIDER_PRESETS.find((p) => p.key === key) ?? PROVIDER_PRESETS[0];
}

// ---------- v1.1: multi-config store ----------

export type TestStatus = "ok" | "fail" | null;

export interface SavedConfig {
  id: string;
  name: string;
  provider: ProviderKind;
  apiKey: string;
  model: string;
  baseUrl: string;
  createdAt: number;
  lastTestedAt: number | null;
  lastTestStatus: TestStatus;
}

export interface ProviderConfigStore {
  configs: SavedConfig[];
  activeId: string | null;
  defaultId: string | null;
}

// v1.0 single-config shape (kept for migration only)
export interface ProviderConfig {
  provider: ProviderKind;
  apiKey: string;
  model: string;
  baseUrl: string;
}

const LEGACY_STORAGE_KEY = "mockinterview.providerConfig";
const STORE_STORAGE_KEY = "mockinterview.providerStore";

function genId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // Fallback for very old environments — prefix + random + timestamp
  return `cfg_${Math.random().toString(36).slice(2, 10)}_${Date.now()}`;
}

function emptyStore(): ProviderConfigStore {
  return { configs: [], activeId: null, defaultId: null };
}

function readLegacyConfig(): ProviderConfig | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(LEGACY_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ProviderConfig;
    if (!parsed?.provider || !parsed?.apiKey) return null;
    return parsed;
  } catch {
    return null;
  }
}

function migrateFromLegacy(legacy: ProviderConfig): ProviderConfigStore {
  const id = genId();
  const cfg: SavedConfig = {
    id,
    name: "默认配置",
    provider: legacy.provider,
    apiKey: legacy.apiKey,
    model: legacy.model,
    baseUrl: legacy.baseUrl,
    createdAt: Date.now(),
    lastTestedAt: null,
    lastTestStatus: null,
  };
  return { configs: [cfg], activeId: id, defaultId: id };
}

export function getStore(): ProviderConfigStore {
  if (typeof window === "undefined") return emptyStore();
  try {
    const raw = window.localStorage.getItem(STORE_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as ProviderConfigStore;
      if (parsed && Array.isArray(parsed.configs)) {
        return parsed;
      }
    }
  } catch {
    // fall through to migration
  }
  // No new store yet — try migrating from v1.0 legacy single config
  const legacy = readLegacyConfig();
  if (legacy) {
    const migrated = migrateFromLegacy(legacy);
    setStore(migrated);
    // Keep legacy key as 90-day rollback safety; do NOT delete here.
    return migrated;
  }
  return emptyStore();
}

export function setStore(store: ProviderConfigStore): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORE_STORAGE_KEY, JSON.stringify(store));
}

export function addConfig(input: Omit<SavedConfig, "id" | "createdAt" | "lastTestedAt" | "lastTestStatus">): SavedConfig {
  const store = getStore();
  const cfg: SavedConfig = {
    ...input,
    id: genId(),
    createdAt: Date.now(),
    lastTestedAt: null,
    lastTestStatus: null,
  };
  const next: ProviderConfigStore = {
    configs: [...store.configs, cfg],
    activeId: store.activeId ?? cfg.id,
    defaultId: store.defaultId ?? cfg.id,
  };
  setStore(next);
  return cfg;
}

export function updateConfig(id: string, patch: Partial<Omit<SavedConfig, "id" | "createdAt">>): SavedConfig | null {
  const store = getStore();
  const idx = store.configs.findIndex((c) => c.id === id);
  if (idx < 0) return null;
  const prev = store.configs[idx];
  // If any provider/model/baseUrl/apiKey field changed, reset test status
  const fieldsTouched =
    (patch.provider !== undefined && patch.provider !== prev.provider) ||
    (patch.apiKey !== undefined && patch.apiKey !== prev.apiKey) ||
    (patch.model !== undefined && patch.model !== prev.model) ||
    (patch.baseUrl !== undefined && patch.baseUrl !== prev.baseUrl);
  const updated: SavedConfig = {
    ...prev,
    ...patch,
    ...(fieldsTouched ? { lastTestedAt: null, lastTestStatus: null } : {}),
  };
  const configs = [...store.configs];
  configs[idx] = updated;
  setStore({ ...store, configs });
  return updated;
}

export function deleteConfig(id: string): ProviderConfigStore {
  const store = getStore();
  const remaining = store.configs.filter((c) => c.id !== id);
  let activeId = store.activeId;
  let defaultId = store.defaultId;
  if (activeId === id) {
    // Prefer falling back to defaultId, then first remaining, then null
    if (defaultId && defaultId !== id && remaining.some((c) => c.id === defaultId)) {
      activeId = defaultId;
    } else {
      activeId = remaining[0]?.id ?? null;
    }
  }
  if (defaultId === id) {
    defaultId = remaining[0]?.id ?? null;
  }
  const next: ProviderConfigStore = { configs: remaining, activeId, defaultId };
  setStore(next);
  return next;
}

export function setActive(id: string): void {
  const store = getStore();
  if (!store.configs.some((c) => c.id === id)) return;
  setStore({ ...store, activeId: id });
}

export function setDefault(id: string): void {
  const store = getStore();
  if (!store.configs.some((c) => c.id === id)) return;
  setStore({ ...store, defaultId: id });
}

export function recordTestResult(id: string, status: "ok" | "fail"): void {
  const store = getStore();
  const idx = store.configs.findIndex((c) => c.id === id);
  if (idx < 0) return;
  const configs = [...store.configs];
  configs[idx] = {
    ...configs[idx],
    lastTestedAt: Date.now(),
    lastTestStatus: status,
  };
  setStore({ ...store, configs });
}

export function getActiveConfig(): SavedConfig | null {
  const store = getStore();
  if (!store.activeId) return null;
  return store.configs.find((c) => c.id === store.activeId) ?? null;
}

// ---------- v1.0 compatibility shims (deprecated, still functional) ----------

/** @deprecated v1.0 shim — use getActiveConfig() instead. */
export function getProviderConfig(): ProviderConfig | null {
  const active = getActiveConfig();
  if (!active) return null;
  return {
    provider: active.provider,
    apiKey: active.apiKey,
    model: active.model,
    baseUrl: active.baseUrl,
  };
}

/** @deprecated v1.0 shim — replaces the active config (or creates one if store empty). */
export function setProviderConfig(config: ProviderConfig): void {
  const store = getStore();
  if (store.activeId) {
    updateConfig(store.activeId, {
      provider: config.provider,
      apiKey: config.apiKey,
      model: config.model,
      baseUrl: config.baseUrl,
    });
    return;
  }
  addConfig({
    name: "默认配置",
    provider: config.provider,
    apiKey: config.apiKey,
    model: config.model,
    baseUrl: config.baseUrl,
  });
}

/** @deprecated v1.0 shim — clears the entire multi-config store. */
export function clearProviderConfig(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORE_STORAGE_KEY);
  // Intentionally keep LEGACY_STORAGE_KEY as a 90-day rollback safety net.
}
