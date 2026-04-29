"use client";
import { useEffect, useRef, useState } from "react";
import { Mic, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  createRecognizer,
  detectSpeechSupport,
  friendlyErrorMessage,
  type Recognizer,
} from "@/lib/speech";
import { getUiPrefs } from "@/lib/ui-prefs";

type Phase = "idle" | "recording" | "stopping";

type Props = {
  /** Current textarea value (controlled). VoiceInput appends transcribed text. */
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
};

/** Speech-to-text button for textarea inputs. Click to start, click again to stop.
 *  Final segments append plain to value; interim segments replace the trailing
 *  pending portion. If the user edits during recording, interim text may stop
 *  being detected as a suffix and stay in place — acceptable trade-off. */
export function VoiceInput({ value, onChange, disabled }: Props) {
  // Defer detectSpeechSupport() to useEffect so SSR and client first paint
  // both render null (avoids hydration mismatch — SSR sees no `window`,
  // client sees SpeechRecognition API). After mount, run the check and
  // re-render with the real support state.
  const [supported, setSupported] = useState<ReturnType<typeof detectSpeechSupport> | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);

  const recognizerRef = useRef<Recognizer | null>(null);
  const interimRef = useRef("");
  const valueRef = useRef(value);
  valueRef.current = value;

  // Detect support post-mount (skips hydration mismatch)
  useEffect(() => {
    setSupported(detectSpeechSupport());
  }, []);

  // Auto-fade error after 3s
  useEffect(() => {
    if (!error) return;
    const id = setTimeout(() => setError(null), 3000);
    return () => clearTimeout(id);
  }, [error]);

  // Cleanup recognizer on unmount
  useEffect(() => {
    return () => {
      try {
        recognizerRef.current?.stop();
      } catch {
        // ignore — already stopped
      }
    };
  }, []);

  // Pre-detection (SSR + first client paint): render nothing
  if (!supported) return null;
  if (!supported.supported) {
    // Definitely unsupported (Firefox / HTTP) — graceful degradation
    return null;
  }

  function stripInterim(): string {
    const cur = valueRef.current;
    if (interimRef.current && cur.endsWith(interimRef.current)) {
      return cur.slice(0, -interimRef.current.length);
    }
    return cur;
  }

  function start() {
    setError(null);
    setPhase("recording");
    interimRef.current = "";

    try {
      const r = createRecognizer({
        lang: getUiPrefs().speechLang,
        onFinal: (newFinalText) => {
          const cleaned = stripInterim();
          onChange(cleaned + newFinalText);
          interimRef.current = "";
        },
        onInterim: (text) => {
          const cleaned = stripInterim();
          onChange(cleaned + text);
          interimRef.current = text;
        },
        onError: (code) => {
          const msg = friendlyErrorMessage(code);
          if (msg) setError(msg);
          setPhase("idle");
          // Strip any unfinalized interim so user isn't stuck with provisional text
          const cleaned = stripInterim();
          if (cleaned !== valueRef.current) onChange(cleaned);
          interimRef.current = "";
        },
        onEnd: () => {
          setPhase("idle");
          const cleaned = stripInterim();
          if (cleaned !== valueRef.current) onChange(cleaned);
          interimRef.current = "";
        },
      });
      r.start();
      recognizerRef.current = r;
    } catch (e) {
      setError(
        `无法启动语音识别：${e instanceof Error ? e.message : "unknown"}`,
      );
      setPhase("idle");
    }
  }

  function stop() {
    setPhase("stopping");
    try {
      recognizerRef.current?.stop();
    } catch {
      // ignore — onEnd will still fire
    }
    // onEnd handler will reset phase to "idle"; safety fallback:
    setTimeout(() => {
      setPhase((p) => (p === "stopping" ? "idle" : p));
    }, 1500);
  }

  function toggle() {
    if (phase === "recording") stop();
    else if (phase === "idle") start();
  }

  return (
    <div className="relative">
      <Button
        type="button"
        size="icon-sm"
        variant={phase === "recording" ? "destructive" : "ghost"}
        onClick={toggle}
        disabled={disabled || phase === "stopping"}
        aria-label={phase === "recording" ? "停止录音" : "开始语音输入"}
        title={phase === "recording" ? "再次点击停止" : "语音输入"}
        className={cn(
          phase === "recording" && "animate-pulse",
        )}
      >
        {phase === "recording" ? <Square /> : <Mic />}
      </Button>
      {error && (
        <div
          className="absolute right-0 bottom-full mb-2 w-64 max-w-[calc(100vw-2rem)] rounded border border-destructive/30 bg-destructive/10 text-destructive px-2 py-1 text-xs shadow-md"
          role="alert"
        >
          {error}
        </div>
      )}
    </div>
  );
}
