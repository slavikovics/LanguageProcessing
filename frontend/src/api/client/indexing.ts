import type { IndexJob } from "../types";
import { request, webSocketUrl } from "./http";

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
  return webSocketUrl(`/index-jobs/ws/${id}`);
}

export function cancelIndexJob(jobId: number): Promise<IndexJob> {
  return request<IndexJob>(`/index-jobs/${jobId}/cancel`, { method: "POST" });
}
