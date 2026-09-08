import type { CollectionMetricsSummary, MetricsCompareResponse, QueryMetrics } from "../types";
import { request } from "./http";

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

export function getMetricsComparison(collectionId: number, modelKeys: string[] = []): Promise<MetricsCompareResponse> {
  const query = modelKeys.length > 0 ? `?models=${modelKeys.map(encodeURIComponent).join(",")}` : "";
  return request<MetricsCompareResponse>(`/collections/${collectionId}/metrics/compare${query}`);
}

export function rerunMetricsComparison(collectionId: number, modelKeys: string[] = []): Promise<MetricsCompareResponse> {
  const query = modelKeys.length > 0 ? `?models=${modelKeys.map(encodeURIComponent).join(",")}` : "";
  return request<MetricsCompareResponse>(`/collections/${collectionId}/metrics/rerun${query}`, {
    method: "POST",
  });
}
