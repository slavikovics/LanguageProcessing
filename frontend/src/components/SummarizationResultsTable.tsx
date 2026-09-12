import {
  SUMMARIZATION_METHOD_LABELS,
  type DocumentSummary,
  type DocumentSummaryRecord,
  type SummarizationMethod,
} from "@/api/types";
import { ModelSwatch } from "@/components/ModelSwatch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { colorForModel } from "@/lib/modelColors";

export function SummarizationResultsTable({
  documents,
  resultsByMethod,
}: {
  documents: DocumentSummary[];
  resultsByMethod: Partial<Record<SummarizationMethod, DocumentSummaryRecord[]>>;
}) {
  const methods = Object.keys(resultsByMethod) as SummarizationMethod[];
  const resultByDocument = new Map(
    methods.map((method) => [
      method,
      new Map((resultsByMethod[method] ?? []).map((result) => [result.document_id, result])),
    ]),
  );

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Документ</TableHead>
          {methods.map((method) => (
            <TableHead key={method} className="text-right">
              <ModelSwatch label={SUMMARIZATION_METHOD_LABELS[method]} color={colorForModel(method)} />
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {documents.map((doc) => (
          <TableRow key={doc.id}>
            <TableCell className="max-w-xs truncate">
              {doc.url ? (
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
              )}
            </TableCell>
            {methods.map((method) => {
              const result = resultByDocument.get(method)?.get(doc.id);
              return (
                <TableCell key={method} className="text-right tabular-nums">
                  {result ? (
                    `${result.summary_sentence_indices.length}/${result.total_sentences} · ${result.elapsed_ms.toFixed(0)} мс`
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </TableCell>
              );
            })}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
