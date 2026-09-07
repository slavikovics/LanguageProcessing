import { Badge } from "@/components/ui/badge";
import { ModelSwatch } from "@/components/ModelSwatch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { colorForModel } from "@/lib/modelColors";
import { LANG_ID_METHOD_LABELS, type DocumentSummary, type LangIdMethod, type LangIdResult } from "../api/types";

export function LangIdResultsTable({
  documents,
  resultsByMethod,
}: {
  documents: DocumentSummary[];
  resultsByMethod: Partial<Record<LangIdMethod, LangIdResult[]>>;
}) {
  const methods = Object.keys(resultsByMethod) as LangIdMethod[];
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
          <TableHead>Истинный язык</TableHead>
          {methods.map((method) => (
            <TableHead key={method} className="text-right">
              <ModelSwatch label={LANG_ID_METHOD_LABELS[method]} color={colorForModel(method)} />
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
            <TableCell>{doc.confirmed_language?.toUpperCase() ?? "—"}</TableCell>
            {methods.map((method) => {
              const result = resultByDocument.get(method)?.get(doc.id);
              return (
                <TableCell key={method} className="text-right">
                  {result ? (
                    <Badge variant={result.is_correct ? "default" : "destructive"}>
                      {result.predicted_language.toUpperCase()}
                    </Badge>
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
