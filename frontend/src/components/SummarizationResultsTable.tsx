import { useState } from "react";

import {
  SUMMARIZATION_METHOD_LABELS,
  type DocumentSummary,
  type DocumentSummaryRecord,
  type SummarizationMethod,
} from "@/api/types";
import { ModelSwatch } from "@/components/ModelSwatch";
import { PagedTable, type PagedTableColumn } from "@/components/PagedTable";
import { colorForModel } from "@/lib/modelColors";

const PAGE_SIZE = 10;

export function SummarizationResultsTable({
  documents,
  resultsByMethod,
}: {
  documents: DocumentSummary[];
  resultsByMethod: Partial<Record<SummarizationMethod, DocumentSummaryRecord[]>>;
}) {
  const [page, setPage] = useState(0);
  const methods = Object.keys(resultsByMethod) as SummarizationMethod[];
  const resultByDocument = new Map(
    methods.map((method) => [
      method,
      new Map((resultsByMethod[method] ?? []).map((result) => [result.document_id, result])),
    ]),
  );

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
    ...methods.map((method) => ({
      key: method,
      header: <ModelSwatch label={SUMMARIZATION_METHOD_LABELS[method]} color={colorForModel(method)} />,
      render: (doc: DocumentSummary) => {
        const result = resultByDocument.get(method)?.get(doc.id);
        return result ? (
          <span className="tabular-nums">
            {`${result.summary_sentence_indices.length}/${result.total_sentences} · ${result.elapsed_ms.toFixed(0)} мс`}
          </span>
        ) : (
          <span className="text-muted-foreground">—</span>
        );
      },
    })),
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
