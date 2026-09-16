import { Download, FileJson, HelpCircle, Printer, RotateCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  getTranslationTestRunResults,
  getTranslationTestRunSummary,
  listDocuments,
  listTranslationTestRunsByCollection,
} from "@/api/client";
import type { DocumentSummary, TranslationRun, TranslationRunSummary } from "@/api/types";
import { downloadCsv, downloadJson } from "@/lib/exportResults";
import { escapeHtml, openPrintView } from "@/lib/printView";

import { TranslationResultsTable } from "@/components/TranslationResultsTable";
import { Button } from "@/components/ui/button";

export function TranslationMetricsSection({ collectionId }: { collectionId: number | null }) {
  const [summary, setSummary] = useState<TranslationRunSummary | null>(null);
  const [results, setResults] = useState<TranslationRun[]>([]);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      const runs = await listTranslationTestRunsByCollection(id);
      const latest = runs.find((run) => run.status === "completed") ?? null;
      if (latest === null) {
        setSummary(null);
        setResults([]);
        setDocuments([]);
        return;
      }
      const [runSummary, runResults, docs] = await Promise.all([
        getTranslationTestRunSummary(latest.id),
        getTranslationTestRunResults(latest.id),
        listDocuments(id, { limit: 500 }),
      ]);
      setSummary(runSummary);
      setResults(runResults);
      setDocuments(docs);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSummary(null);
      setResults([]);
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (collectionId !== null) void refresh(collectionId);
    else {
      setSummary(null);
      setResults([]);
      setDocuments([]);
    }
  }, [collectionId, refresh]);

  function handleExportCsv() {
    const rows = documents.map((doc) => {
      const result = results.find((r) => r.document_id === doc.id);
      return {
        document: doc.title,
        url: doc.url ?? "",
        word_count_before: result?.word_count ?? "",
        word_count_after: result?.translated_text_word_count ?? "",
        translated_word_count: result?.translated_word_count ?? "",
        elapsed_ms: result?.elapsed_ms ?? "",
      };
    });
    downloadCsv("translation-results.csv", rows);
  }

  function handleExportJson() {
    downloadJson("translation-results.json", { summary, results, documents });
  }

  function handlePrint() {
    const resultsTableHtml = `
      <table>
        <thead>
          <tr><th>Документ</th><th>Слов до</th><th>Слов после</th><th>Переведено слов</th><th>Время</th></tr>
        </thead>
        <tbody>
          ${documents
            .map((doc) => {
              const result = results.find((r) => r.document_id === doc.id);
              return `<tr><td>${escapeHtml(doc.title)}</td><td>${
                result?.word_count ?? "—"
              }</td><td>${result?.translated_text_word_count ?? "—"}</td><td>${
                result?.translated_word_count ?? "—"
              }</td><td>${result ? `${result.elapsed_ms.toFixed(0)} мс` : "—"}</td></tr>`;
            })
            .join("")}
        </tbody>
      </table>
    `;

    openPrintView(
      "Метрики машинного перевода",
      `
        <h1>Метрики машинного перевода</h1>
        ${
          summary
            ? `<p>Документов переведено: ${summary.documents_translated}. Среднее время: ${summary.mean_elapsed_ms.toFixed(
                1,
              )} мс. Слов до/после: ${summary.mean_word_count.toFixed(1)} / ${summary.mean_translated_text_word_count.toFixed(
                1,
              )}. Покрытие словаря: ${(summary.mean_coverage_ratio * 100).toFixed(1)}%.</p>`
            : ""
        }
        <h2>Результаты по документам</h2>
        ${resultsTableHtml}
      `,
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold tracking-tight">Метрики машинного перевода</h2>
          <div className="flex flex-wrap gap-2">
            {collectionId !== null && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => refresh(collectionId)}
                disabled={loading}
                title="Пересчитывает метрики по последнему завершённому тестовому прогону"
              >
                <RotateCw className={loading ? "size-3.5 animate-spin" : "size-3.5"} />
                {loading ? "Обновление…" : "Обновить"}
              </Button>
            )}
            <Button type="button" variant="outline" size="sm" asChild>
              <Link to="/help#translation">
                <HelpCircle className="size-3.5" />
                Подробнее о методике
              </Link>
            </Button>
          </div>
        </div>
        <p className="text-sm text-muted-foreground">
          Число слов до и после перевода, покрытие словаря и время выполнения — считаются по
          последнему тестовому прогону пословного перевода на англоязычных документах коллекции
          (по языку, определённому при кроулинге). Запустите тест на странице «Перевод».
        </p>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {collectionId === null && (
        <p className="text-sm text-muted-foreground">
          Выберите коллекцию вверху страницы, чтобы увидеть метрики перевода.
        </p>
      )}

      {collectionId !== null && summary === null && !loading && (
        <p className="text-sm text-muted-foreground">
          Пока нет ни одного завершённого теста для этой коллекции. Запустите тест на странице{" "}
          <Link to="/translation" className="text-primary underline-offset-2 hover:underline">
            «Перевод»
          </Link>
          , либо нажмите «Обновить» здесь.
        </p>
      )}

      {summary !== null && (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
            <MetricStat label="Документов переведено" value={`${summary.documents_translated}`} />
            <MetricStat label="Среднее время" value={`${summary.mean_elapsed_ms.toFixed(1)} мс`} />
            <MetricStat label="Слов до перевода" value={summary.mean_word_count.toFixed(1)} />
            <MetricStat label="Слов после перевода" value={summary.mean_translated_text_word_count.toFixed(1)} />
            <MetricStat label="Покрытие словаря" value={`${(summary.mean_coverage_ratio * 100).toFixed(1)}%`} />
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
            <TranslationResultsTable documents={documents} results={results} />
          </div>
        </div>
      )}
    </div>
  );
}

function MetricStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-lg border bg-card p-3">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-lg font-semibold tabular-nums">{value}</span>
    </div>
  );
}
