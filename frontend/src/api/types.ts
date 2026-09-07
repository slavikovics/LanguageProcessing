export interface Collection {
  id: number;
  name: string;
  language: string;
  created_at: string;
  document_count: number;
  documents_changed_at: string | null;
}

export interface DocumentSummary {
  id: number;
  collection_id: number;
  title: string;
  url: string | null;
  language: string;
  char_count: number;
  fetched_at: string;
  confirmed_language: string | null;
  corpus_split: "train" | "test" | null;
}

export interface DocumentDetail extends DocumentSummary {
  clean_text: string;
}

export type CrawlJobStatus = "pending" | "running" | "completed" | "failed" | "cancelled";
export type CrawlUrlStatus = "queued" | "fetching" | "success" | "failed" | "skipped" | "blocked";

export type CrawlJobMode = "crawl" | "refresh";

export interface CrawlJob {
  id: number;
  collection_id: number;
  seed_urls: string[];
  max_documents: number;
  max_depth: number;
  allowed_domain: string | null;
  mode: CrawlJobMode;
  status: CrawlJobStatus;
  documents_fetched: number;
  urls_queued: number;
  urls_visited: number;
  urls_failed: number;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface CrawlUrl {
  id: number;
  url: string;
  depth: number;
  status: CrawlUrlStatus;
  error: string | null;
}

export interface CrawlJobProgress {
  job: CrawlJob;
  recent_urls: CrawlUrl[];
}

export const TERMINAL_CRAWL_STATUSES: readonly CrawlJobStatus[] = [
  "completed",
  "failed",
  "cancelled",
];

export interface CrawlSeed {
  id: number;
  collection_id: number;
  url: string;
  max_documents: number;
  max_depth: number;
  same_domain_only: boolean;
  language: string;
  created_at: string;
}

export type IndexJobStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export interface IndexJob {
  id: number;
  collection_id: number;
  status: IndexJobStatus;
  documents_total: number;
  documents_processed: number;
  terms_indexed: number | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export const TERMINAL_INDEX_STATUSES: readonly IndexJobStatus[] = ["completed", "failed", "cancelled"];

export interface SearchModel {
  id: number;
  key: string;
  label: string;
  kind: "tfidf" | "dense_embedding";
  dimension: number | null;
}

export interface SearchHit {
  document_id: number;
  title: string;
  url: string | null;
  fetched_at: string;
  rank: number;
  score: number;
  snippet: string;
  matched_terms: string[];
}

export interface SearchResponse {
  query_id: number;
  search_run_id: number;
  query_text: string;
  model: string;
  model_label: string;
  hits: SearchHit[];
}

export interface QuerySummary {
  id: number;
  collection_id: number;
  text: string;
  created_at: string;
}

export interface RelevanceJudgment {
  document_id: number;
  is_relevant: boolean;
}

export type PrecisionRecallCurve = [number, number][];

export interface QueryMetrics {
  query_id: number;
  query_text: string;
  search_run_id: number;
  retrieved_count: number;
  relevant_count: number;
  precision_at_5: number;
  precision_at_10: number;
  recall_at_5: number;
  recall_at_10: number;
  f1_at_5: number;
  f1_at_10: number;
  average_precision: number;
  r_precision: number;
  curve: PrecisionRecallCurve;
}

export interface CollectionMetricsSummary {
  collection_id: number;
  model: string;
  model_label: string;
  map: number;
  mean_recall_at_5: number;
  mean_recall_at_10: number;
  mean_f1_at_5: number;
  mean_f1_at_10: number;
  mean_r_precision: number;
  mean_precision_at_5: number;
  mean_precision_at_10: number;
  queries: QueryMetrics[];
  curve: PrecisionRecallCurve;
  unscored_judged_queries: number;
}

export interface MetricsCompareResponse {
  summaries: CollectionMetricsSummary[];
}

// -- LR2: language identification -------------------------------------------

export type LangIdMethod = "frequent_words" | "alphabetic" | "neural";

export const LANG_ID_METHODS: readonly LangIdMethod[] = ["frequent_words", "alphabetic", "neural"];

export const LANG_ID_METHOD_LABELS: Record<LangIdMethod, string> = {
  frequent_words: "Частотные слова",
  alphabetic: "Алфавитный",
  neural: "Нейросетевой",
};

// Variant 25: French/English — hardcoded rather than a generic per-project
// language config, since this module's whole assignment is these two.
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
