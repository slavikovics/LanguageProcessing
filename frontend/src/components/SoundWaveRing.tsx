import { cn } from "@/lib/utils";

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
