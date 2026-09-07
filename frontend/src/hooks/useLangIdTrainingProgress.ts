import { getNeuralTrainingJob, langIdTrainingWebSocketUrl } from "../api/client";
import { TERMINAL_LANG_ID_JOB_STATUSES, type LangIdTrainingJob } from "../api/types";
import { useJobProgress } from "./useJobProgress";

export function useLangIdTrainingProgress(jobId: number | null) {
  return useJobProgress<LangIdTrainingJob>(jobId, {
    fetchJob: getNeuralTrainingJob,
    wsUrl: langIdTrainingWebSocketUrl,
    isTerminal: (data) => TERMINAL_LANG_ID_JOB_STATUSES.includes(data.status),
  });
}
