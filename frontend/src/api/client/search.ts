import type { QuerySummary, RelevanceJudgment, SearchModel, SearchResponse } from "../types";
import { request } from "./http";

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
