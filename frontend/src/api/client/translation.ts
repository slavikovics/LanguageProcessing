import type {
  SyntaxToken,
  TranslationDictionaryEntry,
  TranslationDictionaryEntryInput,
  TranslationDictionaryPage,
  TranslationRun,
  TranslationRunWord,
} from "../types";
import { request } from "./http";

export function createTranslationRun(payload: {
  documentId?: number;
  text?: string;
  collectionId?: number;
  sourceLang?: string;
  targetLang?: string;
}): Promise<TranslationRun> {
  return request<TranslationRun>("/translation/runs", {
    method: "POST",
    body: JSON.stringify({
      document_id: payload.documentId ?? null,
      text: payload.text ?? null,
      collection_id: payload.collectionId ?? null,
      source_lang: payload.sourceLang,
      target_lang: payload.targetLang,
    }),
  });
}

export function getTranslationRun(runId: number): Promise<TranslationRun> {
  return request<TranslationRun>(`/translation/runs/${runId}`);
}

export function getLatestTranslationRunForCollection(
  collectionId: number,
): Promise<TranslationRun | null> {
  return request<TranslationRun | null>(`/translation/collections/${collectionId}/runs/latest`);
}

export function listTranslationRuns(limit = 20): Promise<TranslationRun[]> {
  return request<TranslationRun[]>(`/translation/runs?limit=${limit}`);
}

export function getTranslationRunWords(runId: number): Promise<TranslationRunWord[]> {
  return request<TranslationRunWord[]>(`/translation/runs/${runId}/words`);
}

export function getTranslationRunSentences(runId: number): Promise<string[]> {
  return request<{ sentences: string[] }>(`/translation/runs/${runId}/sentences`).then(
    (body) => body.sentences,
  );
}

export function parseSentence(text: string): Promise<SyntaxToken[]> {
  return request<{ tokens: SyntaxToken[] }>("/translation/parse-sentence", {
    method: "POST",
    body: JSON.stringify({ text }),
  }).then((body) => body.tokens);
}

export function listTranslationDictionary(options: {
  sourceLang?: string;
  targetLang?: string;
  search?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<TranslationDictionaryPage> {
  const params = new URLSearchParams();
  if (options.sourceLang) params.set("source_lang", options.sourceLang);
  if (options.targetLang) params.set("target_lang", options.targetLang);
  if (options.search) params.set("search", options.search);
  params.set("limit", String(options.limit ?? 50));
  params.set("offset", String(options.offset ?? 0));
  return request<TranslationDictionaryPage>(`/translation/dictionary?${params.toString()}`);
}

export function createTranslationDictionaryEntry(
  input: TranslationDictionaryEntryInput,
): Promise<TranslationDictionaryEntry> {
  return request<TranslationDictionaryEntry>("/translation/dictionary", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateTranslationDictionaryEntry(
  id: number,
  input: Partial<Pick<TranslationDictionaryEntryInput, "target_text" | "pos" | "notes">>,
): Promise<TranslationDictionaryEntry> {
  return request<TranslationDictionaryEntry>(`/translation/dictionary/${id}`, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export function deleteTranslationDictionaryEntry(id: number): Promise<void> {
  return request<void>(`/translation/dictionary/${id}`, { method: "DELETE" });
}
