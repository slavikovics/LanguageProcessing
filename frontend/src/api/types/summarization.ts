export type SummarizationMethod = "algorithmic" | "textrank" | "embeddings";

export const SUMMARIZATION_METHODS: readonly SummarizationMethod[] = [
  "algorithmic",
  "textrank",
  "embeddings",
];

export const SUMMARIZATION_METHOD_LABELS: Record<SummarizationMethod, string> = {
  algorithmic: "Алгоритм (TF-IDF + позиция)",
  textrank: "TextRank",
  embeddings: "Эмбеддинги",
};

export interface SelectedSentence {
  index: number;
  text: string;
  weight: number;
}

export interface SummaryOutcome {
  method: SummarizationMethod;
  sentences: SelectedSentence[];
  total_sentences: number;
  elapsed_ms: number;
  compression_ratio: number;
}

export interface KeywordGroup {
  term: string;
  children: string[];
}

export interface SummarizeDocumentResponse {
  document_id: number;
  keywords: KeywordGroup[];
  results: SummaryOutcome[];
}

export interface DocumentSummaryRecord {
  id: number;
  run_id: number | null;
  document_id: number;
  method: SummarizationMethod;
  sentence_count: number;
  summary_text: string;
  summary_sentence_indices: number[];
  total_sentences: number;
  elapsed_ms: number;
  created_at: string;
}

export interface PolishSummaryResponse {
  document_summary_id: number;
  model: string;
  polished_markdown: string;
}

export type SummarizationJobStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export const TERMINAL_SUMMARIZATION_JOB_STATUSES: readonly SummarizationJobStatus[] = [
  "completed",
  "failed",
  "cancelled",
];

export interface SummarizationRun {
  id: number;
  collection_id: number;
  method: SummarizationMethod;
  status: SummarizationJobStatus;
  documents_total: number;
  documents_processed: number;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface SummarizationRunSummary {
  run_id: number;
  method: SummarizationMethod;
  documents_summarized: number;
  mean_elapsed_ms: number;
  mean_compression_ratio: number;
  mean_sentence_count: number;
}

export interface SummarizationCompareResponse {
  summaries: SummarizationRunSummary[];
}
