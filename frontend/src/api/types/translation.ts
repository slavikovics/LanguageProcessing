export type TranslationMethod = "direct" | "transfer" | "neural";

export const TRANSLATION_METHOD_LABELS: Record<TranslationMethod, string> = {
  direct: "Прямой (пословный)",
  transfer: "Трансферный (с учётом синтаксиса)",
  neural: "Нейросетевой (MarianMT)",
};

export interface DiffSegment {
  text: string;
  changed: boolean;
}

export interface TranslationRun {
  id: number;
  document_id: number | null;
  collection_id: number | null;
  test_run_id: number | null;
  source_lang: string;
  target_lang: string;
  method: TranslationMethod;
  source_text: string;
  translated_text: string;
  word_count: number;
  translated_word_count: number;
  translated_text_word_count: number;
  elapsed_ms: number;
  diff_segments: DiffSegment[] | null;
  created_at: string;
}

export type TranslationTestRunStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export const TERMINAL_TRANSLATION_TEST_RUN_STATUSES: readonly TranslationTestRunStatus[] = [
  "completed",
  "failed",
  "cancelled",
];

export interface TranslationTestRun {
  id: number;
  collection_id: number;
  source_lang: string;
  target_lang: string;
  method: TranslationMethod;
  status: TranslationTestRunStatus;
  documents_total: number;
  documents_processed: number;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface TranslationRunSummary {
  run_id: number;
  source_lang: string;
  target_lang: string;
  method: TranslationMethod;
  documents_translated: number;
  mean_elapsed_ms: number;
  mean_word_count: number;
  mean_translated_word_count: number;
  mean_translated_text_word_count: number;
  mean_coverage_ratio: number;
}

export interface TranslationRunWord {
  rank: number;
  lemma: string;
  surface: string;
  pos: string;
  frequency: number;
  translation: string | null;
}

export interface SyntaxToken {
  position: number;
  text: string;
  lemma: string;
  pos: string;
  dep: string;
  head_position: number | null;
  head_text: string | null;
  morph: Record<string, string>;
  is_punct: boolean;
}

export interface TranslationDictionaryEntry {
  id: number;
  source_lang: string;
  target_lang: string;
  source_lemma: string;
  pos: string | null;
  target_text: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface TranslationDictionaryPage {
  items: TranslationDictionaryEntry[];
  total: number;
}

export interface TranslationDictionaryEntryInput {
  source_lang?: string;
  target_lang?: string;
  source_lemma: string;
  pos?: string | null;
  target_text: string;
  notes?: string | null;
}

export const DEFAULT_SOURCE_LANGUAGE = "en";
export const DEFAULT_TARGET_LANGUAGE = "fr";
