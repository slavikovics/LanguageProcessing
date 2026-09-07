import type { CrawlJob, CrawlJobProgress, CrawlSeed } from "../types";
import { request, webSocketUrl } from "./http";

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
  return webSocketUrl(`/crawl-jobs/ws/${id}`);
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
