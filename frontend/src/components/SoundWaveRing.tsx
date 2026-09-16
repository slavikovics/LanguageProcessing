import { cn } from "@/lib/utils";

/**
 * Concentric ripples that imitate a sound wave radiating outward from a
 * button. Shared by every "audio is active" indicator in the app — the
 * assistant mic, voice input recording, and TTS playback — so they all read
 * the same way no matter the button shape underneath (`rounded` lets a
 * square icon button still emit circular ripples, or match its own corners).
 */
export function SoundWaveRing({
  active,
  color = "bg-primary/40",
  rounded = "rounded-full",
  className,
}: {
  active: boolean;
  color?: string;
  rounded?: string;
  className?: string;
}) {
  if (!active) return null;
  return (
    <span className={cn("pointer-events-none absolute inset-0", className)} aria-hidden="true">
      {[0, 0.5, 1].map((delay) => (
        <span
          key={delay}
          className={cn("absolute inset-0 animate-sound-wave", rounded, color)}
          style={{ animationDelay: `${delay}s` }}
        />
      ))}
    </span>
  );
}
