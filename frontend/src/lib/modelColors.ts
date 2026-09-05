/** Consistent per-model color across every chart/legend/badge on the
 * Metrics page — keyed by model `key` so the color stays stable regardless
 * of fetch order, and a model with no explicit assignment still gets a
 * distinct, deterministic color from the shared palette (so a 3rd/4th
 * future model just works). Chosen to read reasonably on both light and
 * dark backgrounds (mid-saturation Tailwind "500" shades). */
const PALETTE = [
  "#2563eb", // blue
  "#ea580c", // orange
  "#059669", // emerald
  "#7c3aed", // violet
  "#dc2626", // red
  "#0891b2", // cyan
];

const assigned = new Map<string, string>();

export function colorForModel(key: string): string {
  const existing = assigned.get(key);
  if (existing) return existing;
  const color = PALETTE[assigned.size % PALETTE.length];
  assigned.set(key, color);
  return color;
}
