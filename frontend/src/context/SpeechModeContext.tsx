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
import {
  CAPTION_SETTLE_MS,
  MAX_UTTERANCE_MS,
  MESSAGE_HOLD_MS,
  PHRASE_PAUSE_MS,
  REPEATED_ERROR_LIMIT,
  SILENCE_LEVEL_THRESHOLD,
  UTTERANCE_SILENCE_GAP_MS,
} from "@/lib/speechTiming";
import { useSpeechPlayback } from "./SpeechPlaybackContext";
import { useSpeechSettings } from "./SpeechSettingsContext";

interface SpeechModeContextValue {
  isListening: boolean;
  isSupported: boolean;
  notice: string | null;
  partialTranscript: string | null;
  commandFlashToken: number;
  toggle: () => void;
  refreshCommands: () => void;
  setActiveDocumentText: (text: string | null) => void;
  getActiveDocumentText: () => string | null;
  registerReadableText: (id: string, text: string) => void;
  unregisterReadableText: (id: string) => void;
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
  // Full restart (not offset tracking) avoids Chrome re-finalizing stale tail text into the next utterance.
  const captionTextRef = useRef("");
  const captionUpdatedAtRef = useRef(0);
  const consecutiveErrorsRef = useRef(0);

  useEffect(() => {
    if (!notice) return;
    const timeout = setTimeout(() => setNotice(null), MESSAGE_HOLD_MS);
    return () => clearTimeout(timeout);
  }, [notice]);

  const showPartial = useCallback((text: string) => {
    setPartialTranscript(text);
    if (partialTimeoutRef.current !== null) clearTimeout(partialTimeoutRef.current);
    partialTimeoutRef.current = setTimeout(() => setPartialTranscript(null), MESSAGE_HOLD_MS);
  }, []);

  const handleCaptionUpdate = useCallback(
    (text: string) => {
      captionUpdatedAtRef.current = Date.now();
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

  const handleUtterance = useCallback(
    (utterance: string): boolean => {
      let effective = utterance;
      const phrase = activationPhrase.trim();
      if (phrase) {
        const index = utterance.toLowerCase().indexOf(phrase.toLowerCase());
        if (index === -1) return false;
        effective = utterance.slice(index + phrase.length).trim();
      }
      const matched = matchCommand(
        effective,
        commandsRef.current.filter((command) => command.language === sttLanguage),
      );
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
    const caption = captionTextRef.current.trim();
    const serverText = utteranceChunksRef.current.join(" ").trim();
    const text = caption || serverText;
    utteranceChunksRef.current = [];
    hasSpokenRef.current = false;
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
      // Gate on caption OR server chunks: VAD can return an empty chunk while the caption still has content.
      const hasPendingContent =
        utteranceChunksRef.current.length > 0 || captionTextRef.current.trim().length > 0;
      const captionSettled =
        !captionRef.current || now - captionUpdatedAtRef.current > CAPTION_SETTLE_MS;
      if (hasPendingContent && (ranTooLong || (wentQuiet && captionSettled))) {
        flushUtterance();
      }
    },
    onPartial: (chunkText) => {
      consecutiveErrorsRef.current = 0;
      const trimmed = chunkText.trim();
      if (trimmed) {
        if (utteranceChunksRef.current.length === 0) utteranceStartedAtRef.current = Date.now();
        utteranceChunksRef.current.push(trimmed);
      }
      if (!volumeMeterSupportedRef.current) {
        handleUtterance(chunkText);
        return;
      }
      if (!captionRef.current) {
        showPartial(utteranceChunksRef.current.join(" "));
      }
    },
    onFinal: () => {
      resetTranscriptUi();
      setIsListening(false);
    },
    onError: () => {
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
      } catch {}
    })();
  }, []);

  // Ref keeps this mount/unmount-only, since `live`/stopListening get a new identity almost every render.
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
    // Set synchronously so a second click before the async chain resolves is a no-op, not a race.
    startingRef.current = true;
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

export function useReadableText(text: string): void {
  const { registerReadableText, unregisterReadableText } = useSpeechMode();
  const id = useId();
  useEffect(() => {
    registerReadableText(id, text);
    return () => unregisterReadableText(id);
  }, [id, text, registerReadableText, unregisterReadableText]);
}
