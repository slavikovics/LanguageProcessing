import type { Collection } from "../types";
import { request } from "./http";

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
