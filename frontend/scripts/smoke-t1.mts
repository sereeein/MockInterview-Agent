// Smoke test for T1: provider-config store migration + CRUD.
// Run: node --experimental-strip-types --no-warnings scripts/smoke-t1.mts
import { strict as assert } from "node:assert";

// --- mock window.localStorage in Node ---
const store = new Map<string, string>();
(globalThis as unknown as { window: unknown }).window = {
  localStorage: {
    getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
    setItem: (k: string, v: string) => store.set(k, String(v)),
    removeItem: (k: string) => store.delete(k),
  },
};

// Now import the module fresh
const mod = await import("../src/lib/provider-config.ts");

// ---- TEST 1: empty store on first run ----
{
  store.clear();
  const s = mod.getStore();
  assert.equal(s.configs.length, 0, "empty store should have 0 configs");
  assert.equal(s.activeId, null);
  assert.equal(s.defaultId, null);
  console.log("PASS  TEST 1: empty store");
}

// ---- TEST 2: legacy v1.0 single config migrates ----
{
  store.clear();
  store.set(
    "mockinterview.providerConfig",
    JSON.stringify({
      provider: "anthropic",
      apiKey: "sk-ant-legacy",
      model: "claude-opus-4-7",
      baseUrl: "",
    })
  );
  const s = mod.getStore();
  assert.equal(s.configs.length, 1);
  assert.equal(s.configs[0].apiKey, "sk-ant-legacy");
  assert.equal(s.configs[0].name, "默认配置");
  assert.equal(s.activeId, s.configs[0].id);
  assert.equal(s.defaultId, s.configs[0].id);
  assert.ok(store.get("mockinterview.providerConfig"), "legacy key kept for rollback");
  assert.ok(store.get("mockinterview.providerStore"), "new store key persisted");
  console.log("PASS  TEST 2: v1.0 legacy migration");
}

// ---- TEST 3: addConfig + setActive + setDefault ----
{
  store.clear();
  const a = mod.addConfig({
    name: "Claude Opus",
    provider: "anthropic",
    apiKey: "k1",
    model: "claude-opus-4-7",
    baseUrl: "",
  });
  const b = mod.addConfig({
    name: "DeepSeek",
    provider: "deepseek",
    apiKey: "k2",
    model: "deepseek-chat",
    baseUrl: "https://api.deepseek.com/v1",
  });
  let s = mod.getStore();
  assert.equal(s.configs.length, 2);
  assert.equal(s.activeId, a.id, "first added becomes active");
  assert.equal(s.defaultId, a.id, "first added becomes default");

  mod.setActive(b.id);
  s = mod.getStore();
  assert.equal(s.activeId, b.id);

  mod.setDefault(b.id);
  s = mod.getStore();
  assert.equal(s.defaultId, b.id);
  console.log("PASS  TEST 3: addConfig + setActive + setDefault");
}

// ---- TEST 4: updateConfig auto-resets test status when credential field changes ----
{
  store.clear();
  const a = mod.addConfig({
    name: "test-cfg",
    provider: "anthropic",
    apiKey: "k1",
    model: "claude-opus-4-7",
    baseUrl: "",
  });
  mod.recordTestResult(a.id, "ok");
  let cfg = mod.getActiveConfig();
  assert.equal(cfg!.lastTestStatus, "ok");

  // updating only the name should NOT reset
  mod.updateConfig(a.id, { name: "renamed" });
  cfg = mod.getActiveConfig();
  assert.equal(cfg!.name, "renamed");
  assert.equal(cfg!.lastTestStatus, "ok", "name change should not reset test status");

  // updating apiKey SHOULD reset
  mod.updateConfig(a.id, { apiKey: "k1-new" });
  cfg = mod.getActiveConfig();
  assert.equal(cfg!.lastTestStatus, null, "apiKey change should reset test status");
  console.log("PASS  TEST 4: updateConfig resets test status only on credential fields");
}

// ---- TEST 5: deleteConfig fallback to defaultId ----
{
  store.clear();
  const a = mod.addConfig({ name: "A", provider: "anthropic", apiKey: "k1", model: "m1", baseUrl: "" });
  const b = mod.addConfig({ name: "B", provider: "deepseek", apiKey: "k2", model: "m2", baseUrl: "u2" });
  const c = mod.addConfig({ name: "C", provider: "openai", apiKey: "k3", model: "m3", baseUrl: "" });
  mod.setActive(c.id);
  mod.setDefault(b.id);

  mod.deleteConfig(c.id);
  let s = mod.getStore();
  assert.equal(s.configs.length, 2);
  assert.equal(s.activeId, b.id, "delete active should fallback to defaultId");

  mod.deleteConfig(b.id);
  s = mod.getStore();
  assert.equal(s.configs.length, 1);
  assert.equal(s.activeId, a.id, "delete active again should fallback to first remaining");
  assert.equal(s.defaultId, a.id, "deleting default should reset to first remaining");

  mod.deleteConfig(a.id);
  s = mod.getStore();
  assert.equal(s.configs.length, 0);
  assert.equal(s.activeId, null);
  assert.equal(s.defaultId, null);
  console.log("PASS  TEST 5: deleteConfig fallback chain");
}

// ---- TEST 6: v1.0 shim getProviderConfig returns active fields ----
{
  store.clear();
  mod.addConfig({
    name: "shim-test",
    provider: "kimi",
    apiKey: "kshim",
    model: "moonshot-v1-32k",
    baseUrl: "https://api.moonshot.cn/v1",
  });
  const legacyShape = mod.getProviderConfig();
  assert.equal(legacyShape!.provider, "kimi");
  assert.equal(legacyShape!.apiKey, "kshim");
  assert.equal(legacyShape!.model, "moonshot-v1-32k");
  console.log("PASS  TEST 6: v1.0 shim getProviderConfig");
}

// ---- TEST 7: ui-prefs default + patch ----
{
  store.clear();
  const ui = await import("../src/lib/ui-prefs.ts");
  assert.equal(ui.getUiPrefs().speechLang, "zh-CN", "default speechLang");
  ui.patchUiPrefs({ speechLang: "en-US" });
  assert.equal(ui.getUiPrefs().speechLang, "en-US", "patch persists");
  console.log("PASS  TEST 7: ui-prefs default + patch");
}

console.log("\nT1 SMOKE: 7/7 passed");
