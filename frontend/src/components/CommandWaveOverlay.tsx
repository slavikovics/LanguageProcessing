import { useEffect, useState } from "react";

/** Roughly one cycle of the command-wave keyframe (index.css) — long enough
 * to visibly sweep across a full-height page, short enough to read as one
 * confirming pulse rather than a lingering effect. */
const WAVE_DURATION_MS = 1400;

/**
 * A single green ripple that launches from the assistant mic button (bottom
 * right, same corner as AssistantMicButton) and expands until it's swept
 * across the whole page — "a command just fired," readable no matter where
 * on the page the user is looking, unlike a ring confined to the mic button
 * itself which is easy to miss once you've looked away from that corner.
 *
 * `trigger` is SpeechModeContext's commandFlashToken: it increments on every
 * match, so using it as the ripple's `key` retriggers the CSS animation from
 * scratch even for back-to-back matches before the previous ripple finished.
 */
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
        // right-10/bottom-10 (sm:12/12) place this span's own un-transformed
        // bottom-right corner exactly at the mic button's center (mic sits
        // at right-4/bottom-4 sm:6/6 with a 48px/size-12 footprint, so its
        // center is inset by a further half of that, 24px/1.5rem) — combined
        // with the keyframe's constant translate(50%, 50%), the visible
        // ring's center lands on and stays at that same point.
        className="animate-command-wave absolute right-10 bottom-10 size-12 rounded-full sm:right-12 sm:bottom-12"
        style={{
          background:
            "radial-gradient(circle, transparent 40%, rgba(16,185,129,0.45) 55%, transparent 72%)",
        }}
      />
    </div>
  );
}
