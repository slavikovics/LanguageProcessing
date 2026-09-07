import { getLangIdRun, langIdRunWebSocketUrl } from "../api/client";
import { TERMINAL_LANG_ID_JOB_STATUSES, type LangIdRun } from "../api/types";
import { useJobProgress } from "./useJobProgress";

export function useLangIdRunProgress(runId: number | null) {
  return useJobProgress<LangIdRun>(runId, {
    fetchJob: getLangIdRun,
    wsUrl: langIdRunWebSocketUrl,
    isTerminal: (data) => TERMINAL_LANG_ID_JOB_STATUSES.includes(data.status),
  });
}
