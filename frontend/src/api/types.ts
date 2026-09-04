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
}

export interface DocumentDetail extends DocumentSummary {
  clean_text: string;
}

export type CrawlJobStatus = "pending" | "running" | "completed" | "failed" | "cancelled";
export type CrawlUrlStatus = "queued" | "fetching" | "success" | "failed" | "skipped";

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
  created_at: string;
}

export type IndexJobStatus = "pending" | "running" | "completed" | "failed";

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

export const TERMINAL_INDEX_STATUSES: readonly IndexJobStatus[] = ["completed", "failed"];

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
  precision: number;
  recall: number;
  f1: number;
  precision_at_5: number;
  precision_at_10: number;
  average_precision: number;
  r_precision: number;
  curve: PrecisionRecallCurve;
}

export interface CollectionMetricsSummary {
  collection_id: number;
  map: number;
  micro_precision: number;
  micro_recall: number;
  micro_f1: number;
  queries: QueryMetrics[];
  curve: PrecisionRecallCurve;
}
