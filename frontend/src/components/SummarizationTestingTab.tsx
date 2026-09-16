import { CheckCircle2, Loader2, Play, Square } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { cancelSummarizationRun, createSummarizationRuns } from "@/api/client";
import {
  SUMMARIZATION_METHODS,
  SUMMARIZATION_METHOD_LABELS,
  TERMINAL_SUMMARIZATION_JOB_STATUSES,
  type SummarizationMethod,
} from "@/api/types";
import { useSummarizationRunProgress } from "@/hooks/useSummarizationRunProgress";

import { ProgressBar } from "@/components/ProgressBar";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const EMPTY_RUN_IDS: Record<SummarizationMethod, number | null> = {
  algorithmic: null,
  textrank: null,
  embeddings: null,
};

export function SummarizationTestingTab({ collectionId }: { collectionId: number }) {
  const [runIds, setRunIds] = useState<Record<SummarizationMethod, number | null>>(EMPTY_RUN_IDS);
  const [testing, setTesting] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [justFinished, setJustFinished] = useState(false);

  const { progress: algorithmicRun } = useSummarizationRunProgress(runIds.algorithmic);
  const { progress: textrankRun } = useSummarizationRunProgress(runIds.textrank);
  const { progress: embeddingsRun } = useSummarizationRunProgress(runIds.embeddings);
  const runsInProgress = { algorithmic: algorithmicRun, textrank: textrankRun, embeddings: embeddingsRun };

  const finishTesting = useCallback(() => {
    setTesting(false);
    setRunIds(EMPTY_RUN_IDS);
    setJustFinished(true);
  }, []);

  useEffect(() => {
    if (!testing) return;
    const runs = [algorithmicRun, textrankRun, embeddingsRun].filter((r) => r !== null);
    if (runs.length === 0) return;
    const allTerminal = runs.every((r) => TERMINAL_SUMMARIZATION_JOB_STATUSES.includes(r.status));
    if (allTerminal) finishTesting();
  }, [algorithmicRun, textrankRun, embeddingsRun, testing, finishTesting]);

  async function handleRunTest() {
    setRunError(null);
    setTesting(true);
    setJustFinished(false);
    try {
      const runs = await createSummarizationRuns(collectionId, [...SUMMARIZATION_METHODS]);
      const next = { ...EMPTY_RUN_IDS };
      for (const run of runs) next[run.method] = run.id;
      setRunIds(next);
    } catch (err) {
      setRunError(err instanceof Error ? err.message : String(err));
      setTesting(false);
    }
  }

  async function handleStopAndDiscard() {
    setTesting(false);
    setStopping(true);
    const activeIds = Object.values(runIds).filter((id): id is number => id !== null);
    setRunIds(EMPTY_RUN_IDS);
    try {
      await Promise.all(activeIds.map((id) => cancelSummarizationRun(id).catch(() => {})));
    } finally {
      setStopping(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardContent className="flex flex-col gap-4 py-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="max-w-prose text-sm text-muted-foreground">
              Все три метода — {SUMMARIZATION_METHOD_LABELS.algorithmic}, TextRank и эмбеддинги —
              запускаются на всех документах текущей коллекции. По завершении среднее время
              реферирования, степень сжатия и результат по каждому документу можно посмотреть на
              странице{" "}
              <Link to="/metrics" className="text-primary underline-offset-2 hover:underline">
                «Метрики»
              </Link>
              .
            </p>
            <div className="flex shrink-0 flex-col gap-2 self-start sm:self-center">
              <Button type="button" onClick={handleRunTest} disabled={testing || stopping}>
                {testing ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" />}
                {testing ? "Тестирование…" : "Запустить тест"}
              </Button>
              {testing && (
                <Button type="button" variant="destructive" onClick={handleStopAndDiscard} disabled={stopping}>
                  {stopping ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Square className="size-4" />
                  )}
                  {stopping ? "Остановка…" : "Остановить и отменить"}
                </Button>
              )}
            </div>
          </div>
          {runError && <p className="text-sm text-destructive">{runError}</p>}
          {testing && (
            <div className="flex flex-col gap-2">
              {SUMMARIZATION_METHODS.map((method) => {
                const run = runsInProgress[method];
                const active = run !== null && !TERMINAL_SUMMARIZATION_JOB_STATUSES.includes(run.status);
                return (
                  <div key={method} className="flex flex-col gap-1">
                    <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      {active && <Loader2 className="size-3 animate-spin" />}
                      {SUMMARIZATION_METHOD_LABELS[method]}
                    </span>
                    <ProgressBar
                      value={run?.documents_processed ?? 0}
                      max={Math.max(run?.documents_total ?? 1, 1)}
                      complete={run?.status === "completed"}
                    />
                  </div>
                );
              })}
            </div>
          )}
          {justFinished && !testing && (
            <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <CheckCircle2 className="size-4 shrink-0 text-primary" />
              Тест завершён — результаты и сравнение методов на странице{" "}
              <Link to="/metrics" className="text-primary underline-offset-2 hover:underline">
                «Метрики»
              </Link>
              .
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
