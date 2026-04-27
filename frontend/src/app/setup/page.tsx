"use client";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ProviderSelector } from "@/components/provider-selector";
import {
  findPreset,
  getProviderConfig,
  setProviderConfig,
  type ProviderKind,
} from "@/lib/provider-config";

function SetupView() {
  const router = useRouter();
  const sp = useSearchParams();
  const next = sp.get("next") ?? "/";
  const [provider, setProvider] = useState<ProviderKind>("anthropic");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("claude-opus-4-7");
  const [baseUrl, setBaseUrl] = useState("");

  useEffect(() => {
    const existing = getProviderConfig();
    if (existing) {
      setProvider(existing.provider);
      setApiKey(existing.apiKey);
      setModel(existing.model);
      setBaseUrl(existing.baseUrl);
    }
  }, []);

  function onProviderChange(v: ProviderKind) {
    setProvider(v);
    const preset = findPreset(v);
    setModel(preset.defaultModel);
    setBaseUrl(preset.defaultBaseUrl);
  }

  function save() {
    if (!apiKey.trim()) return;
    setProviderConfig({
      provider,
      apiKey: apiKey.trim(),
      model: model.trim(),
      baseUrl: baseUrl.trim(),
    });
    router.push(next);
  }

  const preset = findPreset(provider);

  return (
    <main className="container max-w-3xl mx-auto py-12 space-y-8">
      <div>
        <h1 className="text-3xl font-bold">配置你的 LLM API key</h1>
        <p className="mt-2 text-muted-foreground">
          MockInterview Agent 自带 BYOK（Bring Your Own Key）：每次调用都用你自己的 API。
          key 只存在你的浏览器（localStorage），不会上传到服务器（仅作为 header 透传给后端调用 LLM）。
        </p>
      </div>

      <Card>
        <CardHeader>
          <h2 className="font-semibold">1. 选 Provider</h2>
        </CardHeader>
        <CardContent className="space-y-3">
          <ProviderSelector value={provider} onChange={onProviderChange} />
          {preset.notes && (
            <p className="text-xs text-muted-foreground">{preset.notes}</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="font-semibold">2. 粘贴 API Key</h2>
        </CardHeader>
        <CardContent className="space-y-3">
          <Input
            type="password"
            placeholder={preset.keyHint}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
          {preset.acquireUrl && (
            <p className="text-xs">
              <a
                href={preset.acquireUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary underline"
              >
                获取 / 管理 {preset.label} API Key →
              </a>
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="font-semibold">3. 模型 + Base URL（可选覆盖默认）</h2>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <Label htmlFor="model">Model</Label>
            <Input
              id="model"
              placeholder={preset.defaultModel}
              value={model}
              onChange={(e) => setModel(e.target.value)}
            />
          </div>
          {(preset.needsBaseUrl || preset.defaultBaseUrl) && (
            <div>
              <Label htmlFor="baseUrl">Base URL</Label>
              <Input
                id="baseUrl"
                placeholder={preset.defaultBaseUrl || "https://your-endpoint/v1"}
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
              />
              <p className="text-xs text-muted-foreground mt-1">
                空 = 用 {preset.label} 默认 endpoint
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <Button size="lg" onClick={save} disabled={!apiKey.trim()}>
        保存并继续
      </Button>
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
