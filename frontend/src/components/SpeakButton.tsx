import { Loader2, Square, Volume2 } from "lucide-react";
import { type ComponentProps } from "react";
import { SoundWaveRing } from "@/components/SoundWaveRing";
import { Button } from "@/components/ui/button";
import { useSpeechPlayback } from "@/context/SpeechPlaybackContext";
import { cn } from "@/lib/utils";

export function SpeakButton({
  text,
  className,
  size = "icon",
  variant = "outline",
}: {
  text: string;
  className?: string;
  size?: ComponentProps<typeof Button>["size"];
  variant?: ComponentProps<typeof Button>["variant"];
}) {
  const { status, activeText, error, errorText, speak, stop } = useSpeechPlayback();
  const isThis = activeText === text;
  const displayStatus = isThis ? status : "idle";
  const isPlaying = displayStatus === "playing";
  const isRequesting = displayStatus === "requesting";

  function handleClick() {
    if (isThis && status !== "idle") {
      stop();
    } else {
      speak(text);
    }
  }

  const Icon = isRequesting ? Loader2 : isPlaying ? Square : Volume2;

  return (
    <div className="inline-flex items-center gap-2">
      <div className="relative inline-flex">
        <SoundWaveRing active={isPlaying} rounded="rounded-md" />
        <Button
          type="button"
          variant={isPlaying ? "default" : variant}
          size={size}
          aria-label={displayStatus === "idle" ? "Озвучить текст" : "Остановить озвучивание"}
          onClick={handleClick}
          disabled={!text.trim()}
          className={cn("relative transition-colors", className)}
        >
          <Icon className={cn("size-4", isRequesting && "animate-spin", isPlaying && "animate-pulse")} />
          {!size?.startsWith("icon") && (displayStatus === "idle" ? "Озвучить" : "Остановить")}
        </Button>
      </div>
      {error && errorText === text && <span className="text-xs text-destructive">{error}</span>}
    </div>
  );
}
