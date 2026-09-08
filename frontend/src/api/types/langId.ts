export type LangIdMethod = "frequent_words" | "alphabetic" | "neural";

export const LANG_ID_METHODS: readonly LangIdMethod[] = ["frequent_words", "alphabetic", "neural"];

export const LANG_ID_METHOD_LABELS: Record<LangIdMethod, string> = {
  frequent_words: "Частотные слова",
  alphabetic: "Алфавитный",
  neural: "Нейросетевой",
};

export const LANG_ID_LANGUAGES: readonly { code: string; label: string }[] = [
  { code: "fr", label: "Французский" },
  { code: "en", label: "Английский" },
];

export interface LabelProgress {
  total: number;
  labeled: number;
  unlabeled: number;
  train_count: number;
  test_count: number;
}

export interface AutoSplitResult {
  train_assigned: number;
  test_assigned: number;
}

export interface LangIdProfile {
  id: number;
  method: LangIdMethod;
  language: string | null;
  source_document_count: number;
  source_char_count: number;
  built_at: string;
}

export interface IdentificationOutcome {
  method: LangIdMethod;
  predicted_language: string;
  distances: Record<string, number>;
  elapsed_ms: number;
}

export interface IdentifyResponse {
  results: IdentificationOutcome[];
}

export type LangIdJobStatus = "pending" | "running" | "completed" | "failed";

export const TERMINAL_LANG_ID_JOB_STATUSES: readonly LangIdJobStatus[] = ["completed", "failed"];

export interface LangIdTrainingJob {
  id: number;
  status: LangIdJobStatus;
  epochs_total: number;
  epochs_completed: number;
  current_loss: number | null;
  current_train_accuracy: number | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface LangIdRun {
  id: number;
  collection_id: number;
  method: LangIdMethod;
  status: LangIdJobStatus;
  documents_total: number;
  documents_processed: number;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface LangIdResult {
  id: number;
  run_id: number;
  document_id: number;
  predicted_language: string;
  distances: Record<string, number>;
  elapsed_ms: number;
  is_correct: boolean | null;
}

export interface LangIdRunSummary {
  run_id: number;
  method: LangIdMethod;
  documents_evaluated: number;
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  mean_elapsed_ms: number;
  confusion: Record<string, Record<string, number>>;
}

export interface LangIdCompareResponse {
  summaries: LangIdRunSummary[];
}
