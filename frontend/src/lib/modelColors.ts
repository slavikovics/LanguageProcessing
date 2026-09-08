const PALETTE = [
  "#2563eb",
  "#ea580c",
  "#059669",
  "#7c3aed",
  "#dc2626",
  "#0891b2",
];

const assigned = new Map<string, string>();

export function colorForModel(key: string): string {
  const existing = assigned.get(key);
  if (existing) return existing;
  const color = PALETTE[assigned.size % PALETTE.length];
  assigned.set(key, color);
  return color;
}
