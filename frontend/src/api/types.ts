export interface Collection {
  id: number;
  name: string;
  language: string;
  created_at: string;
}

export interface DocumentSummary {
  id: number;
  collection_id: number;
  title: string;
  url: string;
  language: string;
  char_count: number;
  fetched_at: string;
}

export type CrawlJobStatus = "pending" | "running" | "completed" | "failed" | "cancelled";
export type CrawlUrlStatus = "queued" | "fetching" | "success" | "failed" | "skipped";

export interface CrawlJob {
  id: number;
  collection_id: number;
  seed_urls: string[];
  max_documents: number;
  max_depth: number;
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
