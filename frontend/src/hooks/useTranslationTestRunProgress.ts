import { getTranslationTestRun, translationTestRunWebSocketUrl } from "../api/client";
import { TERMINAL_TRANSLATION_TEST_RUN_STATUSES, type TranslationTestRun } from "../api/types";
import { useJobProgress } from "./useJobProgress";

export function useTranslationTestRunProgress(runId: number | null) {
  return useJobProgress<TranslationTestRun>(runId, {
    fetchJob: getTranslationTestRun,
    wsUrl: translationTestRunWebSocketUrl,
    isTerminal: (data) => TERMINAL_TRANSLATION_TEST_RUN_STATUSES.includes(data.status),
  });
}
