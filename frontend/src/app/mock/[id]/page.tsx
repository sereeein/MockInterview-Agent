"use client";
import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ChatInterface } from "@/components/chat-interface";
import { answerDrill, getMock, startDrill } from "@/lib/api";
import type { DrillResponse, MockSession } from "@/lib/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function advanceMock(mockId: number, drillAttemptId: number): Promise<MockSession> {
  const r = await fetch(`${BASE}/mock/${mockId}/advance`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ drill_attempt_id: drillAttemptId }),
  });
  return r.json();
}

export default function MockPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const mockId = Number(id);
  const router = useRouter();
  const [mock, setMock] = useState<MockSession | null>(null);
  const [drill, setDrill] = useState<DrillResponse | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getMock(mockId).then(setMock);
  }, [mockId]);

  useEffect(() => {
    if (!mock) return;
    if (mock.status === "ended") {
      router.push(`/mock/${mockId}/report`);
      return;
    }
    const qid = mock.question_ids[mock.current_index];
    startDrill(qid).then(setDrill);
  }, [mock, mockId, router]);

  async function send() {
    if (!drill || !mock || !input.trim()) return;
    setBusy(true);
    try {
      const next = await answerDrill(drill.drill_id, input);
      setDrill(next);
      setInput("");
      if (next.status === "ended") {
        const updated = await advanceMock(mockId, next.drill_id);
        setMock(updated);
        setDrill(null);
      }
    } finally {
      setBusy(false);
    }
  }

  if (!mock) return <main className="container py-12">加载……</main>;

  return (
    <main className="container max-w-3xl mx-auto py-8 space-y-4 flex flex-col h-[90vh]">
      <h1 className="text-lg font-bold">
        模拟面试 · 题 {mock.current_index + 1} / {mock.question_ids.length}
      </h1>
      {drill ? (
        <>
          <ChatInterface transcript={drill.transcript} />
          <Textarea
            rows={4}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={busy || drill.status === "ended"}
            placeholder="作答……"
          />
          <Button onClick={send} disabled={busy || drill.status === "ended"}>
            {busy ? "评估中…" : "发送"}
          </Button>
        </>
      ) : (
        <p>下一题加载中……</p>
      )}
    </main>
  );
}
