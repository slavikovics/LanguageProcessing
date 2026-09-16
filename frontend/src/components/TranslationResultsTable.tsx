import { useState } from "react";

import type { DocumentSummary, TranslationRun } from "@/api/types";
import { PagedTable, type PagedTableColumn } from "@/components/PagedTable";

const PAGE_SIZE = 10;

export function TranslationResultsTable({
  documents,
  results,
}: {
  documents: DocumentSummary[];
  results: TranslationRun[];
}) {
  const [page, setPage] = useState(0);
  const resultByDocument = new Map(results.map((result) => [result.document_id, result]));

  const totalPages = Math.max(1, Math.ceil(documents.length / PAGE_SIZE));
  const pageRows = documents.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const columns: PagedTableColumn<DocumentSummary>[] = [
    {
      key: "document",
      header: "Документ",
      align: "left",
      render: (doc) =>
        doc.url ? (
          <a
            href={doc.url}
            target="_blank"
            rel="noreferrer"
            className="text-primary underline-offset-2 hover:underline"
          >
            {doc.title}
          </a>
        ) : (
          doc.title
        ),
    },
    {
      key: "word_count",
      header: "Слов до",
      render: (doc) => {
        const result = resultByDocument.get(doc.id);
        return result ? <span className="tabular-nums">{result.word_count}</span> : "—";
      },
    },
    {
      key: "translated_text_word_count",
      header: "Слов после",
      render: (doc) => {
        const result = resultByDocument.get(doc.id);
        return result ? <span className="tabular-nums">{result.translated_text_word_count}</span> : "—";
      },
    },
    {
      key: "coverage",
      header: "Покрытие словаря",
      render: (doc) => {
        const result = resultByDocument.get(doc.id);
        if (!result || result.word_count === 0) return "—";
        const percent = Math.round((result.translated_word_count / result.word_count) * 100);
        return (
          <span className="tabular-nums">
            {result.translated_word_count}/{result.word_count} ({percent}%)
          </span>
        );
      },
    },
    {
      key: "elapsed_ms",
      header: "Время",
      render: (doc) => {
        const result = resultByDocument.get(doc.id);
        return result ? <span className="tabular-nums">{result.elapsed_ms.toFixed(0)} мс</span> : "—";
      },
    },
  ];

  return (
    <PagedTable
      columns={columns}
      rows={pageRows}
      getRowKey={(doc) => doc.id}
      page={page}
      totalPages={totalPages}
      onPageChange={setPage}
      totalCount={documents.length}
      totalLabel="Всего документов:"
      emptyMessage="Нет результатов"
    />
  );
}
