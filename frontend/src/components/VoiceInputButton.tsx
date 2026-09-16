import { Loader2, Mic, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { SpeechCommand } from "@/api/types";
import { SoundWaveRing } from "@/components/SoundWaveRing";
import { Button } from "@/components/ui/button";
import { useSpeechSettings } from "@/context/SpeechSettingsContext";
import { useLiveSttStream } from "@/hooks/useLiveSttStream";
import { startLiveTranscription } from "@/lib/liveSpeechRecognition";
import { MESSAGE_HOLD_MS, PHRASE_PAUSE_MS } from "@/lib/speechTiming";

type Status = "idle" | "recording" | "transcribing";

export function VoiceInputButton({
  onTranscript,
  onCommand,
  size = "icon",
  detectCommands = true,
}: {
  onTranscript: (text: string) => void;
  onCommand?: (command: SpeechCommand, transcript: string) => void;
  size?: "icon" | "sm" | "default";
  /** Set false for a widget that only wants plain recognized text back
   * (e.g. Settings' STT accuracy preview) — the server skips matching the
   * transcript against speech_commands entirely, and no "Команда
   * распознана" notice or onCommand call can fire. */
  detectCommands?: boolean;
}) {
  const { sttLanguage } = useSpeechSettings();
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const volumeRef = useRef(0);
  const volumeRingRef = useRef<HTMLSpanElement>(null);
  // Best-effort *live* caption while recording, via the browser's Web Speech
  // API (see liveSpeechRecognition.ts) — words appear as they're spoken, far
  // more often and (in practice) more accurately than faster-whisper's
  // ~3.5s-chunked "stream" model, which decodes each chunk mostly without
  // context and lags real time by up to one chunk. When a caption is
  // running it's treated as authoritative for what ends up in the box (see
  // onPartial/onFinal below) — previously the server's per-chunk fullText
  // unconditionally overwrote it every ~3.5s and again on stop, which is
  // what caused a good live caption to flicker to a worse transcript
  // mid-recording and to visibly lose its last few words at the end (the
  // final chunk hadn't been decoded yet, so the server's fullText briefly
  // lagged what was already on screen, then the missing tail popped in
  // separately once that chunk's transcription arrived). The server
  // transcript is still what's actually sent to the backend for command
  // matching (matchedCommand below) and is the only source used when no
  // caption is available at all (e.g. Firefox).
  const captionRef = useRef<{ stop: () => void } | null>(null);
  const captionTextRef = useRef("");

  const live = useLiveSttStream({
    language: sttLanguage,
    autoStopOnSilence: true,
    silenceTimeoutMs: PHRASE_PAUSE_MS,
    matchCommands: detectCommands,
    onVolume: (level) => {
      volumeRef.current = level;
    },
    onPartial: (_chunkText, fullText) => {
      // Only the fallback path (no live caption) drives the box from here —
      // otherwise the caption's own onUpdate already does, and letting this
      // fire too is exactly the periodic-overwrite race described above.
      if (!captionRef.current) onTranscript(fullText);
    },
    onFinal: (fullText, matchedCommand) => {
      captionRef.current?.stop();
      captionRef.current = null;
      const finalText = captionTextRef.current.trim() || fullText;
      captionTextRef.current = "";
      onTranscript(finalText);
      if (detectCommands && matchedCommand) {
        setNotice(`Команда распознана: «${matchedCommand.phrase}»`);
        onCommand?.(matchedCommand, finalText);
      }
      setStatus("idle");
    },
    onError: (detail) => setNotice(`Не удалось распознать фрагмент речи: ${detail}`),
    onUnavailable: (reason) => {
      captionRef.current?.stop();
      captionRef.current = null;
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

  // Drives the volume ring directly via style writes each frame rather than
  // React state — same rationale as AssistantMicButton's ring: loudness
  // changes far faster than a sane re-render budget.
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
      captionTextRef.current = "";
      void live.start();
      captionRef.current = startLiveTranscription(sttLanguage, (text) => {
        captionTextRef.current = text;
        onTranscript(text);
      });
    } else if (status === "recording") {
      setStatus("transcribing");
      live.stop();
    } else {
      // Already waiting on the server's final transcript for this
      // recording (auto-stopped on silence or user re-clicked) — nothing
      // in flight that can be cancelled, just stop showing "transcribing".
      setStatus("idle");
    }
  }

  const Icon = status === "transcribing" ? Loader2 : status === "recording" ? Square : Mic;

  return (
    <div className="inline-flex flex-col gap-1.5">
      <div className="relative inline-flex">
        {status === "recording" && (
          <>
            {/* Sound-wave ripple: "recording is on", independent of volume. */}
            <SoundWaveRing active rounded="rounded-md" color="bg-destructive/40" />
            {/* Volume ring: scales/brightens with live mic loudness. */}
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
