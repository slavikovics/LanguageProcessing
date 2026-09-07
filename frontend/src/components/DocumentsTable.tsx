import { Pencil, Trash2 } from "lucide-react";
import type { DocumentSummary } from "../api/types";

import { Button } from "@/components/ui/button";
import { Pagination } from "@/components/ui/pagination";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export function DocumentsTable({
  documents,
  loading,
  page,
  totalPages,
  onPageChange,
  onEdit,
  onDelete,
  deletingId,
}: {
  documents: DocumentSummary[];
  loading: boolean;
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onEdit: (doc: DocumentSummary) => void;
  onDelete: (doc: DocumentSummary) => void;
  deletingId: number | null;
}) {
  if (loading) {
    return <p className="text-sm text-muted-foreground">Загрузка…</p>;
  }
  if (documents.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Документов пока нет — запустите краулинг на странице «Краулинг» или добавьте документ вручную.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Заголовок</TableHead>
            <TableHead>URL</TableHead>
            <TableHead className="w-24">Символов</TableHead>
            <TableHead className="w-40">Дата</TableHead>
            <TableHead className="w-20">Действия</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {documents.map((doc) => (
            <TableRow key={doc.id}>
              <TableCell className="max-w-xs truncate">{doc.title}</TableCell>
              <TableCell className="max-w-xs truncate">
                {doc.url ? (
                  <a
                    href={doc.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-primary underline-offset-2 hover:underline"
                  >
                    {doc.url}
                  </a>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </TableCell>
              <TableCell>{doc.char_count}</TableCell>
              <TableCell>{new Date(doc.fetched_at).toLocaleString()}</TableCell>
              <TableCell className="text-right">
                <div className="flex justify-end gap-1">
                  <Button type="button" variant="ghost" size="icon-sm" onClick={() => onEdit(doc)} aria-label="Редактировать">
                    <Pencil className="size-3.5" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => onDelete(doc)}
                    disabled={deletingId === doc.id}
                    aria-label="Удалить"
                    className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-1">
          <span className="text-xs text-muted-foreground">
            Страница {page + 1} из {totalPages}
          </span>
          <Pagination page={page} totalPages={totalPages} onPageChange={onPageChange} />
        </div>
      )}
    </div>
  );
}
