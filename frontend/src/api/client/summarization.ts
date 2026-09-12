import type {
  DocumentSummaryRecord,
  PolishSummaryResponse,
  SummarizationCompareResponse,
  SummarizationMethod,
  SummarizationRun,
  SummarizationRunSummary,
  SummarizeDocumentResponse,
} from "../types";
import { request, webSocketUrl } from "./http";

export function summarizeDocument(
  documentId: number,
  { methods, sentenceCount = 10 }: { methods?: SummarizationMethod[]; sentenceCount?: number } = {},
): Promise<SummarizeDocumentResponse> {
  return request<SummarizeDocumentResponse>(`/documents/${documentId}/summarize`, {
    method: "POST",
    body: JSON.stringify({ methods, sentence_count: sentenceCount }),
  });
}

export function listDocumentSummaries(documentId: number): Promise<DocumentSummaryRecord[]> {
  return request<DocumentSummaryRecord[]>(`/documents/${documentId}/summaries`);
}

export function polishSummary(
  summaryId: number,
  language?: string | null,
): Promise<PolishSummaryResponse> {
  return request<PolishSummaryResponse>(`/summaries/${summaryId}/polish`, {
    method: "POST",
    body: JSON.stringify({ language: language ?? null }),
  });
}

export function createSummarizationRuns(
  collectionId: number,
  methods: SummarizationMethod[],
): Promise<SummarizationRun[]> {
  return request<SummarizationRun[]>("/summarization/runs", {
    method: "POST",
    body: JSON.stringify({ collection_id: collectionId, methods }),
  });
}

export function getSummarizationRun(id: number): Promise<SummarizationRun> {
  return request<SummarizationRun>(`/summarization/runs/${id}`);
}

export function cancelSummarizationRun(id: number): Promise<SummarizationRun> {
  return request<SummarizationRun>(`/summarization/runs/${id}/cancel`, { method: "POST" });
}

export function listSummarizationRuns(collectionId: number): Promise<SummarizationRun[]> {
  return request<SummarizationRun[]>(`/collections/${collectionId}/summarization/runs`);
}

export function summarizationRunWebSocketUrl(id: number): string {
  return webSocketUrl(`/summarization/runs/ws/${id}`);
}

export function getSummarizationRunResults(runId: number): Promise<DocumentSummaryRecord[]> {
  return request<DocumentSummaryRecord[]>(`/summarization/runs/${runId}/results`);
}

export function getSummarizationRunSummary(runId: number): Promise<SummarizationRunSummary> {
  return request<SummarizationRunSummary>(`/summarization/runs/${runId}/summary`);
}

export function compareSummarizationMethods(
  collectionId: number,
  methods: SummarizationMethod[],
): Promise<SummarizationCompareResponse> {
  return request<SummarizationCompareResponse>(
    `/summarization/compare?collection_id=${collectionId}&methods=${methods
      .map(encodeURIComponent)
      .join(",")}`,
  );
}
