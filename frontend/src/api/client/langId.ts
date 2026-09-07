import type {
  AutoSplitResult,
  DocumentSummary,
  IdentifyResponse,
  LabelProgress,
  LangIdCompareResponse,
  LangIdMethod,
  LangIdProfile,
  LangIdResult,
  LangIdRun,
  LangIdRunSummary,
  LangIdTrainingJob,
} from "../types";
import { request, webSocketUrl } from "./http";

export function listUnlabeledDocuments(
  collectionId: number,
  { limit = 20, offset = 0 }: { limit?: number; offset?: number } = {},
): Promise<DocumentSummary[]> {
  return request<DocumentSummary[]>(
    `/collections/${collectionId}/lang-id/unlabeled-documents?limit=${limit}&offset=${offset}`,
  );
}

export function getLabelProgress(collectionId: number): Promise<LabelProgress> {
  return request<LabelProgress>(`/collections/${collectionId}/lang-id/label-progress`);
}

export function setLanguageLabel(
  documentId: number,
  input: { confirmed_language: string | null; corpus_split: "train" | "test" | null },
): Promise<DocumentSummary> {
  return request<DocumentSummary>(`/documents/${documentId}/language-label`, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

/** Stratified per-language bulk train/test split for every confirmed
 * document that doesn't have one yet (see LanguageIdentificationService.auto_split) —
 * the one-click alternative to labeling each document's split by hand. */
export function autoSplitTrainTest(collectionId: number, testRatio = 0.2): Promise<AutoSplitResult> {
  return request<AutoSplitResult>(
    `/collections/${collectionId}/lang-id/auto-split?test_ratio=${testRatio}`,
    { method: "POST" },
  );
}

export function listLangIdProfiles(): Promise<LangIdProfile[]> {
  return request<LangIdProfile[]>("/lang-id/profiles");
}

export function buildFrequentWordsProfile(language: string): Promise<LangIdProfile> {
  return request<LangIdProfile>("/lang-id/profiles/frequent-words", {
    method: "POST",
    body: JSON.stringify({ language }),
  });
}

export function buildAlphabeticProfile(language: string): Promise<LangIdProfile> {
  return request<LangIdProfile>("/lang-id/profiles/alphabetic", {
    method: "POST",
    body: JSON.stringify({ language }),
  });
}

export function trainNeuralProfile(): Promise<LangIdTrainingJob> {
  return request<LangIdTrainingJob>("/lang-id/neural/train", { method: "POST" });
}

export function getNeuralTrainingJob(jobId: number): Promise<LangIdTrainingJob> {
  return request<LangIdTrainingJob>(`/lang-id/neural/train/${jobId}`);
}

export function getLatestNeuralTrainingJob(): Promise<LangIdTrainingJob | null> {
  return request<LangIdTrainingJob | null>("/lang-id/neural/train/latest");
}

export function langIdTrainingWebSocketUrl(jobId: number): string {
  return webSocketUrl(`/lang-id/neural/train/ws/${jobId}`);
}

export function identifyDocument(documentId: number, methods?: LangIdMethod[]): Promise<IdentifyResponse> {
  return request<IdentifyResponse>("/lang-id/identify", {
    method: "POST",
    body: JSON.stringify({ document_id: documentId, methods }),
  });
}

export function identifyUrl(url: string, methods?: LangIdMethod[]): Promise<IdentifyResponse> {
  return request<IdentifyResponse>("/lang-id/identify-url", {
    method: "POST",
    body: JSON.stringify({ url, methods }),
  });
}

export function identifyText(
  text: string,
  { isHtml = false, methods }: { isHtml?: boolean; methods?: LangIdMethod[] } = {},
): Promise<IdentifyResponse> {
  return request<IdentifyResponse>("/lang-id/identify-text", {
    method: "POST",
    body: JSON.stringify({ text, is_html: isHtml, methods }),
  });
}

export function createLangIdRuns(collectionId: number, methods: LangIdMethod[]): Promise<LangIdRun[]> {
  return request<LangIdRun[]>("/lang-id/runs", {
    method: "POST",
    body: JSON.stringify({ collection_id: collectionId, methods }),
  });
}

export function getLangIdRun(id: number): Promise<LangIdRun> {
  return request<LangIdRun>(`/lang-id/runs/${id}`);
}

export function listLangIdRuns(collectionId: number): Promise<LangIdRun[]> {
  return request<LangIdRun[]>(`/collections/${collectionId}/lang-id/runs`);
}

export function langIdRunWebSocketUrl(id: number): string {
  return webSocketUrl(`/lang-id/runs/ws/${id}`);
}

export function listLangIdResults(runId: number): Promise<LangIdResult[]> {
  return request<LangIdResult[]>(`/lang-id/runs/${runId}/results`);
}

export function getLangIdRunSummary(runId: number): Promise<LangIdRunSummary> {
  return request<LangIdRunSummary>(`/lang-id/runs/${runId}/summary`);
}

export function compareLangIdMethods(
  collectionId: number,
  methods: LangIdMethod[],
): Promise<LangIdCompareResponse> {
  return request<LangIdCompareResponse>(
    `/lang-id/compare?collection_id=${collectionId}&methods=${methods.map(encodeURIComponent).join(",")}`,
  );
}

/** Like compareLangIdMethods, but runs fresh classification passes for
 * every method first (real test-collection runs, slower) instead of
 * reading each method's latest already-completed run. */
export function rerunLangIdComparison(
  collectionId: number,
  methods: LangIdMethod[],
): Promise<LangIdCompareResponse> {
  return request<LangIdCompareResponse>("/lang-id/rerun", {
    method: "POST",
    body: JSON.stringify({ collection_id: collectionId, methods }),
  });
}
