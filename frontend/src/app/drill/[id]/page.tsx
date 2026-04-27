"use client";
import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ChatInterface } from "@/components/chat-interface";
import { answerDrill, startDrill } from "@/lib/api";
import type { DrillResponse } from "@/lib/types";

export default function DrillPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const questionId = Number(id);
  const router = useRouter();
  const [drill, setDrill] = useState<DrillResponse | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    startDrill(questionId).then(setDrill);
  }, [questionId]);

  async function send() {
    if (!drill || !input.trim()) return;
    setBusy(true);
    try {
      const next = await answerDrill(drill.drill_id, input);
      setDrill(next);
      setInput("");
      if (next.status === "ended") {
        setTimeout(() => router.push(`/report/${next.drill_id}`), 1200);
      }
    } finally {
      setBusy(false);
    }
  }

  if (!drill) {
    return <main className="container py-12">起题中……</main>;
  }

  return (
    <main className="container max-w-3xl mx-auto py-8 space-y-4 flex flex-col h-[90vh]">
      <h1 className="text-lg font-bold">单题演练</h1>
      <ChatInterface transcript={drill.transcript} />
      <div className="space-y-2">
        <Textarea
          rows={4}
          placeholder="作答……（可输入 跳过 / 我答完了 / 没思路 / 换个例子）"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={busy || drill.status === "ended"}
        />
        <div className="flex gap-2 justify-between">
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => setInput("跳过")}>跳过</Button>
            <Button size="sm" variant="outline" onClick={() => setInput("能换个例子吗")}>换场景</Button>
            <Button size="sm" variant="outline" onClick={() => setInput("没思路，给点提示")}>求提示</Button>
            <Button size="sm" variant="outline" onClick={() => setInput("我答完了")}>结束</Button>
          </div>
          <Button onClick={send} disabled={busy || drill.status === "ended"}>
            {busy ? "评估中…" : "发送"}
          </Button>
        </div>
      </div>
      {drill.status === "ended" && (
        <p className="text-sm text-muted-foreground">本题结束，即将跳转报告……</p>
      )}
    </main>
  );
}
