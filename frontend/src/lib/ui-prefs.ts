export type SpeechLang = "zh-CN" | "zh-TW" | "en-US";

export interface UiPrefs {
  speechLang: SpeechLang;
}

const STORAGE_KEY = "mockinterview.uiPrefs";

const DEFAULT_PREFS: UiPrefs = {
  speechLang: "zh-CN",
};

export function getUiPrefs(): UiPrefs {
  if (typeof window === "undefined") return DEFAULT_PREFS;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_PREFS;
    const parsed = JSON.parse(raw) as Partial<UiPrefs>;
    return {
      speechLang: parsed.speechLang ?? DEFAULT_PREFS.speechLang,
    };
  } catch {
    return DEFAULT_PREFS;
  }
}

export function setUiPrefs(prefs: UiPrefs): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
}

export function patchUiPrefs(patch: Partial<UiPrefs>): UiPrefs {
  const next: UiPrefs = { ...getUiPrefs(), ...patch };
  setUiPrefs(next);
  return next;
}
