import type { Key, ReactNode } from "react";

import { Pagination } from "@/components/ui/pagination";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export interface PagedTableColumn<T> {
  key: string;
  header: ReactNode;
  render: (row: T, rowIndex: number) => ReactNode;
  align?: "left" | "center";
  className?: string;
}

export function PagedTable<T>({
  columns,
  rows,
  getRowKey,
  onRowClick,
  page,
  totalPages,
  onPageChange,
  totalCount,
  totalLabel = "Всего:",
  loading = false,
  emptyMessage = "Нет данных",
}: {
  columns: PagedTableColumn<T>[];
  rows: T[];
  getRowKey: (row: T, index: number) => Key;
  onRowClick?: (row: T, index: number) => void;
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  totalCount: number;
  totalLabel?: string;
  loading?: boolean;
  emptyMessage?: string;
}) {
  return (
    <div className="flex flex-col gap-3">
      {loading && <p className="text-sm text-muted-foreground">Загрузка…</p>}
      {!loading && (
        <Table className="table-fixed">
          <TableHeader>
            <TableRow>
              {columns.map((col) => (
                <TableHead key={col.key} className={col.className}>
                  {col.header}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row, index) => (
              <TableRow
                key={getRowKey(row, index)}
                className={onRowClick ? "cursor-pointer" : undefined}
                onClick={onRowClick ? () => onRowClick(row, index) : undefined}
              >
                {columns.map((col) => (
                  <TableCell
                    key={col.key}
                    className={`${col.align === "left" ? "text-left" : "text-center"} ${
                      col.align === "left" ? "truncate" : ""
                    } ${col.className ?? ""}`}
                  >
                    {col.render(row, index)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
            {rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={columns.length} className="text-center text-muted-foreground">
                  {emptyMessage}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground">
          {totalLabel} {totalCount}
        </p>
        <Pagination page={page} totalPages={Math.max(1, totalPages)} onPageChange={onPageChange} />
      </div>
    </div>
  );
}
