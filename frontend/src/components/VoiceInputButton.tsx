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

  const live = useLiveSttStream({
    language: sttLanguage,
    autoStopOnSilence: true,
    silenceTimeoutMs: PHRASE_PAUSE_MS,
    matchCommands: detectCommands,
    onVolume: (level) => {
      volumeRef.current = level;
    },
    onPartial: (_chunkText, fullText) => {
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
