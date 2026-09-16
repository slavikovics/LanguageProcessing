import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";
import { listSpeechCommands } from "@/api/client";
import type { SpeechCommand } from "@/api/types";
import { isVolumeMeterSupported } from "@/lib/micVolumeMeter";
import { isLiveSttSupported, useLiveSttStream } from "@/hooks/useLiveSttStream";
import { dispatchSpeechCommandAction } from "@/lib/commandDispatch";
import { startLiveTranscription } from "@/lib/liveSpeechRecognition";
import { matchCommand } from "@/lib/matchCommand";
import { MESSAGE_HOLD_MS, PHRASE_PAUSE_MS } from "@/lib/speechTiming";
import { useSpeechPlayback } from "./SpeechPlaybackContext";
import { useSpeechSettings } from "./SpeechSettingsContext";

const SILENCE_LEVEL_THRESHOLD = 0.06;
/** How long (ms) a pause in speech must last before an utterance is
 * considered finished and checked against active commands — this is what
 * lets ambient mode wait for the user to actually stop talking (Siri/Google
 * Assistant style) instead of committing to whatever the current ~3.5s
 * recorder chunk happens to contain (see useLiveSttStream's chunkMs), which
 * cuts a longer phrase in half at an arbitrary boundary. Shared with
 * VoiceInputButton's auto-stop-on-silence wait (see speechTiming.ts) so the
 * two don't drift apart. */
const UTTERANCE_SILENCE_GAP_MS = PHRASE_PAUSE_MS;
/** Force-evaluates an utterance even without a detected pause, so a long
 * run-on without silence still eventually gets checked. */
const MAX_UTTERANCE_MS = 12000;
/** Chrome's Web Speech recognizer isn't purely local — it round-trips audio
 * to a recognition service — so it can still be mid-flight finalizing the
 * tail of what was just said at the exact moment UTTERANCE_SILENCE_GAP_MS of
 * raw mic silence elapses. Flushing right then locks in a "consumed" caption
 * boundary that's missing those last words; once the recognizer catches up
 * a moment later, they land past that boundary and get misread as the start
 * of the NEXT utterance instead of the tail of the one just dispatched. The
 * flush gate additionally requires the caption stream itself to have been
 * quiet for this long, so a recognizer still actively updating never gets
 * cut off mid-word. */
const CAPTION_SETTLE_MS = 500;
/** If speech-service itself is unreachable (container down/restarting), the
 * gateway doesn't close the WebSocket — it just sends an {"type":"error"}
 * frame back for each chunk and keeps the connection open (see
 * routers/speech.py), so onUnavailable/onFinal never fire and the mic stays
 * shown as "listening" indefinitely with whatever was last heard frozen in
 * the bubble, even though nothing is actually being transcribed anymore.
 * This many CONSECUTIVE chunk errors (no successful one in between) is
 * treated the same as the backend having gone away entirely — the session
 * is torn down and the UI is reset exactly like onUnavailable does. */
const REPEATED_ERROR_LIMIT = 3;

/**
 * "Ambient mode": once toggled on, listens continuously via the same live
 * faster-whisper stream push-to-talk dictation uses (hooks/useLiveSttStream)
 * — chunks keep arriving every ~3.5s, but they're accumulated into one
 * "current utterance" buffer that's only checked against speech_commands
 * once the mic actually goes quiet for a bit (UTTERANCE_SILENCE_GAP_MS,
 * detected from the same mic-loudness signal that drives the volume ring),
 * optionally gated behind an activation phrase
 * (SpeechSettingsContext.activationPhrase). Where AudioContext-based
 * loudness metering isn't available at all, falls back to the older
 * evaluate-every-chunk-immediately behavior rather than never matching
 * anything. Also tracks what "read this" should read: an explicitly open
 * document dialog takes priority (activeDocumentTextRef); otherwise it falls
 * back to whichever readable block (e.g. a summary or translation result)
 * registered itself first via useReadableText, mirroring page/DOM order.
 */
interface SpeechModeContextValue {
  isListening: boolean;
  isSupported: boolean;
  notice: string | null;
  partialTranscript: string | null;
  /** Increments every time a voice command is recognized and dispatched —
   * a token rather than a boolean so repeated commands each retrigger a
   * consumer's flash animation even if it fires again before the previous
   * one finished. There's no text notice for this anymore (see
   * handleUtterance); AssistantMicButton turns this into a brief green-wave
   * pulse on the mic itself instead. */
  commandFlashToken: number;
  toggle: () => void;
  /** Re-fetches speech_commands into commandsRef immediately — called by the
   * Settings "Команды" tab after every create/edit/delete/toggle so ambient
   * mode's client-side matching (see matchCommand) reflects the edit right
   * away instead of only picking it up the next time the mic is toggled on
   * (which is when commandsRef was previously ever (re)populated). */
  refreshCommands: () => void;
  setActiveDocumentText: (text: string | null) => void;
  getActiveDocumentText: () => string | null;
  /** Registers/unregisters one page's readable block under a stable id (see
   * useReadableText) — insertion order is preserved (a Map), so "the first
   * one" naturally follows whichever block mounted first, i.e. page order. */
  registerReadableText: (id: string, text: string) => void;
  unregisterReadableText: (id: string) => void;
  /** Current mic loudness, 0..1, updated every animation frame while
   * listening. A ref-backed getter rather than state — consumers that want
   * to animate off it (AssistantMicButton) read it in their own rAF loop so
   * a busy mic doesn't force a React re-render 60 times a second. */
  getVolume: () => number;
}

const SpeechModeContext = createContext<SpeechModeContextValue | null>(null);

export function SpeechModeProvider({ children }: { children: ReactNode }) {
  const { sttLanguage, activationPhrase } = useSpeechSettings();
  const { speak, stop: stopSpeaking, primeAudioContext } = useSpeechPlayback();
  const navigate = useNavigate();

  const [isListening, setIsListening] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [partialTranscript, setPartialTranscript] = useState<string | null>(null);
  const [commandFlashToken, setCommandFlashToken] = useState(0);
  const commandsRef = useRef<SpeechCommand[]>([]);
  const activeDocumentTextRef = useRef<string | null>(null);
  /** Insertion-ordered so the first still-mounted entry is the first block
   * that appeared on the current page — see registerReadableText/
   * getActiveDocumentText's fallback below. */
  const readableTextsRef = useRef<Map<string, string>>(new Map());
  const partialTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const startingRef = useRef(false);
  const volumeRef = useRef(0);

  const volumeMeterSupportedRef = useRef(isVolumeMeterSupported());
  const utteranceChunksRef = useRef<string[]>([]);
  const utteranceStartedAtRef = useRef(0);
  const lastLoudAtRef = useRef(0);
  const hasSpokenRef = useRef(false);
  const captionRef = useRef<{ stop: () => void } | null>(null);
  /** Live caption text for the utterance currently in progress — kept
   * separately from what's shown in the bubble (showPartial/
   * setPartialTranscript is the same value, just also fed through the
   * auto-clear timer) so flushUtterance can match/dispatch against it
   * instead of utteranceChunksRef's server-decoded text. The caption
   * (continuous, low-latency) is consistently more accurate in practice than
   * faster-whisper's per-~3.5s-chunk "stream" model, which decodes mostly
   * without cross-chunk context.
   *
   * Reset by fully stopping and restarting the underlying SpeechRecognition
   * (see restartCaption) once a phrase ends, rather than tracking a
   * consumed-offset into one long-lived session — an offset-based version
   * was tried, but Chrome's recognizer sometimes revises/re-finalizes the
   * tail of an utterance slightly differently a moment after it was already
   * used for a flush, and that revision landed past the old offset,
   * reappearing as stray leftover text from an utterance that had already
   * been correctly matched and dispatched. A full restart has no such
   * carryover: the new recognition starts with a completely empty
   * transcript, so nothing from the previous utterance can leak into the
   * next one. The tradeoff is the engine's brief reinitialization latency,
   * which CAPTION_SETTLE_MS (below) exists to stay clear of. */
  const captionTextRef = useRef("");
  /** Timestamp of the last caption update — see CAPTION_SETTLE_MS. */
  const captionUpdatedAtRef = useRef(0);
  /** Consecutive chunk errors with no successful one in between — see
   * REPEATED_ERROR_LIMIT. Reset on every successful chunk. */
  const consecutiveErrorsRef = useRef(0);

  useEffect(() => {
    if (!notice) return;
    const timeout = setTimeout(() => setNotice(null), MESSAGE_HOLD_MS);
    return () => clearTimeout(timeout);
  }, [notice]);

  /** Live caption while actively speaking — auto-clears after MESSAGE_HOLD_MS
   * only as a safety net (e.g. the stream stalls mid-utterance); normally
   * it's superseded well before then, either by the next update while still
   * talking or by flushUtterance settling it once you pause. */
  const showPartial = useCallback((text: string) => {
    setPartialTranscript(text);
    if (partialTimeoutRef.current !== null) clearTimeout(partialTimeoutRef.current);
    partialTimeoutRef.current = setTimeout(() => setPartialTranscript(null), MESSAGE_HOLD_MS);
  }, []);

  const handleCaptionUpdate = useCallback(
    (text: string) => {
      captionUpdatedAtRef.current = Date.now();
      // Mirrors onPartial's utteranceStartedAtRef bookkeeping below, but for
      // the caption source — needed so ranTooLong/wentQuiet timing reflects
      // when THIS utterance actually started even if the server hasn't sent
      // a single non-empty chunk for it yet (see the onVolume flush gate).
      if (!captionTextRef.current.trim() && text.trim()) {
        utteranceStartedAtRef.current = Date.now();
      }
      captionTextRef.current = text;
      showPartial(text);
    },
    [showPartial],
  );

  const restartCaption = useCallback(() => {
    captionRef.current?.stop();
    captionTextRef.current = "";
    captionRef.current = startLiveTranscription(sttLanguage, handleCaptionUpdate);
  }, [sttLanguage, handleCaptionUpdate]);

  /** Instantly clears whatever's currently shown near the mic (the "what
   * you last said" bubble and its overlays) — called whenever the mic stops
   * listening, whether from the user toggling it off, the stream reaching
   * its own "final", or it going unavailable (mic denied, connection lost).
   * Previously only the manual toggle-off path did this, so a dropped
   * connection left the last heard phrase sitting there looking current
   * even though the mic had already gone quiet. */
  const resetTranscriptUi = useCallback(() => {
    captionRef.current?.stop();
    captionRef.current = null;
    captionTextRef.current = "";
    captionUpdatedAtRef.current = 0;
    consecutiveErrorsRef.current = 0;
    utteranceChunksRef.current = [];
    hasSpokenRef.current = false;
    if (partialTimeoutRef.current !== null) {
      clearTimeout(partialTimeoutRef.current);
      partialTimeoutRef.current = null;
    }
    setPartialTranscript(null);
  }, []);

  /** Checks one finished utterance against active commands, dispatching and
   * flashing the mic (see commandFlashToken) on a match instead of a text
   * notice. Returns whether it matched, so flushUtterance can decide what
   * (if anything) to leave on screen for an utterance that didn't. */
  const handleUtterance = useCallback(
    (utterance: string): boolean => {
      let effective = utterance;
      const phrase = activationPhrase.trim();
      if (phrase) {
        // Case-insensitive substring search on the original text (not the
        // fully punctuation-stripped `normalize()`) so the remainder passed
        // to dispatchSpeechCommandAction keeps its original casing/
        // punctuation — matters for navigate_search, which uses it
        // verbatim as the search query.
        const index = utterance.toLowerCase().indexOf(phrase.toLowerCase());
        if (index === -1) return false;
        effective = utterance.slice(index + phrase.length).trim();
      }
      const matched = matchCommand(effective, commandsRef.current);
      if (!matched) return false;
      setCommandFlashToken((token) => token + 1);
      dispatchSpeechCommandAction(matched.action, effective, {
        navigate,
        speak,
        stopSpeaking,
        getActiveDocumentText: () => activeDocumentTextRef.current,
      });
      return true;
    },
    [activationPhrase, navigate, speak, stopSpeaking],
  );

  const flushUtterance = useCallback(() => {
    // Prefer the live caption's text for matching/dispatch, same reasoning
    // as its use for the bubble — it's what the user actually saw and is
    // consistently more accurate than the server's per-chunk transcript.
    // Read before restartCaption() below clears it for the next utterance.
    // Falls back to the server text when no caption ran at all (Web Speech
    // unsupported).
    const caption = captionTextRef.current.trim();
    const serverText = utteranceChunksRef.current.join(" ").trim();
    const text = caption || serverText;
    utteranceChunksRef.current = [];
    hasSpokenRef.current = false;
    // The phrase has ended (matched or not) — kill the caption's detection
    // process and start it over from a clean slate (see captionTextRef's
    // comment above) so nothing from this utterance can carry into the next.
    if (captionRef.current) restartCaption();
    if (!text) {
      setPartialTranscript(null);
      return;
    }
    const matched = handleUtterance(text);
    if (partialTimeoutRef.current !== null) {
      clearTimeout(partialTimeoutRef.current);
      partialTimeoutRef.current = null;
    }
    // A matched command already gets its own confirmation via the mic's
    // green-wave flash (see commandFlashToken) — no text needed. An
    // unmatched phrase instead keeps showing what was heard for a bit
    // (PHRASE_PAUSE_MS) so it's not blanked the instant the pause is
    // detected, but it still needs its own auto-clear timer here — it's no
    // longer being fed by showPartial's own timer (that one was just
    // cancelled above), and without one it would otherwise sit there
    // forever until either the next utterance's caption starts overwriting
    // it or ambient mode is turned off.
    setPartialTranscript(matched ? null : text);
    if (!matched) {
      partialTimeoutRef.current = setTimeout(() => setPartialTranscript(null), PHRASE_PAUSE_MS);
    }
  }, [handleUtterance, restartCaption]);

  const live = useLiveSttStream({
    language: sttLanguage,
    onVolume: (level) => {
      volumeRef.current = level;
      if (!volumeMeterSupportedRef.current) return;
      const now = Date.now();
      if (level > SILENCE_LEVEL_THRESHOLD) {
        lastLoudAtRef.current = now;
        hasSpokenRef.current = true;
      }
      const wentQuiet = hasSpokenRef.current && now - lastLoudAtRef.current > UTTERANCE_SILENCE_GAP_MS;
      const ranTooLong = now - utteranceStartedAtRef.current > MAX_UTTERANCE_MS;
      // Gate on either source having unconsumed content, not just the
      // server chunks — the server's per-chunk faster-whisper model
      // sometimes returns an empty transcript for a chunk (VAD filtered it,
      // audio was too quiet/short) while the caption still captured real
      // words. Gating on server chunks alone left that caption text sitting
      // unflushed (Web Speech's continuous mode keeps accumulating it)
      // until some later, unrelated chunk finally came back non-empty —
      // at which point flushUtterance fired with a long, stale string
      // covering everything said since the last real flush, effectively
      // re-dispatching an utterance well after the user had gone quiet.
      const hasPendingContent =
        utteranceChunksRef.current.length > 0 || captionTextRef.current.trim().length > 0;
      // Beyond raw mic silence, also require the caption stream itself to
      // have gone quiet for CAPTION_SETTLE_MS before committing to a flush
      // (see its comment above) — skipped when there's no caption running
      // at all, and overridden by ranTooLong so a recognizer that somehow
      // never settles can't wedge an utterance open forever.
      const captionSettled =
        !captionRef.current || now - captionUpdatedAtRef.current > CAPTION_SETTLE_MS;
      if (hasPendingContent && (ranTooLong || (wentQuiet && captionSettled))) {
        flushUtterance();
      }
    },
    onPartial: (chunkText) => {
      // A chunk round-tripped successfully — whatever error streak was
      // building (see REPEATED_ERROR_LIMIT) is over.
      consecutiveErrorsRef.current = 0;
      const trimmed = chunkText.trim();
      if (trimmed) {
        if (utteranceChunksRef.current.length === 0) utteranceStartedAtRef.current = Date.now();
        utteranceChunksRef.current.push(trimmed);
      }
      if (!volumeMeterSupportedRef.current) {
        // No mic-loudness signal to detect a pause in this browser — fall
        // back to evaluating each chunk the moment it arrives, same as
        // before utterance buffering existed, so ambient mode still reacts.
        handleUtterance(chunkText);
        return;
      }
      if (!captionRef.current) {
        // No Web Speech live-caption overlay available either — show the
        // accumulating server transcript directly.
        showPartial(utteranceChunksRef.current.join(" "));
      }
    },
    onFinal: () => {
      // Ambient mode never sends a "stop" frame itself (see stopListening);
      // reaching "final" here means the connection is being torn down.
      resetTranscriptUi();
      setIsListening(false);
    },
    onError: () => {
      // One bad chunk shouldn't interrupt ambient listening — the stream
      // keeps running and the next chunk is unaffected. But a run of them
      // with nothing successful in between means speech-service itself is
      // gone (see REPEATED_ERROR_LIMIT) — tear the session down and reset
      // the UI instead of leaving the mic looking "on" forever while
      // silently transcribing nothing.
      consecutiveErrorsRef.current += 1;
      if (consecutiveErrorsRef.current >= REPEATED_ERROR_LIMIT) {
        stopListening();
        setNotice("Соединение с сервером распознавания речи потеряно. Попробуйте снова.");
      }
    },
    onUnavailable: (reason) => {
      resetTranscriptUi();
      setNotice(
        reason === "mic_denied"
          ? "Не удалось получить доступ к микрофону."
          : reason === "connection_lost"
            ? "Соединение с сервером распознавания речи потеряно. Попробуйте снова."
            : reason === "mic_lost"
              ? "Микрофон отключился — голосовой режим остановлен."
              : "Голосовой режим не поддерживается этим браузером.",
      );
      setIsListening(false);
    },
  });

  const isSupported = isLiveSttSupported();

  const stopListening = useCallback(() => {
    live.stop();
    resetTranscriptUi();
    setIsListening(false);
    volumeRef.current = 0;
  }, [live, resetTranscriptUi]);

  const getVolume = useCallback(() => volumeRef.current, []);

  const refreshCommands = useCallback(() => {
    void (async () => {
      try {
        commandsRef.current = await listSpeechCommands();
      } catch {
        // Transient failure — keep whatever command set was already loaded
        // rather than wiping it out from under an active listening session.
      }
    })();
  }, []);

  // Stop the mic only on a genuine unmount of this provider, not on every
  // re-render. useLiveSttStream() returns a brand-new `{isStreaming, start,
  // stop}` object literal on every render, so `live` — and therefore
  // `stopListening`, which depends on it — gets a new identity on every
  // single re-render of this component (including the setIsStreaming(true)
  // that fires the instant the mic connects, and every setPartialTranscript
  // from a live chunk arriving). `useEffect(() => stopListening, [dep])`
  // treats whatever the callback returns as its cleanup, so a changing `dep`
  // ran that cleanup — i.e. called stop() — after nearly every render,
  // killing the session moments after it started. A ref keeps the effect's
  // own dependency array empty (mount/unmount only) while still calling
  // through to the latest stopListening when the real unmount happens.
  const stopListeningRef = useRef(stopListening);
  useEffect(() => {
    stopListeningRef.current = stopListening;
  }, [stopListening]);
  useEffect(() => {
    return () => stopListeningRef.current();
  }, []);

  const toggle = useCallback(() => {
    if (isListening || startingRef.current) {
      if (isListening) stopListening();
      return;
    }
    if (!isSupported) {
      setNotice("Голосовой режим не поддерживается этим браузером.");
      return;
    }
    // Set synchronously (not after an await) so a second click landing
    // before this async chain resolves is a no-op instead of racing a
    // second getUserMedia()/WebSocket into existence — the underlying
    // hook's own guard only covers its half of the work, not the
    // listSpeechCommands() fetch that runs first here.
    startingRef.current = true;
    // Must also run synchronously inside this click handler (not after an
    // await) — this is the one real user gesture that unlocks playback
    // for every voice-triggered "read this" from here on, since a later
    // streaming callback doesn't count as one itself.
    primeAudioContext();
    void (async () => {
      try {
        commandsRef.current = await listSpeechCommands();
      } catch {
        commandsRef.current = [];
      }
      utteranceChunksRef.current = [];
      hasSpokenRef.current = false;
      captionTextRef.current = "";
      captionUpdatedAtRef.current = 0;
      const started = await live.start();
      startingRef.current = false;
      if (started) {
        setIsListening(true);
        captionRef.current = startLiveTranscription(sttLanguage, handleCaptionUpdate);
      }
      // On failure, onUnavailable has already set its own notice and
      // isListening stays false — nothing more to do here.
    })();
  }, [isListening, isSupported, live, primeAudioContext, sttLanguage, handleCaptionUpdate, stopListening]);

  const setActiveDocumentText = useCallback((text: string | null) => {
    activeDocumentTextRef.current = text;
  }, []);
  const getActiveDocumentText = useCallback(() => {
    if (activeDocumentTextRef.current?.trim()) return activeDocumentTextRef.current;
    for (const text of readableTextsRef.current.values()) {
      if (text.trim()) return text;
    }
    return null;
  }, []);
  const registerReadableText = useCallback((id: string, text: string) => {
    if (text.trim()) readableTextsRef.current.set(id, text);
    else readableTextsRef.current.delete(id);
  }, []);
  const unregisterReadableText = useCallback((id: string) => {
    readableTextsRef.current.delete(id);
  }, []);

  const value: SpeechModeContextValue = {
    isListening,
    isSupported,
    notice,
    partialTranscript,
    commandFlashToken,
    toggle,
    refreshCommands,
    setActiveDocumentText,
    getActiveDocumentText,
    registerReadableText,
    unregisterReadableText,
    getVolume,
  };

  return <SpeechModeContext.Provider value={value}>{children}</SpeechModeContext.Provider>;
}

export function useSpeechMode(): SpeechModeContextValue {
  const ctx = useContext(SpeechModeContext);
  if (!ctx) {
    throw new Error("useSpeechMode must be used within a SpeechModeProvider");
  }
  return ctx;
}

/** Registers `text` as a "read this"-able block for as long as the calling
 * component is mounted with non-empty text — e.g. a summary result or a
 * translation's source/translated text. Pass "" (not conditionally skipping
 * the hook) when there's nothing to read yet; it's a no-op until `text` is
 * non-empty. Several blocks on the same page each register independently;
 * the "read this" command reads whichever registered first (see
 * getActiveDocumentText), which follows mount/DOM order in practice. */
export function useReadableText(text: string): void {
  const { registerReadableText, unregisterReadableText } = useSpeechMode();
  const id = useId();
  useEffect(() => {
    registerReadableText(id, text);
    return () => unregisterReadableText(id);
  }, [id, text, registerReadableText, unregisterReadableText]);
}
