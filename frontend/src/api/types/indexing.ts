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
