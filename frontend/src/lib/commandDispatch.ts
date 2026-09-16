import type { NavigateFunction } from "react-router-dom";

export interface CommandDispatchDeps {
  navigate: NavigateFunction;
  speak: (text: string) => void;
  stopSpeaking: () => void;
  getActiveDocumentText: () => string | null;
}

const NAVIGATE_TARGETS: Record<string, string> = {
  navigate_to_crawl: "/crawl",
  navigate_to_collections: "/collections",
  navigate_to_search: "/search",
  navigate_to_metrics: "/metrics",
  navigate_to_lang_id: "/lang-id",
  navigate_to_summarization: "/summarization",
  navigate_to_translation: "/translation",
  navigate_to_settings: "/settings",
  navigate_to_help: "/help",
};

export function dispatchSpeechCommandAction(
  action: string,
  transcript: string,
  deps: CommandDispatchDeps,
): void {
  const navigateTarget = NAVIGATE_TARGETS[action];
  if (navigateTarget) {
    deps.navigate(navigateTarget);
    return;
  }
  switch (action) {
    case "navigate_search":
      deps.navigate(`/search?voiceQuery=${encodeURIComponent(transcript)}`);
      break;
    case "clear_query":
      deps.navigate("/search?voiceQuery=");
      break;
    case "read_document": {
      const text = deps.getActiveDocumentText();
      if (text) deps.speak(text);
      break;
    }
    case "stop_speaking":
      deps.stopSpeaking();
      break;
    default:
      break;
  }
}
