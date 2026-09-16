import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

const STORAGE_KEY = "ips-speech-settings";

interface SpeechSettings {
  voice: string;
  rate: number;
  volume: number;
  sttLanguage: string;
  /** Wake phrase gating the always-on ambient listening mode
   * (SpeechModeContext) — empty means no gating (every utterance heard
   * while listening is checked against active commands, today's default
   * behavior). Push-to-talk (VoiceInputButton) never requires this: pressing
   * the button is already an explicit activation. */
  activationPhrase: string;
}

const DEFAULT_SETTINGS: SpeechSettings = {
  voice: "en_US-amy-medium",
  rate: 1.0,
  volume: 1.0,
  sttLanguage: "en",
  activationPhrase: "",
};

function loadSettings(): SpeechSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    return { ...DEFAULT_SETTINGS, ...(JSON.parse(raw) as Partial<SpeechSettings>) };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

interface SpeechSettingsContextValue extends SpeechSettings {
  update: (patch: Partial<SpeechSettings>) => void;
}

const SpeechSettingsContext = createContext<SpeechSettingsContextValue | null>(null);

export function SpeechSettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<SpeechSettings>(loadSettings);

  const update = useCallback((patch: Partial<SpeechSettings>) => {
    setSettings((prev) => {
      const next = { ...prev, ...patch };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  return (
    <SpeechSettingsContext.Provider value={{ ...settings, update }}>
      {children}
    </SpeechSettingsContext.Provider>
  );
}

export function useSpeechSettings(): SpeechSettingsContextValue {
  const ctx = useContext(SpeechSettingsContext);
  if (!ctx) {
    throw new Error("useSpeechSettings must be used within a SpeechSettingsProvider");
  }
  return ctx;
}
