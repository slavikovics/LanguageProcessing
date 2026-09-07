export type PrecisionRecallCurve = [number, number][];

export interface QueryMetrics {
  query_id: number;
  query_text: string;
  search_run_id: number;
  retrieved_count: number;
  relevant_count: number;
  precision_at_5: number;
  precision_at_10: number;
  recall_at_5: number;
  recall_at_10: number;
  f1_at_5: number;
  f1_at_10: number;
  average_precision: number;
  r_precision: number;
  curve: PrecisionRecallCurve;
}

export interface CollectionMetricsSummary {
  collection_id: number;
  model: string;
  model_label: string;
  map: number;
  mean_recall_at_5: number;
  mean_recall_at_10: number;
  mean_f1_at_5: number;
  mean_f1_at_10: number;
  mean_r_precision: number;
  mean_precision_at_5: number;
  mean_precision_at_10: number;
  queries: QueryMetrics[];
  curve: PrecisionRecallCurve;
  unscored_judged_queries: number;
}

export interface MetricsCompareResponse {
  summaries: CollectionMetricsSummary[];
}
