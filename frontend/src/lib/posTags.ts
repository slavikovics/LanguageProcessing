export const POS_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  NOUN: { bg: "#3b82f620", text: "#3b82f6", border: "#3b82f6" },
  PROPN: { bg: "#3b82f620", text: "#3b82f6", border: "#3b82f6" },
  VERB: { bg: "#ef444420", text: "#ef4444", border: "#ef4444" },
  AUX: { bg: "#f4717120", text: "#f47171", border: "#f47171" },
  ADJ: { bg: "#10b98120", text: "#10b981", border: "#10b981" },
  ADV: { bg: "#f59e0b20", text: "#f59e0b", border: "#f59e0b" },
  ADP: { bg: "#8b5cf620", text: "#8b5cf6", border: "#8b5cf6" },
  PRON: { bg: "#ec489920", text: "#ec4899", border: "#ec4899" },
  DET: { bg: "#06b6d420", text: "#06b6d4", border: "#06b6d4" },
  CONJ: { bg: "#f9731620", text: "#f97316", border: "#f97316" },
  CCONJ: { bg: "#f9731620", text: "#f97316", border: "#f97316" },
  SCONJ: { bg: "#f9731620", text: "#f97316", border: "#f97316" },
  NUM: { bg: "#84cc1620", text: "#84cc16", border: "#84cc16" },
  PART: { bg: "#a855f720", text: "#a855f7", border: "#a855f7" },
  INTJ: { bg: "#d946ef20", text: "#d946ef", border: "#d946ef" },
  PUNCT: { bg: "#6b728020", text: "#6b7280", border: "#6b7280" },
  SYM: { bg: "#6b728020", text: "#6b7280", border: "#6b7280" },
  X: { bg: "#6b728020", text: "#6b7280", border: "#6b7280" },
  default: { bg: "#9ca3af20", text: "#9ca3af", border: "#9ca3af" },
};

export const DEP_COLORS: Record<string, string> = {
  nsubj: "#3b82f6",
  nsubjpass: "#3b82f6",
  csubj: "#3b82f6",
  csubjpass: "#3b82f6",
  dobj: "#10b981",
  dative: "#10b981",
  oprd: "#10b981",
  pobj: "#10b981",
  attr: "#10b981",
  advmod: "#f59e0b",
  advcl: "#f59e0b",
  npadvmod: "#f59e0b",
  quantmod: "#f59e0b",
  agent: "#f59e0b",
  amod: "#8b5cf6",
  nmod: "#8b5cf6",
  nummod: "#8b5cf6",
  appos: "#8b5cf6",
  relcl: "#8b5cf6",
  acomp: "#8b5cf6",
  compound: "#8b5cf6",
  acl: "#a78bfa",
  ccomp: "#a78bfa",
  xcomp: "#a78bfa",
  parataxis: "#a78bfa",
  det: "#ec4899",
  predet: "#ec4899",
  preconj: "#ec4899",
  poss: "#ec4899",
  case: "#6b7280",
  prep: "#6b7280",
  pcomp: "#6b7280",
  mark: "#6b7280",
  aux: "#14b8a6",
  auxpass: "#14b8a6",
  conj: "#ef4444",
  cc: "#ef4444",
  ROOT: "#f59e0b",
  punct: "#9ca3af",
  dep: "#9ca3af",
  intj: "#f97316",
  expl: "#a855f7",
  neg: "#ef4444",
  meta: "#6b7280",
  prt: "#6b7280",
};

export function getPosStyle(pos: string | null) {
  if (!pos) return POS_COLORS.default;
  return POS_COLORS[pos] ?? POS_COLORS.default;
}

export function getDepColor(dep: string | null): string {
  if (!dep) return "#9ca3af";
  return DEP_COLORS[dep] ?? "#9ca3af";
}

export function getDepLabel(dep: string | null): string {
  if (!dep) return "неизвестно";
  return dep;
}
