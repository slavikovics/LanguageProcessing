import { Download, FileJson, HelpCircle, Printer, RotateCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { compareSummarizationMethods, getSummarizationRunResults, listDocuments } from "@/api/client";
import {
  SUMMARIZATION_METHODS,
  SUMMARIZATION_METHOD_LABELS,
  type DocumentSummary,
  type DocumentSummaryRecord,
  type SummarizationMethod,
  type SummarizationRunSummary,
} from "@/api/types";
import { downloadCsv, downloadJson } from "@/lib/exportResults";
import { escapeHtml, openPrintView } from "@/lib/printView";

import { SummarizationMethodComparisonTable } from "@/components/SummarizationMethodComparisonTable";
import { SummarizationResultsTable } from "@/components/SummarizationResultsTable";
import { SummarizationSummaryBarChart } from "@/components/SummarizationSummaryBarChart";
import { Button } from "@/components/ui/button";

export function SummarizationMetricsSection({ collectionId }: { collectionId: number | null }) {
  const [summaries, setSummaries] = useState<SummarizationRunSummary[]>([]);
  const [resultsByMethod, setResultsByMethod] = useState<
    Partial<Record<SummarizationMethod, DocumentSummaryRecord[]>>
  >({});
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      const compared = await compareSummarizationMethods(id, [...SUMMARIZATION_METHODS]);
      setSummaries(compared.summaries);
      const byMethod: Partial<Record<SummarizationMethod, DocumentSummaryRecord[]>> = {};
      for (const summary of compared.summaries) {
        byMethod[summary.method] = await getSummarizationRunResults(summary.run_id);
      }
      setResultsByMethod(byMethod);
      setDocuments(await listDocuments(id, { limit: 500 }));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSummaries([]);
      setResultsByMethod({});
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (collectionId !== null) void refresh(collectionId);
    else {
      setSummaries([]);
      setResultsByMethod({});
      setDocuments([]);
    }
  }, [collectionId, refresh]);

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
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold tracking-tight">Метрики реферирования</h2>
          <div className="flex flex-wrap gap-2">
            {collectionId !== null && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => refresh(collectionId)}
                disabled={loading}
                title="Пересчитывает метрики по последним завершённым тестовым прогонам каждого метода"
              >
                <RotateCw className={loading ? "size-3.5 animate-spin" : "size-3.5"} />
                {loading ? "Обновление…" : "Обновить"}
              </Button>
            )}
            <Button type="button" variant="outline" size="sm" asChild>
              <Link to="/help#summarization">
                <HelpCircle className="size-3.5" />
                Подробнее о методике
              </Link>
            </Button>
          </div>
        </div>
        <p className="text-sm text-muted-foreground">
          Среднее время реферирования, средняя степень сжатия и число предложений в реферате для
          каждого из трёх методов — считаются по последнему тестовому прогону на всех документах
          коллекции. Запустите тест на странице «Реферирование».
        </p>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {collectionId === null && (
        <p className="text-sm text-muted-foreground">
          Выберите коллекцию вверху страницы, чтобы увидеть метрики реферирования.
        </p>
      )}

      {collectionId !== null && summaries.length === 0 && !loading && (
        <p className="text-sm text-muted-foreground">
          Пока нет ни одного завершённого теста для этой коллекции. Запустите тест на странице{" "}
          <Link to="/summarization" className="text-primary underline-offset-2 hover:underline">
            «Реферирование»
          </Link>
          , либо нажмите «Обновить» здесь.
        </p>
      )}

      {summaries.length > 0 && (
        <div className="flex flex-col gap-6">
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

          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="text-base font-medium">Результаты по документам</h3>
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
            </div>
            <SummarizationResultsTable documents={documents} resultsByMethod={resultsByMethod} />
          </div>
        </div>
      )}
    </div>
  );
}
