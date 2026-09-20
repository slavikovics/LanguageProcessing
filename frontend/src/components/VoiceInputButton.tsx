import { Loader2, Mic, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { listSpeechCommands } from "@/api/client";
import type { SpeechCommand } from "@/api/types";
import { SoundWaveRing } from "@/components/SoundWaveRing";
import { Button } from "@/components/ui/button";
import { useSpeechSettings } from "@/context/SpeechSettingsContext";
import { useLiveSttStream } from "@/hooks/useLiveSttStream";
import { startLiveTranscription } from "@/lib/liveSpeechRecognition";
import { matchCommand } from "@/lib/matchCommand";
import { isVolumeMeterSupported } from "@/lib/micVolumeMeter";
import {
  CAPTION_SETTLE_MS,
  MAX_UTTERANCE_MS,
  MESSAGE_HOLD_MS,
  REPEATED_ERROR_LIMIT,
  SILENCE_LEVEL_THRESHOLD,
  UTTERANCE_SILENCE_GAP_MS,
} from "@/lib/speechTiming";

type Status = "idle" | "recording" | "transcribing";

// Listens continuously until the user presses the button again; each pause in speech ends one utterance,
// which replaces the previous one via onTranscript (and fires onCommand when it matches a command).
export function VoiceInputButton({
  onTranscript,
  onCommand,
  size = "icon",
  detectCommands = true,
}: {
  onTranscript: (text: string) => void;
  onCommand?: (command: SpeechCommand, transcript: string) => void;
  size?: "icon" | "sm" | "default";
  detectCommands?: boolean;
}) {
  const { sttLanguage } = useSpeechSettings();
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const volumeRef = useRef(0);
  const volumeRingRef = useRef<HTMLSpanElement>(null);
  // Live caption (Web Speech API) takes priority over server transcript to avoid overwrite flicker.
  const captionRef = useRef<{ stop: () => void } | null>(null);
  const captionTextRef = useRef("");
  const captionUpdatedAtRef = useRef(0);
  const commandsRef = useRef<SpeechCommand[]>([]);
  const utteranceChunksRef = useRef<string[]>([]);
  const utteranceStartedAtRef = useRef(0);
  const lastLoudAtRef = useRef(0);
  const hasSpokenRef = useRef(false);
  const consecutiveErrorsRef = useRef(0);
  const volumeMeterSupportedRef = useRef(isVolumeMeterSupported());

  function startCaption() {
    captionRef.current = startLiveTranscription(sttLanguage, (text) => {
      captionUpdatedAtRef.current = Date.now();
      if (!captionTextRef.current.trim() && text.trim()) {
        utteranceStartedAtRef.current = Date.now();
      }
      captionTextRef.current = text;
      onTranscript(text);
    });
  }

  function stopCaption() {
    captionRef.current?.stop();
    captionRef.current = null;
    captionTextRef.current = "";
    captionUpdatedAtRef.current = 0;
  }

  function resetUtterance() {
    utteranceChunksRef.current = [];
    hasSpokenRef.current = false;
    captionTextRef.current = "";
    captionUpdatedAtRef.current = 0;
  }

  function emitUtterance(text: string) {
    onTranscript(text);
    if (!detectCommands) return;
    const matched = matchCommand(
      text,
      commandsRef.current.filter((command) => command.language === sttLanguage),
    );
    if (!matched) return;
    setNotice(`Команда распознана: «${matched.phrase}»`);
    onCommand?.(matched, text);
  }

  function flushUtterance() {
    const text = captionTextRef.current.trim() || utteranceChunksRef.current.join(" ").trim();
    resetUtterance();
    // Full restart (not offset tracking) avoids Chrome re-finalizing stale tail text into the next utterance.
    if (captionRef.current) {
      captionRef.current.stop();
      startCaption();
    }
    if (text) emitUtterance(text);
  }

  const live = useLiveSttStream({
    language: sttLanguage,
    matchCommands: false,
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
      if (!trimmed) return;
      if (!volumeMeterSupportedRef.current) {
        emitUtterance(trimmed);
        return;
      }
      if (utteranceChunksRef.current.length === 0) utteranceStartedAtRef.current = Date.now();
      utteranceChunksRef.current.push(trimmed);
      if (!captionRef.current) onTranscript(utteranceChunksRef.current.join(" "));
    },
    onFinal: () => {
      // User pressed stop: emit whatever was still pending when the recording ended.
      const text = captionTextRef.current.trim() || utteranceChunksRef.current.join(" ").trim();
      stopCaption();
      resetUtterance();
      if (text) emitUtterance(text);
      setStatus("idle");
    },
    onError: () => {
      // A single failed chunk is transient; only give up when the backend keeps failing.
      consecutiveErrorsRef.current += 1;
      if (consecutiveErrorsRef.current < REPEATED_ERROR_LIMIT) return;
      stopCaption();
      resetUtterance();
      live.stop();
      setError("Соединение с сервером распознавания речи потеряно. Попробуйте снова.");
      setStatus("idle");
    },
    onUnavailable: (reason) => {
      stopCaption();
      resetUtterance();
      setError(
        reason === "mic_denied"
          ? "Не удалось получить доступ к микрофону."
          : reason === "connection_lost"
            ? "Соединение для распознавания речи прервалось."
            : reason === "mic_lost"
              ? "Микрофон отключился во время записи."
              : "Живое распознавание недоступно в этом браузере.",
      );
      setStatus("idle");
    },
  });

  useEffect(() => {
    return () => {
      live.stop();
      captionRef.current?.stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Direct style writes, not React state — loudness updates faster than re-render budget.
  useEffect(() => {
    if (status !== "recording") {
      volumeRef.current = 0;
      return;
    }
    let rafId = 0;
    const tick = () => {
      const ring = volumeRingRef.current;
      if (ring) {
        const level = volumeRef.current;
        ring.style.transform = `scale(${1 + level * 0.9})`;
        ring.style.opacity = String(0.2 + level * 0.6);
      }
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafId);
  }, [status]);

  useEffect(() => {
    if (!notice) return;
    const timeout = setTimeout(() => setNotice(null), MESSAGE_HOLD_MS);
    return () => clearTimeout(timeout);
  }, [notice]);

  function handleClick() {
    if (status === "idle") {
      setError(null);
      setStatus("recording");
      resetUtterance();
      consecutiveErrorsRef.current = 0;
      lastLoudAtRef.current = Date.now();
      if (detectCommands) {
        void listSpeechCommands()
          .then((commands) => {
            commandsRef.current = commands;
          })
          .catch(() => {
            commandsRef.current = [];
          });
      }
      void live.start();
      startCaption();
    } else if (status === "recording") {
      setStatus("transcribing");
      live.stop();
    } else {
      setStatus("idle");
    }
  }

  const Icon = status === "transcribing" ? Loader2 : status === "recording" ? Square : Mic;

  return (
    <div className="inline-flex flex-col gap-1.5">
      <div className="relative inline-flex">
        {status === "recording" && (
          <>
            <SoundWaveRing active rounded="rounded-md" color="bg-destructive/40" />
            <span
              ref={volumeRingRef}
              className="pointer-events-none absolute inset-0 rounded-md bg-destructive/50 blur-sm transition-none"
              style={{ transform: "scale(1)", opacity: 0.2 }}
            />
          </>
        )}
        <Button
          type="button"
          variant={status === "recording" ? "secondary" : "outline"}
          size={size}
          className="relative"
          aria-label={status === "idle" ? "Голосовой ввод" : "Остановить запись"}
          onClick={handleClick}
        >
          <Icon
            className={
              status === "transcribing"
                ? "size-4 animate-spin"
                : status === "recording"
                  ? "size-4 text-destructive"
                  : "size-4"
            }
          />
        </Button>
      </div>
      {error && <span className="text-xs text-destructive">{error}</span>}
      {notice && (
        <div className="absolute mt-9 max-w-64 rounded-md border border-amber-600/30 bg-amber-600/5 px-3 py-2 text-xs dark:border-amber-400/30">
          {notice}
        </div>
      )}
    </div>
  );
}
