import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Clamps a number input's draft value on blur. Draft state should be typed
 * as `number | ""` (empty while the field is fully cleared) so a controlled
 * <input type="number"> can actually render as empty instead of snapping
 * back to a stale numeric value on every keystroke — the empty case here
 * falls back to `min` rather than staying blank.
 */
export function clampNumberInput(value: number | "", min: number, max: number): number {
  const n = value === "" ? min : value;
  return Math.min(max, Math.max(min, n));
}
