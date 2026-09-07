import type { DocumentDetail, DocumentSummary } from "../types";
import { request } from "./http";

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
