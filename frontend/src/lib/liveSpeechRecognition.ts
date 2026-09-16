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
  recognition.onerror = () => {};
  recognition.onend = () => {
    if (!stopped) {
      try {
        recognition.start();
      } catch {
        // Some browsers throw when restarting too soon after onend; preview just stops updating.
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
      } catch {}
    },
  };
}

