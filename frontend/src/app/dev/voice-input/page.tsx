"use client";
// Dev-only showcase for v1.1 T5 VoiceInput.
// Bypasses the full resume→drill flow so you can test the mic button directly.
// Safe to delete after v1.1 ships.
import { useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { VoiceInput } from "@/components/voice-input";
import { detectSpeechSupport } from "@/lib/speech";
import { getUiPrefs } from "@/lib/ui-prefs";

export default function VoiceInputShowcase() {
  const [input, setInput] = useState("");
  const [supportInfo, setSupportInfo] = useState<string | null>(null);
  const [lang, setLang] = useState<string | null>(null);

  function refreshDiagnostics() {
    const support = detectSpeechSupport();
    setSupportInfo(
      support.supported
        ? "✓ 浏览器支持 SpeechRecognition"
        : `✗ 不支持：${support.reason}`,
    );
    setLang(getUiPrefs().speechLang);
  }

  return (
    <main className="container max-w-2xl mx-auto py-12 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">v1.1 T5 dev showcase — 语音输入</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          直接测试 VoiceInput 组件，不需走完整 resume→drill 流程。
          T6 收尾时可删除此页。
        </p>
      </div>

      <section className="space-y-2">
        <h2 className="font-semibold">1. 浏览器能力 + 当前语言</h2>
        <button
          onClick={refreshDiagnostics}
          className="text-sm text-primary underline"
        >
          检测当前浏览器支持情况
        </button>
        {supportInfo && (
          <div className="text-sm space-y-1 rounded border p-3 bg-muted/30">
            <div>{supportInfo}</div>
            <div>当前 speechLang: {lang}（在 /setup 底部修改）</div>
          </div>
        )}
      </section>

      <section className="space-y-2">
        <h2 className="font-semibold">2. 试一试</h2>
        <p className="text-sm text-muted-foreground">
          点右下角 🎙 → 允许麦克风权限 → 说一段话 → 看 textarea 文字实时出现 → 再次点击停止。
        </p>
        <div className="relative">
          <Textarea
            rows={6}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="用键盘打字 或 点右下角 🎙 语音输入"
            className="pr-12"
          />
          <div className="absolute right-2 bottom-2">
            <VoiceInput value={input} onChange={setInput} />
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          字符数：{input.length}
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="font-semibold">3. 预期行为清单</h2>
        <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
          <li>支持的浏览器（Chrome/Edge/Safari）：🎙 按钮渲染</li>
          <li>不支持的浏览器（Firefox、HTTP 非 HTTPS）：按钮**完全不渲染**</li>
          <li>Idle：灰色 🎙 图标</li>
          <li>Recording：红色 ◼ 图标 + 脉冲动画 + tooltip「再次点击停止」</li>
          <li>新 final 段：直接拼到 textarea 末尾</li>
          <li>interim 段：临时拼到末尾，下次更新时被新 interim/final 替换</li>
          <li>停止后：interim 残留被自动剥离</li>
          <li>permission denied：按钮上方红色 tooltip 3 秒淡出</li>
          <li>network 错（如国内 Chrome 调 Google STT 不可达）：同样红色提示</li>
        </ul>
      </section>
    </main>
  );
}
