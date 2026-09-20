import { AlertTriangle, CheckCircle2, Loader2, Play, Square } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { cancelTranslationTestRun, createTranslationTestRun } from "@/api/client";
import type { TranslationMethod } from "@/api/types";
import {
  DEFAULT_SOURCE_LANGUAGE,
  DEFAULT_TARGET_LANGUAGE,
  TERMINAL_TRANSLATION_TEST_RUN_STATUSES,
  TRANSLATION_METHOD_LABELS,
} from "@/api/types";
import { useTranslationTestRunProgress } from "@/hooks/useTranslationTestRunProgress";

import { ProgressBar } from "@/components/ProgressBar";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function TranslationTestingTab({
  collectionId,
  method,
}: {
  collectionId: number | null;
  method: TranslationMethod;
}) {
  const [runId, setRunId] = useState<number | null>(null);
  const [testing, setTesting] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [justFinished, setJustFinished] = useState(false);
  const [finishNote, setFinishNote] = useState<string | null>(null);

  const { progress: run } = useTranslationTestRunProgress(runId);

  const finishTesting = useCallback(() => {
    setTesting(false);
    setRunId(null);
    setJustFinished(true);
  }, []);

  useEffect(() => {
    if (!testing || run === null) return;
    if (!TERMINAL_TRANSLATION_TEST_RUN_STATUSES.includes(run.status)) return;
    if (run.status === "failed") {
      setRunError(run.error_message ?? "Тест завершился с ошибкой.");
      setJustFinished(false);
      setTesting(false);
      setRunId(null);
      return;
    }
    setFinishNote(run.status === "completed" ? run.error_message : null);
    finishTesting();
  }, [run, testing, finishTesting]);

  async function handleRunTest() {
    if (collectionId === null) return;
    setRunError(null);
    setFinishNote(null);
    setTesting(true);
    setJustFinished(false);
    try {
      const created = await createTranslationTestRun({
        collectionId,
        sourceLang: DEFAULT_SOURCE_LANGUAGE,
        targetLang: DEFAULT_TARGET_LANGUAGE,
        method,
      });
      setRunId(created.id);
    } catch (err) {
      setRunError(err instanceof Error ? err.message : String(err));
      setTesting(false);
    }
  }

  async function handleStopAndDiscard() {
    setTesting(false);
    setStopping(true);
    const activeId = runId;
    setRunId(null);
    try {
      if (activeId !== null) await cancelTranslationTestRun(activeId).catch(() => {});
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
              Тест запускает выбранный метод — «{TRANSLATION_METHOD_LABELS[method]}» — на
              документах текущей коллекции, размеченных как англоязычные при кроулинге (документы
              на других языках пропускаются). По завершении среднее число слов до и после
              перевода, покрытие словаря и время перевода можно посмотреть на странице{" "}
              <Link to="/metrics" className="text-primary underline-offset-2 hover:underline">
                «Метрики»
              </Link>
              .
            </p>
            <div className="flex shrink-0 flex-col gap-2 self-start sm:self-center">
              <Button
                type="button"
                onClick={handleRunTest}
                disabled={testing || stopping || collectionId === null}
              >
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
            <ProgressBar
              value={run?.documents_processed ?? 0}
              max={Math.max(run?.documents_total ?? 1, 1)}
              complete={run?.status === "completed"}
            />
          )}
          {justFinished && !testing && (
            <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <CheckCircle2 className="size-4 shrink-0 text-primary" />
              Тест завершён — результаты на странице{" "}
              <Link to="/metrics" className="text-primary underline-offset-2 hover:underline">
                «Метрики»
              </Link>
              .
            </p>
          )}
          {justFinished && !testing && finishNote && (
            <p className="flex items-center gap-1.5 text-sm text-amber-600 dark:text-amber-400">
              <AlertTriangle className="size-4 shrink-0" />
              {finishNote}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
