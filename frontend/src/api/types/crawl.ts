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
