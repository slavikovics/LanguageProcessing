import { useEffect, useState } from "react";

const WAVE_DURATION_MS = 1400;

export function CommandWaveOverlay({ trigger }: { trigger: number }) {
  const [playToken, setPlayToken] = useState<number | null>(null);

  useEffect(() => {
    if (trigger === 0) return;
    setPlayToken(trigger);
    const timeout = setTimeout(() => setPlayToken(null), WAVE_DURATION_MS);
    return () => clearTimeout(timeout);
  }, [trigger]);

  if (playToken === null) return null;

  return (
    <div className="pointer-events-none fixed inset-0 z-40 overflow-hidden" aria-hidden="true">
      <span
        key={playToken}
        // right-10/bottom-10 aligns this span's corner with the mic button's center; keep in sync with AssistantMicButton's position.
        className="animate-command-wave absolute right-10 bottom-10 size-12 rounded-full sm:right-12 sm:bottom-12"
        style={{
          background:
            "radial-gradient(circle, transparent 40%, rgba(16,185,129,0.45) 55%, transparent 72%)",
        }}
      />
    </div>
  );
}
