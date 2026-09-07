export interface SearchModel {
  id: number;
  key: string;
  label: string;
  kind: "tfidf" | "dense_embedding";
  dimension: number | null;
}

export interface SearchHit {
  document_id: number;
  title: string;
  url: string | null;
  fetched_at: string;
  rank: number;
  score: number;
  snippet: string;
  matched_terms: string[];
}

export interface SearchResponse {
  query_id: number;
  search_run_id: number;
  query_text: string;
  model: string;
  model_label: string;
  hits: SearchHit[];
}

export interface QuerySummary {
  id: number;
  collection_id: number;
  text: string;
  created_at: string;
}

export interface RelevanceJudgment {
  document_id: number;
  is_relevant: boolean;
}
