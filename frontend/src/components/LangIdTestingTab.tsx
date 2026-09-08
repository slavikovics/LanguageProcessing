import { useCallback, useEffect, useState } from "react";
import { compareLangIdMethods, createLangIdRuns, listDocuments, listLangIdResults } from "../api/client";
import {
  LANG_ID_METHODS,
  LANG_ID_METHOD_LABELS,
  type DocumentSummary,
  type LangIdMethod,
  type LangIdResult,
  type LangIdRunSummary,
} from "../api/types";
import { downloadCsv, downloadJson } from "../lib/exportResults";
import { useLangIdRunProgress } from "../hooks/useLangIdRunProgress";

import { LangIdMethodComparisonTable } from "@/components/LangIdMethodComparisonTable";
import { LangIdResultsTable } from "@/components/LangIdResultsTable";
import { LangIdSummaryBarChart } from "@/components/LangIdSummaryBarChart";
import { ProgressBar } from "@/components/ProgressBar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const EMPTY_RUN_IDS: Record<LangIdMethod, number | null> = {
  frequent_words: null,
  alphabetic: null,
  neural: null,
};

export function LangIdTestingTab({ collectionId }: { collectionId: number }) {
  const [runIds, setRunIds] = useState<Record<LangIdMethod, number | null>>(EMPTY_RUN_IDS);
  const [testing, setTesting] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [summaries, setSummaries] = useState<LangIdRunSummary[]>([]);
  const [resultsByMethod, setResultsByMethod] = useState<Partial<Record<LangIdMethod, LangIdResult[]>>>({});
  const [testDocuments, setTestDocuments] = useState<DocumentSummary[]>([]);

  const { progress: freqWordsRun } = useLangIdRunProgress(runIds.frequent_words);
  const { progress: alphabeticRun } = useLangIdRunProgress(runIds.alphabetic);
  const { progress: neuralRun } = useLangIdRunProgress(runIds.neural);
  const runsInProgress = { frequent_words: freqWordsRun, alphabetic: alphabeticRun, neural: neuralRun };

  const loadLatestResults = useCallback(async () => {
    const compared = await compareLangIdMethods(collectionId, [...LANG_ID_METHODS]);
    setSummaries(compared.summaries);
    const byMethod: Partial<Record<LangIdMethod, LangIdResult[]>> = {};
    for (const summary of compared.summaries) {
      byMethod[summary.method] = await listLangIdResults(summary.run_id);
    }
    setResultsByMethod(byMethod);
    const docs = await listDocuments(collectionId, { limit: 500 });
    setTestDocuments(docs.filter((d) => d.corpus_split === "test"));
  }, [collectionId]);

  useEffect(() => {
    void loadLatestResults();
  }, [loadLatestResults]);

  const finishTesting = useCallback(async () => {
    setTesting(false);
    setRunIds(EMPTY_RUN_IDS);
    await loadLatestResults();
  }, [loadLatestResults]);

  useEffect(() => {
    if (!testing) return;
    const runs = [freqWordsRun, alphabeticRun, neuralRun].filter((r) => r !== null);
    if (runs.length === 0) return;
    const allTerminal = runs.every((r) => r.status === "completed" || r.status === "failed");
    if (allTerminal)
      void finishTesting();
  }, [freqWordsRun, alphabeticRun, neuralRun, testing]);

  async function handleRunTest() {
    setRunError(null);
    setTesting(true);
    setSummaries([]);
    setResultsByMethod({});
    try {
      const runs = await createLangIdRuns(collectionId, [...LANG_ID_METHODS]);
      const next = { ...EMPTY_RUN_IDS };
      for (const run of runs) next[run.method] = run.id;
      setRunIds(next);
    } catch (err) {
      setRunError(err instanceof Error ? err.message : String(err));
      setTesting(false);
    }
  }

  function handleExportCsv() {
    const rows = testDocuments.map((doc) => {
      const row: Record<string, unknown> = {
        document: doc.title,
        url: doc.url ?? "",
        true_language: doc.confirmed_language ?? "",
      };
      for (const method of LANG_ID_METHODS) {
        const result = resultsByMethod[method]?.find((r) => r.document_id === doc.id);
        row[`${method}_predicted`] = result?.predicted_language ?? "";
        row[`${method}_correct`] = result?.is_correct ?? "";
      }
      return row;
    });
    downloadCsv("lang-id-results.csv", rows);
  }

  function handleExportJson() {
    downloadJson("lang-id-results.json", { summaries, results: resultsByMethod, documents: testDocuments });
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardContent className="flex flex-col gap-4 py-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="max-w-prose text-sm text-muted-foreground">
              Все три метода — частотных слов, алфавитный и нейросетевой — запускаются на
              документах тестовой выборки текущей коллекции. По завершении будут показаны
              Accuracy, Precision, Recall, F1 и среднее время классификации каждого метода, а
              также результат по каждому документу с экспортом в CSV/JSON и печатью.
            </p>
            <Button
              type="button"
              onClick={handleRunTest}
              disabled={testing}
              className="shrink-0 self-start sm:self-center"
            >
              {testing ? "Тестирование…" : "Запустить тест"}
            </Button>
          </div>
          {runError && <p className="text-sm text-destructive">{runError}</p>}
          {testing && (
            <div className="flex flex-col gap-2">
              {LANG_ID_METHODS.map((method) => {
                const run = runsInProgress[method];
                return (
                  <div key={method} className="flex flex-col gap-1">
                    <span className="text-xs text-muted-foreground">{LANG_ID_METHOD_LABELS[method]}</span>
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
        </CardContent>
      </Card>

      {summaries.length > 0 && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Сравнение методов</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-6">
              <LangIdMethodComparisonTable summaries={summaries} />
              <div className="grid gap-4 sm:grid-cols-2">
                <LangIdSummaryBarChart
                  summaries={summaries}
                  valueOf={(s) => s.accuracy * 100}
                  formatValue={(v) => `${v.toFixed(1)}%`}
                  ariaLabel="Точность по методам"
                />
                <LangIdSummaryBarChart
                  summaries={summaries}
                  valueOf={(s) => s.mean_elapsed_ms}
                  formatValue={(v) => `${v.toFixed(1)} мс`}
                  ariaLabel="Среднее время по методам"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-3">
              <CardTitle>Результаты по документам</CardTitle>
              <div className="flex gap-2">
                <Button type="button" variant="outline" size="sm" onClick={handleExportCsv}>
                  Скачать CSV
                </Button>
                <Button type="button" variant="outline" size="sm" onClick={handleExportJson}>
                  Экспорт JSON
                </Button>
                <Button type="button" variant="outline" size="sm" onClick={() => window.print()}>
                  Печать
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <LangIdResultsTable documents={testDocuments} resultsByMethod={resultsByMethod} />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
