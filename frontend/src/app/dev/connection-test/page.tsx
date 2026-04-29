"use client";
// Dev-only showcase page for v1.1 T3 ConnectionTestDialog.
// Shows all 6 dialog states (testing + 5 result categories) so the visual
// smoke test for T3 is reproducible without hitting a real backend.
// Safe to delete after v1.1 ships; not linked from anywhere in main app.
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { SecretInput } from "@/components/secret-input";
import {
  ConnectionTestDialog,
  type ConnectionTestState,
} from "@/components/connection-test-dialog";
import type { ProviderTestResult } from "@/lib/api";

const MOCKS: { label: string; state: ConnectionTestState }[] = [
  {
    label: "1. testing (loading)",
    state: {
      phase: "testing",
      providerLabel: "Anthropic Claude",
      model: "claude-opus-4-7",
      startedAt: Date.now(),
    },
  },
  {
    label: "2. ok (success → auto-close 2s)",
    state: {
      phase: "result",
      result: mock({ ok: true, category: "ok", http_status: 200, elapsed_ms: 412 }),
    },
  },
  {
    label: "3. network",
    state: {
      phase: "result",
      result: mock({
        ok: false,
        category: "network",
        http_status: null,
        provider_message: "Connection error.",
        elapsed_ms: 1368,
      }),
    },
  },
  {
    label: "4. auth (real Anthropic 401 message)",
    state: {
      phase: "result",
      result: mock({
        ok: false,
        category: "auth",
        http_status: 401,
        provider_message:
          "Error code: 401 - {'type': 'error', 'error': {'type': 'authentication_error', 'message': 'invalid x-api-key'}, 'request_id': 'req_xxxxxxxxxxxxxxxxxxxxxx'}",
        elapsed_ms: 473,
      }),
    },
  },
  {
    label: "5. rate_limit",
    state: {
      phase: "result",
      result: mock({
        ok: false,
        category: "rate_limit",
        http_status: 429,
        provider_message:
          "Rate limit exceeded. Limit: 50 requests/min. Retry after: 60s.",
        elapsed_ms: 233,
      }),
    },
  },
  {
    label: "6. json_format (with raw_response)",
    state: {
      phase: "result",
      result: mock({
        ok: false,
        category: "json_format",
        http_status: 200,
        raw_response:
          'Sure! Here is the connection test reply:\n\n```json\n{"status": "ok", "echo": "ping"}\n```\n\nLet me know if you need anything else!',
        elapsed_ms: 1024,
      }),
    },
  },
  {
    label: "7. unknown",
    state: {
      phase: "result",
      result: mock({
        ok: false,
        category: "unknown",
        http_status: 418,
        provider_message: "I'm a teapot",
        elapsed_ms: 87,
      }),
    },
  },
];

function mock(p: Partial<ProviderTestResult>): ProviderTestResult {
  return {
    ok: false,
    category: "unknown",
    http_status: null,
    provider_message: null,
    raw_response: null,
    elapsed_ms: 0,
    ...p,
  };
}

export default function ConnectionTestShowcase() {
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<ConnectionTestState | null>(null);
  const [secret, setSecret] = useState("");

  return (
    <main className="container max-w-2xl mx-auto py-12 space-y-8">
      <div>
        <h1 className="text-2xl font-bold">v1.1 T3 dev showcase</h1>
        <p className="text-sm text-muted-foreground mt-2">
          点击按钮触发对应状态的 ConnectionTestDialog。SecretInput 显示在下方。
          这是 dev-only 页面，T6 收尾时可删除。
        </p>
      </div>

      <section className="space-y-2">
        <h2 className="font-semibold">SecretInput</h2>
        <SecretInput value={secret} onChange={setSecret} placeholder="sk-..." />
        <p className="text-xs text-muted-foreground">当前值：{secret}</p>
      </section>

      <section className="space-y-2">
        <h2 className="font-semibold">ConnectionTestDialog 状态</h2>
        <div className="grid gap-2">
          {MOCKS.map((m) => (
            <Button
              key={m.label}
              variant="outline"
              onClick={() => {
                // For state 1 (testing), refresh startedAt so the timer is real
                const s =
                  m.state.phase === "testing"
                    ? { ...m.state, startedAt: Date.now() }
                    : m.state;
                setState(s);
                setOpen(true);
              }}
            >
              {m.label}
            </Button>
          ))}
        </div>
      </section>

      <ConnectionTestDialog
        open={open}
        onOpenChange={setOpen}
        state={state}
      />
    </main>
  );
}
