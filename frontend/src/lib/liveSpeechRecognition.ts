/** Minimal shape of the (non-standardized, Chrome/Edge-only) Web Speech API
 * SpeechRecognition interface — not in TypeScript's DOM lib, so declared
 * locally rather than pulling in a whole @types package for a few fields. */
interface LiveRecognitionResult {
  isFinal: boolean;
  0: { transcript: string };
}

interface LiveRecognitionEvent {
  resultIndex: number;
  results: ArrayLike<LiveRecognitionResult>;
}

interface LiveRecognition extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start(): void;
  stop(): void;
  onresult: ((event: LiveRecognitionEvent) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
}

type LiveRecognitionConstructor = new () => LiveRecognition;

const LANG_TAGS: Record<string, string> = { en: "en-US", ru: "ru-RU" };

function getConstructor(): LiveRecognitionConstructor | null {
  const w = window as unknown as {
    SpeechRecognition?: LiveRecognitionConstructor;
    webkitSpeechRecognition?: LiveRecognitionConstructor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

/**
 * Best-effort *live* caption while recording, using the browser's built-in
 * Web Speech API purely as a "words appear as you speak" preview — the
 * authoritative transcript and command matching still come from the local
 * faster-whisper backend (see SpeechHelp's "Почему не Web Speech API": that
 * choice still stands, this is only a cosmetic layer on top of it, updating
 * far more often than the ~3.5s server chunk cadence). Returns null where
 * the API isn't available (e.g. Firefox); callers must treat that as "no
 * live preview" and keep working exactly as before.
 */
export function startLiveTranscription(
  language: string,
  onUpdate: (text: string) => void,
): { stop: () => void } | null {
  const Ctor = getConstructor();
  if (!Ctor) return null;

  let stopped = false;
  let finalText = "";
  const recognition = new Ctor();
  recognition.lang = LANG_TAGS[language] ?? language;
  recognition.continuous = true;
  recognition.interimResults = true;

  recognition.onresult = (event) => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      if (result.isFinal) {
        finalText = finalText ? `${finalText} ${result[0].transcript}` : result[0].transcript;
      } else {
        interim += result[0].transcript;
      }
    }
    const combined = `${finalText} ${interim}`.trim();
    if (combined) onUpdate(combined);
  };
  recognition.onerror = () => {
    // Best-effort only — the backend transcription is authoritative, so a
    // live-preview hiccup (no-speech, permission race, etc.) isn't surfaced.
  };
  recognition.onend = () => {
    if (!stopped) {
      try {
        recognition.start();
      } catch {
        // Some browsers throw when restarting too quickly after onend;
        // the preview just stops updating until the next click, which is
        // harmless since it's cosmetic.
      }
    }
  };

  try {
    recognition.start();
  } catch {
    return null;
  }

  return {
    stop() {
      stopped = true;
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.onend = null;
      try {
        recognition.stop();
      } catch {
        // already stopped
      }
    },
  };
}

