import { Mic } from "lucide-react";
import { useEffect, useRef } from "react";
import { CommandWaveOverlay } from "@/components/CommandWaveOverlay";
import { SoundWaveRing } from "@/components/SoundWaveRing";
import { Button } from "@/components/ui/button";
import { useSpeechMode } from "@/context/SpeechModeContext";
import { cn } from "@/lib/utils";

export function AssistantMicButton() {
  const { isListening, isSupported, notice, partialTranscript, commandFlashToken, toggle, getVolume } =
    useSpeechMode();
  const volumeRingRef = useRef<HTMLSpanElement>(null);

  // Volume ring is driven via direct style writes, not state, to avoid 60fps re-renders.
  useEffect(() => {
    if (!isListening) return;
    let rafId = 0;
    const tick = () => {
      const level = getVolume();
      const ring = volumeRingRef.current;
      if (ring) {
        ring.style.transform = `scale(${1 + level * 0.9})`;
        ring.style.opacity = String(0.2 + level * 0.6);
      }
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafId);
  }, [isListening, getVolume]);

  return (
    <>
      <CommandWaveOverlay trigger={commandFlashToken} />
      <div className="fixed right-4 bottom-4 z-50 flex items-center gap-2 sm:right-6 sm:bottom-6">
        {(notice || partialTranscript) && (
          <div className="flex flex-col items-end gap-2">
            {notice && (
              <div className="max-w-72 animate-in fade-in slide-in-from-left-4 rounded-xl border bg-card/95 px-3 py-2 text-xs text-muted-foreground shadow-lg backdrop-blur-md duration-200">
                {notice}
              </div>
            )}
            {partialTranscript && (
              <div className="max-w-72 animate-in fade-in slide-in-from-left-4 rounded-xl border bg-card/95 px-3 py-2 text-sm shadow-lg backdrop-blur-md duration-200">
                {partialTranscript}
              </div>
            )}
          </div>
        )}
        <div className="relative">
          {isListening && (
            <>
              <SoundWaveRing active={isListening} />
              <span
                ref={volumeRingRef}
                className="pointer-events-none absolute inset-0 rounded-full bg-primary/60 blur-sm transition-none"
                style={{ transform: "scale(1)", opacity: 0.2 }}
              />
            </>
          )}
          <Button
            type="button"
            size="icon"
            className="relative size-12 rounded-full shadow-lg"
            variant={isListening ? "default" : "secondary"}
            aria-label={isListening ? "Выключить голосовой режим" : "Включить голосовой режим"}
            title={
              isSupported
                ? "Голосовой режим: реагировать на команды в любой момент"
                : "Голосовой режим не поддерживается этим браузером"
            }
            onClick={toggle}
            disabled={!isSupported}
          >
            <Mic className={cn("size-5", isListening && "animate-pulse")} />
          </Button>
        </div>
      </div>
    </>
  );
}
