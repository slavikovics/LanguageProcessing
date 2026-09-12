import { getSummarizationRun, summarizationRunWebSocketUrl } from "../api/client";
import { TERMINAL_SUMMARIZATION_JOB_STATUSES, type SummarizationRun } from "../api/types";
import { useJobProgress } from "./useJobProgress";

export function useSummarizationRunProgress(runId: number | null) {
  return useJobProgress<SummarizationRun>(runId, {
    fetchJob: getSummarizationRun,
    wsUrl: summarizationRunWebSocketUrl,
    isTerminal: (data) => TERMINAL_SUMMARIZATION_JOB_STATUSES.includes(data.status),
  });
}
