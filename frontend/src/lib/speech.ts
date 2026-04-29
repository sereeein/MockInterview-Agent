// Web Speech API thin wrapper.
// Lives in the browser only; recordings never reach our backend (BYOK invariant).
//
// Provider availability is split: Chrome/Edge route to Google STT; Safari to
// Apple's local STT; Firefox is unsupported. We feature-detect and degrade
// gracefully — if SpeechRecognition is missing, the VoiceInput button doesn't
// render at all.

export type SpeechSupport =
  | { supported: true }
  | { supported: false; reason: "ssr" | "no-api" | "not-secure-context" };

export function detectSpeechSupport(): SpeechSupport {
  if (typeof window === "undefined") {
    return { supported: false, reason: "ssr" };
  }
  if (!window.isSecureContext) {
    return { supported: false, reason: "not-secure-context" };
  }
  // Chrome/Edge expose webkitSpeechRecognition; Safari + spec-compliant browsers
  // expose SpeechRecognition. Both have the same surface for our needs.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const SR = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
  if (!SR) {
    return { supported: false, reason: "no-api" };
  }
  return { supported: true };
}

export interface Recognizer {
  start(): void;
  stop(): void;
}

export interface CreateRecognizerOpts {
  /** BCP 47 language tag, e.g. "zh-CN", "en-US". */
  lang: string;
  /** Called when a new finalized segment arrives — caller appends it. */
  onFinal: (newFinalText: string) => void;
  /** Called whenever interim text changes — caller replaces pending portion.
   *  May be called with empty string to clear the pending portion. */
  onInterim: (currentInterimText: string) => void;
  /** Called on SpeechRecognition error events (event.error). */
  onError: (errorCode: string) => void;
  /** Called when recognition stops (user-initiated or browser auto-stop). */
  onEnd: () => void;
}

export function createRecognizer(opts: CreateRecognizerOpts): Recognizer {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const SR = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
  if (!SR) {
    throw new Error("SpeechRecognition not supported in this browser");
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const r: any = new SR();
  r.lang = opts.lang;
  r.continuous = true;        // user pauses don't auto-end (interview thinking)
  r.interimResults = true;    // emit text as user speaks for instant feedback
  r.maxAlternatives = 1;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  r.onresult = (event: any) => {
    let newFinal = "";
    let interimText = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const segment = event.results[i];
      const transcript = segment[0].transcript;
      if (segment.isFinal) newFinal += transcript;
      else interimText += transcript;
    }
    if (newFinal) opts.onFinal(newFinal);
    // Always emit interim — pass empty to signal "no current pending text"
    opts.onInterim(interimText);
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  r.onerror = (event: any) => {
    opts.onError(event?.error || "unknown");
  };

  r.onend = () => {
    opts.onEnd();
  };

  return {
    start: () => r.start(),
    stop: () => r.stop(),
  };
}

/** Map a SpeechRecognition error code to a Chinese user-facing message.
 *  Returns empty string for codes that should be silently ignored
 *  (no-speech, aborted). */
export function friendlyErrorMessage(code: string): string {
  switch (code) {
    case "not-allowed":
    case "service-not-allowed":
      return "需要麦克风权限。在浏览器地址栏左侧点击🔒重新授权";
    case "network":
      return "语音识别需要联网到识别服务，当前网络不可用。请用键盘输入";
    case "audio-capture":
      return "无法访问麦克风设备";
    case "no-speech":
    case "aborted":
      return ""; // silent — user simply stopped or didn't speak
    default:
      return `语音识别出错：${code}。请用键盘输入`;
  }
}
