"use client";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowRight,
  Download,
  Plus,
  Star,
  Trash2,
  Upload,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ProviderSelector } from "@/components/provider-selector";
import { SecretInput } from "@/components/secret-input";
import {
  ConnectionTestDialog,
  type ConnectionTestState,
} from "@/components/connection-test-dialog";
import {
  addConfig,
  deleteConfig,
  findPreset,
  getStore,
  importConfigs,
  PROVIDER_PRESETS,
  recordTestResult,
  setActive,
  setDefault,
  updateConfig,
  type ProviderConfigStore,
  type ProviderKind,
  type SavedConfig,
} from "@/lib/provider-config";
import { getUiPrefs, patchUiPrefs, type SpeechLang } from "@/lib/ui-prefs";
import { testProvider, type ProviderTestResult } from "@/lib/api";
import { cn } from "@/lib/utils";

type EditorDraft = {
  /** null = creating new; string = editing existing config id */
  id: string | null;
  name: string;
  provider: ProviderKind;
  apiKey: string;
  model: string;
  baseUrl: string;
};

const SPEECH_LANG_OPTIONS: { value: SpeechLang; label: string }[] = [
  { value: "zh-CN", label: "中文（普通话, zh-CN）" },
  { value: "zh-TW", label: "中文（台湾, zh-TW）" },
  { value: "en-US", label: "English（en-US）" },
];

function emptyDraft(): EditorDraft {
  const preset = PROVIDER_PRESETS[0];
  return {
    id: null,
    name: "",
    provider: preset.key,
    apiKey: "",
    model: preset.defaultModel,
    baseUrl: preset.defaultBaseUrl,
  };
}

function toast(msg: string) {
  // v1.1 lightweight toast: no library, just window-level alert for now.
  // The whole banner+save flow is interactive enough that a quick alert is fine.
  if (typeof window !== "undefined") {
    // Use a very short queueMicrotask + console for non-blocking feel
    console.info("[mockinterview]", msg);
    // Inline soft toast: append to body, fade out
    const el = document.createElement("div");
    el.textContent = msg;
    el.className =
      "fixed bottom-6 left-1/2 -translate-x-1/2 z-[100] rounded-md bg-foreground text-background px-4 py-2 text-sm shadow-lg transition-opacity duration-300";
    document.body.appendChild(el);
    setTimeout(() => {
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 300);
    }, 1800);
  }
}

function SetupView() {
  const router = useRouter();
  const sp = useSearchParams();
  const next = sp.get("next") ?? "/";

  const [store, setStoreState] = useState<ProviderConfigStore>({
    configs: [],
    activeId: null,
    defaultId: null,
  });
  const [editor, setEditor] = useState<EditorDraft | null>(null);
  const [speechLang, setSpeechLang] = useState<SpeechLang>("zh-CN");

  const [testOpen, setTestOpen] = useState(false);
  const [testState, setTestState] = useState<ConnectionTestState | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Refresh local mirror of localStorage store
  function refresh() {
    setStoreState(getStore());
  }

  useEffect(() => {
    refresh();
    setSpeechLang(getUiPrefs().speechLang);
  }, []);

  // ---------- editor open / close / save ----------

  function openNew() {
    setEditor(emptyDraft());
  }

  function openEdit(cfg: SavedConfig) {
    setEditor({
      id: cfg.id,
      name: cfg.name,
      provider: cfg.provider,
      apiKey: cfg.apiKey,
      model: cfg.model,
      baseUrl: cfg.baseUrl,
    });
  }

  function changeProvider(v: ProviderKind) {
    if (!editor) return;
    const preset = findPreset(v);
    setEditor({
      ...editor,
      provider: v,
      model: preset.defaultModel || editor.model,
      baseUrl: preset.defaultBaseUrl || "",
    });
  }

  /** Persist current draft. Returns the id of the saved config (new or existing).
   *  null on validation failure (also alerts). */
  function persistDraft(): string | null {
    if (!editor) return null;
    if (!editor.name.trim()) {
      toast("请填写配置名称");
      return null;
    }
    if (!editor.apiKey.trim()) {
      toast("请粘贴 API Key");
      return null;
    }
    const payload = {
      name: editor.name.trim(),
      provider: editor.provider,
      apiKey: editor.apiKey.trim(),
      model: editor.model.trim(),
      baseUrl: editor.baseUrl.trim(),
    };
    let id: string;
    if (editor.id) {
      const updated = updateConfig(editor.id, payload);
      if (!updated) {
        toast("更新失败：配置已不存在");
        refresh();
        return null;
      }
      id = updated.id;
    } else {
      const created = addConfig(payload);
      id = created.id;
    }
    refresh();
    return id;
  }

  function onSave() {
    const id = persistDraft();
    if (!id) return;
    toast("已保存");
    setEditor(null);
  }

  async function runTest(cfg: {
    id: string;
    name: string;
    provider: ProviderKind;
    apiKey: string;
    model: string;
    baseUrl: string;
  }) {
    const preset = findPreset(cfg.provider);
    setTestState({
      phase: "testing",
      providerLabel: preset.label,
      model: cfg.model || preset.defaultModel,
      startedAt: Date.now(),
    });
    setTestOpen(true);
    let result: ProviderTestResult;
    try {
      result = await testProvider({
        provider: cfg.provider,
        apiKey: cfg.apiKey,
        model: cfg.model,
        baseUrl: cfg.baseUrl,
      });
    } catch (e) {
      result = {
        ok: false,
        category: "unknown",
        http_status: null,
        provider_message: e instanceof Error ? e.message : String(e),
        raw_response: null,
        elapsed_ms: 0,
      };
    }
    setTestState({ phase: "result", result });
    recordTestResult(cfg.id, result.ok ? "ok" : "fail");
    refresh();
  }

  async function onSaveAndTest() {
    const id = persistDraft();
    if (!id) return;
    const saved = getStore().configs.find((c) => c.id === id);
    if (!saved) return;
    await runTest(saved);
    // Don't close editor — user may want to fix and re-test
  }

  // ---------- card actions ----------

  function onUseCard(cfg: SavedConfig) {
    if (cfg.lastTestStatus === "fail") {
      const ok = window.confirm(
        `「${cfg.name}」上次连接测试失败。仍要切换到这组配置吗？`,
      );
      if (!ok) return;
    }
    setActive(cfg.id);
    refresh();
    toast(`已切换到 ${cfg.name}`);
  }

  function onSetDefaultCard(cfg: SavedConfig) {
    setDefault(cfg.id);
    refresh();
    toast(`「${cfg.name}」已设为默认`);
  }

  function onDeleteCard(cfg: SavedConfig) {
    const ok = window.confirm(`确定删除「${cfg.name}」？此操作不可撤销。`);
    if (!ok) return;
    const after = deleteConfig(cfg.id);
    refresh();
    if (after.configs.length === 0) {
      toast("已删除全部配置，跳回引导");
      router.push(`/setup?next=${encodeURIComponent(next)}`);
      return;
    }
    if (editor?.id === cfg.id) setEditor(null);
  }

  // ---------- export / import ----------

  function onExport() {
    const ok = window.confirm(
      "导出文件含明文 API key，请妥善保管，不要上传到公开平台。继续？",
    );
    if (!ok) return;
    const payload = {
      version: "v1.1",
      configs: store.configs,
      exportedAt: Date.now(),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const date = new Date().toISOString().slice(0, 10);
    a.download = `mockinterview-configs-${date}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast(`已导出 ${store.configs.length} 组配置`);
  }

  function onImportClick() {
    fileInputRef.current?.click();
  }

  async function onImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // reset so picking same file again triggers change
    if (!file) return;
    try {
      const text = await file.text();
      const parsed = JSON.parse(text) as {
        version?: string;
        configs?: SavedConfig[];
      };
      if (!parsed.version || !parsed.version.startsWith("v1.")) {
        toast(`无法识别的版本：${parsed.version ?? "(无)"}`);
        return;
      }
      if (!Array.isArray(parsed.configs)) {
        toast("文件格式错误：缺少 configs 字段");
        return;
      }
      const { added, updated } = importConfigs(parsed.configs);
      refresh();
      toast(`导入完成：新增 ${added}，覆盖 ${updated}`);
    } catch (err) {
      toast(`导入失败：${err instanceof Error ? err.message : "未知错误"}`);
    }
  }

  // ---------- speech lang ----------

  function changeSpeechLang(lang: SpeechLang) {
    patchUiPrefs({ speechLang: lang });
    setSpeechLang(lang);
  }

  const editorPreset = useMemo(
    () => (editor ? findPreset(editor.provider) : null),
    [editor],
  );

  return (
    <main className="container max-w-6xl mx-auto py-8 space-y-6">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Provider 配置</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            BYOK：所有 API key 仅存在你的浏览器（localStorage），不会上传到服务器。
            每次请求作为 X-API-Key header 透传给后端调用 LLM。
          </p>
        </div>
        {store.configs.length > 0 && store.activeId && (
          <Link
            href={next}
            className="shrink-0 inline-flex items-center gap-1 rounded-md border bg-primary text-primary-foreground px-3 py-2 text-sm font-medium hover:opacity-90 transition-opacity"
          >
            {next === "/" ? "去上传简历" : `去 ${next}`}
            <ArrowRight className="size-4" />
          </Link>
        )}
      </header>

      <div className="rounded-md border border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950/40 px-4 py-3 flex items-start gap-2">
        <AlertTriangle className="size-4 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
        <p className="text-sm text-amber-900 dark:text-amber-100">
          配置仅存于此浏览器。换浏览器或清缓存会全部丢失，建议下方「导出全部 JSON」备份。
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
        {/* ---------- LEFT: saved config list ---------- */}
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">已保存配置 ({store.configs.length})</h2>
            <Button size="sm" onClick={openNew}>
              <Plus />
              新建
            </Button>
          </div>

          {store.configs.length === 0 && (
            <Card>
              <CardContent className="py-8 text-center text-sm text-muted-foreground">
                还没有保存配置。点上方「新建」开始。
              </CardContent>
            </Card>
          )}

          <div className="space-y-2">
            {store.configs.map((cfg) => {
              const isActive = cfg.id === store.activeId;
              const isDefault = cfg.id === store.defaultId;
              const preset = findPreset(cfg.provider);
              const dotColor =
                cfg.lastTestStatus === "ok"
                  ? "bg-emerald-500"
                  : cfg.lastTestStatus === "fail"
                    ? "bg-destructive"
                    : "bg-muted-foreground/40";
              const isEditing = editor?.id === cfg.id;
              return (
                <Card
                  key={cfg.id}
                  onClick={() => {
                    // Click anywhere on the card body → switch active + open in editor.
                    // Inline icon buttons stopPropagation so they fire their own action only.
                    if (!isActive) onUseCard(cfg);
                    openEdit(cfg);
                  }}
                  className={cn(
                    "border transition-colors cursor-pointer hover:bg-muted/30",
                    isActive && "ring-2 ring-primary",
                    isEditing && !isActive && "ring-2 ring-primary/40",
                  )}
                >
                  <CardHeader className="flex flex-row items-start justify-between gap-2 space-y-0">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className={cn("size-2 rounded-full shrink-0", dotColor)} />
                        <span className="font-medium truncate">{cfg.name}</span>
                        {isDefault && (
                          <Star className="size-3.5 text-amber-500 fill-amber-500 shrink-0" />
                        )}
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground truncate">
                        {preset.label.split("（")[0]} · {cfg.model || "(默认)"}
                      </div>
                    </div>
                    {isActive && (
                      <span className="shrink-0 rounded bg-primary text-primary-foreground text-[10px] px-1.5 py-0.5 font-medium">
                        使用中
                      </span>
                    )}
                  </CardHeader>
                  <CardContent className="flex flex-wrap gap-1 pt-0">
                    {!isDefault && (
                      <Button
                        size="xs"
                        variant="outline"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSetDefaultCard(cfg);
                        }}
                        aria-label="设为默认"
                      >
                        <Star />
                        默认
                      </Button>
                    )}
                    <Button
                      size="xs"
                      variant="outline"
                      onClick={(e) => {
                        e.stopPropagation();
                        runTest(cfg);
                      }}
                      aria-label="测试连接"
                    >
                      <Zap />
                      测试
                    </Button>
                    <Button
                      size="xs"
                      variant="ghost"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteCard(cfg);
                      }}
                      aria-label="删除"
                      className="text-destructive hover:bg-destructive/10 ml-auto"
                    >
                      <Trash2 />
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </section>

        {/* ---------- RIGHT: editor ---------- */}
        <section>
          {!editor ? (
            <Card>
              <CardContent className="py-12 text-center text-sm text-muted-foreground space-y-3">
                <p>
                  {store.configs.length === 0
                    ? "👈 点左侧「新建」创建第一组配置"
                    : "👈 点左侧任一卡片可同时切换并编辑，或「新建」一组"}
                </p>
                {store.configs.length > 0 && store.activeId && (
                  <Link
                    href={next}
                    className="inline-flex items-center gap-1 text-primary hover:underline"
                  >
                    或者直接 {next === "/" ? "去上传简历" : `前往 ${next}`}
                    <ArrowRight className="size-3.5" />
                  </Link>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <h2 className="font-semibold">
                  {editor.id ? "编辑配置" : "新建配置"}
                </h2>
              </CardHeader>
              <CardContent className="space-y-5">
                <div>
                  <Label htmlFor="name">配置名称</Label>
                  <Input
                    id="name"
                    placeholder="比如：Claude Opus 4.7、DeepSeek 便宜"
                    value={editor.name}
                    onChange={(e) =>
                      setEditor({ ...editor, name: e.target.value })
                    }
                    className="mt-1"
                  />
                </div>

                <div>
                  <Label className="block mb-1">Provider</Label>
                  <ProviderSelector
                    value={editor.provider}
                    onChange={changeProvider}
                  />
                  {editorPreset?.notes && (
                    <p className="mt-2 text-xs text-muted-foreground">
                      {editorPreset.notes}
                    </p>
                  )}
                </div>

                <div>
                  <Label htmlFor="apikey">API Key</Label>
                  <SecretInput
                    id="apikey"
                    value={editor.apiKey}
                    onChange={(v) => setEditor({ ...editor, apiKey: v })}
                    placeholder={editorPreset?.keyHint}
                  />
                  {editorPreset?.acquireUrl && (
                    <p className="mt-1 text-xs">
                      <a
                        href={editorPreset.acquireUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary underline"
                      >
                        获取 / 管理 {editorPreset.label.split("（")[0]} API Key →
                      </a>
                    </p>
                  )}
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label htmlFor="model">Model</Label>
                    <Input
                      id="model"
                      placeholder={editorPreset?.defaultModel}
                      value={editor.model}
                      onChange={(e) =>
                        setEditor({ ...editor, model: e.target.value })
                      }
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="baseurl">
                      Base URL
                      <span className="ml-1 text-xs font-normal text-muted-foreground">
                        （可选）
                      </span>
                    </Label>
                    <Input
                      id="baseurl"
                      placeholder={
                        editorPreset?.defaultBaseUrl || "https://your-endpoint/v1"
                      }
                      value={editor.baseUrl}
                      onChange={(e) =>
                        setEditor({ ...editor, baseUrl: e.target.value })
                      }
                      className="mt-1"
                    />
                  </div>
                </div>

                <div className="flex flex-wrap gap-2 pt-2">
                  <Button variant="outline" onClick={() => setEditor(null)}>
                    取消
                  </Button>
                  <div className="flex-1" />
                  <Button variant="outline" onClick={onSaveAndTest}>
                    <Zap />
                    保存并测试
                  </Button>
                  <Button onClick={onSave}>保存</Button>
                </div>

                <p className="text-xs text-muted-foreground">
                  保存后会自动设为「使用中」。配完后点页面右上角「
                  {next === "/" ? "去上传简历" : `去 ${next}`}」继续。
                </p>
              </CardContent>
            </Card>
          )}
        </section>
      </div>

      {/* ---------- BOTTOM: speech lang ---------- */}
      <Card>
        <CardHeader>
          <h2 className="font-semibold">语音输入语言</h2>
          <p className="text-xs text-muted-foreground">
            v1.1 单题演练 / 模拟面试 textarea 右下角的 🎙 按钮使用。
            此设置仅影响浏览器原生 Web Speech API 识别——音频不上传任何服务器。
          </p>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            {SPEECH_LANG_OPTIONS.map((opt) => (
              <label
                key={opt.value}
                className={cn(
                  "flex items-center gap-2 rounded border px-3 py-2 cursor-pointer text-sm transition-colors",
                  speechLang === opt.value
                    ? "border-primary bg-primary/10"
                    : "border-border hover:bg-muted",
                )}
              >
                <input
                  type="radio"
                  name="speechLang"
                  value={opt.value}
                  checked={speechLang === opt.value}
                  onChange={() => changeSpeechLang(opt.value)}
                  className="accent-primary"
                />
                {opt.label}
              </label>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* ---------- BOTTOM: import / export ---------- */}
      <Card>
        <CardHeader>
          <h2 className="font-semibold">导入 / 导出</h2>
          <p className="text-xs text-muted-foreground">
            备份配置以应对换浏览器、清缓存。导出文件含明文 API
            key，请妥善保管，不要上传到任何公开平台。
          </p>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={onExport}
            disabled={store.configs.length === 0}
          >
            <Download />
            导出全部 JSON
          </Button>
          <Button variant="outline" onClick={onImportClick}>
            <Upload />
            导入 JSON
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/json,.json"
            className="hidden"
            onChange={onImportFile}
          />
        </CardContent>
      </Card>

      <ConnectionTestDialog
        open={testOpen}
        onOpenChange={setTestOpen}
        state={testState}
      />
    </main>
  );
}

export default function SetupPage() {
  return (
    <Suspense fallback={<main className="container py-12">加载……</main>}>
      <SetupView />
    </Suspense>
  );
}
