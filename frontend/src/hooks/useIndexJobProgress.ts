import { getIndexJob, indexJobWebSocketUrl } from "../api/client";
import { TERMINAL_INDEX_STATUSES, type IndexJob } from "../api/types";
import { useJobProgress } from "./useJobProgress";

export function useIndexJobProgress(jobId: number | null) {
  return useJobProgress<IndexJob>(jobId, {
    fetchJob: getIndexJob,
    wsUrl: indexJobWebSocketUrl,
    isTerminal: (data) => TERMINAL_INDEX_STATUSES.includes(data.status),
  });
}
