export interface Collection {
  id: number;
  name: string;
  language: string;
  created_at: string;
  document_count: number;
  documents_changed_at: string | null;
}

export interface DocumentSummary {
  id: number;
  collection_id: number;
  title: string;
  url: string | null;
  language: string;
  char_count: number;
  fetched_at: string;
  confirmed_language: string | null;
  corpus_split: "train" | "test" | null;
}

export interface DocumentDetail extends DocumentSummary {
  clean_text: string;
}
