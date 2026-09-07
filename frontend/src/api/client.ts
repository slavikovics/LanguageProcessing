import type {
  AutoSplitResult,
  Collection,
  CollectionMetricsSummary,
  CrawlJob,
  CrawlJobProgress,
  CrawlSeed,
  DocumentDetail,
  DocumentSummary,
  IdentifyResponse,
  IndexJob,
  LabelProgress,
  LangIdCompareResponse,
  LangIdMethod,
  LangIdProfile,
  LangIdResult,
  LangIdRun,
  LangIdRunSummary,
  LangIdTrainingJob,
  MetricsCompareResponse,
  QueryMetrics,
  QuerySummary,
  RelevanceJudgment,
  SearchModel,
  SearchResponse,
} from "./types";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${detail}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function listCollections(): Promise<Collection[]> {
  return request<Collection[]>("/collections");
}

export function createCollection(input: { name: string; language: string }): Promise<Collection> {
  return request<Collection>("/collections", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function deleteCollection(collectionId: number): Promise<void> {
  return request<void>(`/collections/${collectionId}`, { method: "DELETE" });
}

export function listDocuments(
  collectionId: number,
  { limit = 50, offset = 0 }: { limit?: number; offset?: number } = {},
): Promise<DocumentSummary[]> {
  return request<DocumentSummary[]>(
    `/collections/${collectionId}/documents?limit=${limit}&offset=${offset}`,
  );
}

export interface DocumentInput {
  title: string;
  url: string | null;
  clean_text: string;
}

export function createDocument(collectionId: number, input: DocumentInput): Promise<DocumentDetail> {
  return request<DocumentDetail>(`/collections/${collectionId}/documents`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getDocument(id: number): Promise<DocumentDetail> {
  return request<DocumentDetail>(`/documents/${id}`);
}

export function updateDocument(id: number, input: DocumentInput): Promise<DocumentDetail> {
  return request<DocumentDetail>(`/documents/${id}`, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export function deleteDocument(id: number): Promise<void> {
  return request<void>(`/documents/${id}`, { method: "DELETE" });
}

export interface CreateCrawlJobInput {
  collection_id: number;
  seed_urls: string[];
  max_documents: number;
  max_depth: number;
}

export function createCrawlJob(input: CreateCrawlJobInput): Promise<CrawlJob> {
  return request<CrawlJob>("/crawl-jobs", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function listCrawlJobs(collectionId?: number): Promise<CrawlJob[]> {
  const query = collectionId !== undefined ? `?collection_id=${collectionId}` : "";
  return request<CrawlJob[]>(`/crawl-jobs${query}`);
}

export function getCrawlJob(id: number): Promise<CrawlJobProgress> {
  return request<CrawlJobProgress>(`/crawl-jobs/${id}`);
}

export function crawlJobWebSocketUrl(id: number): string {
  const wsBase = API_BASE_URL.replace(/^http/, "ws");
  return `${wsBase}/crawl-jobs/ws/${id}`;
}

export function refreshCollection(collectionId: number): Promise<CrawlJob> {
  return request<CrawlJob>(`/collections/${collectionId}/refresh`, { method: "POST" });
}

export function cancelCrawlJob(jobId: number): Promise<CrawlJob> {
  return request<CrawlJob>(`/crawl-jobs/${jobId}/cancel`, { method: "POST" });
}

export interface CrawlSeedInput {
  url: string;
  max_documents: number;
  max_depth: number;
  same_domain_only: boolean;
  language: string;
}

export function listCrawlSeeds(collectionId: number): Promise<CrawlSeed[]> {
  return request<CrawlSeed[]>(`/collections/${collectionId}/crawl-seeds`);
}

export function createCrawlSeed(collectionId: number, input: CrawlSeedInput): Promise<CrawlSeed> {
  return request<CrawlSeed>(`/collections/${collectionId}/crawl-seeds`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateCrawlSeed(seedId: number, input: CrawlSeedInput): Promise<CrawlSeed> {
  return request<CrawlSeed>(`/crawl-seeds/${seedId}`, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export function deleteCrawlSeed(seedId: number): Promise<void> {
  return request<void>(`/crawl-seeds/${seedId}`, { method: "DELETE" });
}

export function runCollectionCrawl(collectionId: number): Promise<CrawlJob[]> {
  return request<CrawlJob[]>(`/collections/${collectionId}/crawl-seeds/run`, { method: "POST" });
}

export function createIndexJob(collectionId: number): Promise<IndexJob> {
  return request<IndexJob>(`/collections/${collectionId}/index-jobs`, { method: "POST" });
}

export function getIndexJob(id: number): Promise<IndexJob> {
  return request<IndexJob>(`/index-jobs/${id}`);
}

export function getLatestIndexJob(collectionId: number): Promise<IndexJob | null> {
  return request<IndexJob | null>(`/collections/${collectionId}/index-jobs/latest`);
}

export function indexJobWebSocketUrl(id: number): string {
  const wsBase = API_BASE_URL.replace(/^http/, "ws");
  return `${wsBase}/index-jobs/ws/${id}`;
}

export function cancelIndexJob(jobId: number): Promise<IndexJob> {
  return request<IndexJob>(`/index-jobs/${jobId}/cancel`, { method: "POST" });
}

export interface SearchInput {
  collection_id: number;
  text: string;
  top_k?: number;
  model?: string;
}

export function search(input: SearchInput): Promise<SearchResponse> {
  return request<SearchResponse>("/search", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function listSearchModels(): Promise<SearchModel[]> {
  return request<SearchModel[]>("/search-models");
}

export function listCollectionQueries(collectionId: number): Promise<QuerySummary[]> {
  return request<QuerySummary[]>(`/collections/${collectionId}/queries`);
}

export function setJudgment(
  queryId: number,
  documentId: number,
  isRelevant: boolean,
): Promise<RelevanceJudgment> {
  return request<RelevanceJudgment>(`/queries/${queryId}/judgments/${documentId}`, {
    method: "PUT",
    body: JSON.stringify({ is_relevant: isRelevant }),
  });
}

export function clearJudgment(queryId: number, documentId: number): Promise<void> {
  return request<void>(`/queries/${queryId}/judgments/${documentId}`, { method: "DELETE" });
}

export function listJudgments(queryId: number): Promise<RelevanceJudgment[]> {
  return request<RelevanceJudgment[]>(`/queries/${queryId}/judgments`);
}

export function evaluateSearchRun(searchRunId: number): Promise<QueryMetrics> {
  return request<QueryMetrics>(`/search-runs/${searchRunId}/metrics`, { method: "POST" });
}

export function getCollectionMetricsSummary(
  collectionId: number,
  model = "tfidf",
): Promise<CollectionMetricsSummary> {
  return request<CollectionMetricsSummary>(
    `/collections/${collectionId}/metrics/summary?model=${encodeURIComponent(model)}`,
  );
}

export function getMetricsComparison(
  collectionId: number,
  modelKeys: string[] = [],
): Promise<MetricsCompareResponse> {
  const query = modelKeys.length > 0 ? `?models=${modelKeys.map(encodeURIComponent).join(",")}` : "";
  return request<MetricsCompareResponse>(`/collections/${collectionId}/metrics/compare${query}`);
}

/** Like getMetricsComparison, but re-executes every judged query against
 * every given model first (see POST .../metrics/rerun) — takes noticeably
 * longer since it's a real search per judged query per model, not just a
 * metrics recomputation over existing search_runs. */
// -- LR2: language identification -------------------------------------------

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
  const wsBase = API_BASE_URL.replace(/^http/, "ws");
  return `${wsBase}/lang-id/neural/train/ws/${jobId}`;
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
  const wsBase = API_BASE_URL.replace(/^http/, "ws");
  return `${wsBase}/lang-id/runs/ws/${id}`;
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

export function rerunMetricsComparison(
  collectionId: number,
  modelKeys: string[] = [],
): Promise<MetricsCompareResponse> {
  const query = modelKeys.length > 0 ? `?models=${modelKeys.map(encodeURIComponent).join(",")}` : "";
  return request<MetricsCompareResponse>(`/collections/${collectionId}/metrics/rerun${query}`, {
    method: "POST",
  });
}
