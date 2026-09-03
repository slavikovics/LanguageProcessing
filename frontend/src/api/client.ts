import type { Collection, CrawlJob, CrawlJobProgress, DocumentSummary } from "./types";

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

export function listDocuments(collectionId: number): Promise<DocumentSummary[]> {
  return request<DocumentSummary[]>(`/collections/${collectionId}/documents`);
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

export function listCrawlJobs(): Promise<CrawlJob[]> {
  return request<CrawlJob[]>("/crawl-jobs");
}

export function getCrawlJob(id: number): Promise<CrawlJobProgress> {
  return request<CrawlJobProgress>(`/crawl-jobs/${id}`);
}

export function crawlJobWebSocketUrl(id: number): string {
  const wsBase = API_BASE_URL.replace(/^http/, "ws");
  return `${wsBase}/crawl-jobs/ws/${id}`;
}
