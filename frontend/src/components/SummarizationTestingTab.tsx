import { Download, FileJson, Loader2, Play, Printer, Square } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import {
  cancelSummarizationRun,
  compareSummarizationMethods,
  createSummarizationRuns,
  getSummarizationRunResults,
  listDocuments,
} from "@/api/client";
import {
  SUMMARIZATION_METHODS,
  SUMMARIZATION_METHOD_LABELS,
  TERMINAL_SUMMARIZATION_JOB_STATUSES,
  type DocumentSummary,
  type DocumentSummaryRecord,
  type SummarizationMethod,
  type SummarizationRunSummary,
} from "@/api/types";
import { downloadCsv, downloadJson } from "@/lib/exportResults";
import { escapeHtml, openPrintView } from "@/lib/printView";
import { useSummarizationRunProgress } from "@/hooks/useSummarizationRunProgress";

import { ProgressBar } from "@/components/ProgressBar";
import { SummarizationMethodComparisonTable } from "@/components/SummarizationMethodComparisonTable";
import { SummarizationResultsTable } from "@/components/SummarizationResultsTable";
import { SummarizationSummaryBarChart } from "@/components/SummarizationSummaryBarChart";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

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
  const [summaries, setSummaries] = useState<SummarizationRunSummary[]>([]);
  const [resultsByMethod, setResultsByMethod] = useState<
    Partial<Record<SummarizationMethod, DocumentSummaryRecord[]>>
  >({});
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);

  const { progress: algorithmicRun } = useSummarizationRunProgress(runIds.algorithmic);
  const { progress: textrankRun } = useSummarizationRunProgress(runIds.textrank);
  const { progress: embeddingsRun } = useSummarizationRunProgress(runIds.embeddings);
  const runsInProgress = { algorithmic: algorithmicRun, textrank: textrankRun, embeddings: embeddingsRun };

  const loadLatestResults = useCallback(async () => {
    const compared = await compareSummarizationMethods(collectionId, [...SUMMARIZATION_METHODS]);
    setSummaries(compared.summaries);
    const byMethod: Partial<Record<SummarizationMethod, DocumentSummaryRecord[]>> = {};
    for (const summary of compared.summaries) {
      byMethod[summary.method] = await getSummarizationRunResults(summary.run_id);
    }
    setResultsByMethod(byMethod);
    const docs = await listDocuments(collectionId, { limit: 500 });
    setDocuments(docs);
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
    const runs = [algorithmicRun, textrankRun, embeddingsRun].filter((r) => r !== null);
    if (runs.length === 0) return;
    const allTerminal = runs.every((r) =>
      TERMINAL_SUMMARIZATION_JOB_STATUSES.includes(r.status),
    );
    if (allTerminal) void finishTesting();
  }, [algorithmicRun, textrankRun, embeddingsRun, testing]);

  async function handleRunTest() {
    setRunError(null);
    setTesting(true);
    setSummaries([]);
    setResultsByMethod({});
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
    await loadLatestResults();
  }

  function handleExportCsv() {
    const rows = documents.map((doc) => {
      const row: Record<string, unknown> = { document: doc.title, url: doc.url ?? "" };
      for (const method of SUMMARIZATION_METHODS) {
        const result = resultsByMethod[method]?.find((r) => r.document_id === doc.id);
        row[`${method}_sentence_count`] = result?.summary_sentence_indices.length ?? "";
        row[`${method}_elapsed_ms`] = result?.elapsed_ms ?? "";
      }
      return row;
    });
    downloadCsv("summarization-results.csv", rows);
  }

  function handleExportJson() {
    downloadJson("summarization-results.json", { summaries, results: resultsByMethod, documents });
  }

  function handlePrint() {
    const comparisonRows: [string, (s: SummarizationRunSummary) => string][] = [
      ["Среднее время реферирования", (s) => `${s.mean_elapsed_ms.toFixed(2)} мс`],
      ["Средняя степень сжатия", (s) => `${(s.mean_compression_ratio * 100).toFixed(1)}%`],
      ["Среднее число предложений в реферате", (s) => s.mean_sentence_count.toFixed(1)],
      ["Документов обработано", (s) => `${s.documents_summarized}`],
    ];
    const comparisonTableHtml = `
      <table>
        <thead><tr><th>Метрика</th>${summaries
          .map((s) => `<th>${escapeHtml(SUMMARIZATION_METHOD_LABELS[s.method])}</th>`)
          .join("")}</tr></thead>
        <tbody>
          ${comparisonRows
            .map(
              ([label, format]) =>
                `<tr><td>${escapeHtml(label)}</td>${summaries
                  .map((s) => `<td>${escapeHtml(format(s))}</td>`)
                  .join("")}</tr>`,
            )
            .join("")}
        </tbody>
      </table>
    `;

    const methods = Object.keys(resultsByMethod) as SummarizationMethod[];
    const resultsTableHtml = `
      <table>
        <thead><tr><th>Документ</th>${methods
          .map((m) => `<th>${escapeHtml(SUMMARIZATION_METHOD_LABELS[m])}</th>`)
          .join("")}</tr></thead>
        <tbody>
          ${documents
            .map((doc) => {
              const cells = methods
                .map((method) => {
                  const result = resultsByMethod[method]?.find((r) => r.document_id === doc.id);
                  return `<td>${
                    result
                      ? escapeHtml(
                          `${result.summary_sentence_indices.length}/${result.total_sentences} · ${result.elapsed_ms.toFixed(0)} мс`,
                        )
                      : "—"
                  }</td>`;
                })
                .join("");
              return `<tr><td>${escapeHtml(doc.title)}</td>${cells}</tr>`;
            })
            .join("")}
        </tbody>
      </table>
    `;

    openPrintView(
      "Сравнение методов реферирования",
      `
        <h1>Сравнение методов реферирования</h1>
        <h2>Сравнение методов</h2>
        ${comparisonTableHtml}
        <h2>Результаты по документам</h2>
        ${resultsTableHtml}
      `,
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardContent className="flex flex-col gap-4 py-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="max-w-prose text-sm text-muted-foreground">
              Все три метода — алгоритм из методички, TextRank и эмбеддинги — запускаются на всех
              документах текущей коллекции. По завершении будет показано среднее время
              реферирования, средняя степень сжатия и число предложений в реферате для каждого
              метода, а также результат по каждому документу с экспортом в CSV/JSON и печатью.
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
        </CardContent>
      </Card>

      {summaries.length > 0 && (
        <>
          <Card>
            <CardHeader className="text-center">
              <CardTitle>Сравнение методов</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-6">
              <SummarizationMethodComparisonTable summaries={summaries} />
              <div className="grid gap-4 sm:grid-cols-2">
                <SummarizationSummaryBarChart
                  summaries={summaries}
                  valueOf={(s) => s.mean_elapsed_ms}
                  formatValue={(v) => `${v.toFixed(1)} мс`}
                  ariaLabel="Среднее время по методам"
                />
                <SummarizationSummaryBarChart
                  summaries={summaries}
                  valueOf={(s) => s.mean_compression_ratio * 100}
                  formatValue={(v) => `${v.toFixed(1)}%`}
                  ariaLabel="Средняя степень сжатия по методам"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-3">
              <CardTitle>Результаты по документам</CardTitle>
              <div className="flex gap-2">
                <Button type="button" variant="outline" size="sm" onClick={handleExportCsv}>
                  <Download className="size-3.5" />
                  Скачать CSV
                </Button>
                <Button type="button" variant="outline" size="sm" onClick={handleExportJson}>
                  <FileJson className="size-3.5" />
                  Экспорт JSON
                </Button>
                <Button type="button" variant="outline" size="sm" onClick={handlePrint}>
                  <Printer className="size-3.5" />
                  Печать
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <SummarizationResultsTable documents={documents} resultsByMethod={resultsByMethod} />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
