import type { NavigateFunction } from "react-router-dom";

/**
 * What each speech_commands.action actually does, in one place — used both
 * by a page's own push-to-talk VoiceInputButton and by the global
 * always-listening speech mode, so a command behaves identically regardless
 * of which one heard it.
 */
export interface CommandDispatchDeps {
  navigate: NavigateFunction;
  speak: (text: string) => void;
  stopSpeaking: () => void;
  getActiveDocumentText: () => string | null;
}

/** Plain "go to that tab" actions, one per Layout.tsx nav item — a lookup
 * table rather than one switch case each since they're all the same shape
 * (navigate, no args). */
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
      // Encoded empty voiceQuery (rather than a bare "/search") so
      // SearchPage's handler still runs and clears its query box even if
      // the user is already on that page.
      deps.navigate("/search?voiceQuery=");
      break;
    case "read_document": {
      // Prefers an explicitly open document dialog (see
      // SpeechModeContext's activeDocumentTextRef); otherwise falls back to
      // the first still-mounted readable block registered via
      // useReadableText (e.g. a summary or a translation result) — "the
      // first block with playback available on the page," per LR9's ask.
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
