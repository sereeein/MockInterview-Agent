"use client";
import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import type { TranscriptTurn } from "@/lib/types";

export function ChatInterface({ transcript }: { transcript: TranscriptTurn[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight, behavior: "smooth" });
  }, [transcript]);

  return (
    <div ref={ref} className="flex-1 overflow-y-auto space-y-3 p-4 border rounded-lg max-h-[60vh]">
      {transcript.map((t, i) => (
        <div key={i} className={cn("flex", t.role === "user" ? "justify-end" : "justify-start")}>
          <div
            className={cn(
              "max-w-[80%] rounded-lg px-4 py-2 text-sm whitespace-pre-wrap",
              t.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted",
              t.kind === "scenario_switch" && "ring-2 ring-amber-400/60",
              t.kind === "prompt_mode" && "ring-2 ring-blue-400/60"
            )}
          >
            {t.kind === "scenario_switch" && (
              <div className="text-xs font-semibold opacity-70 mb-1">↔ 换场景</div>
            )}
            {t.kind === "prompt_mode" && (
              <div className="text-xs font-semibold opacity-70 mb-1">💡 思考框架</div>
            )}
            {t.text}
          </div>
        </div>
      ))}
    </div>
  );
}
