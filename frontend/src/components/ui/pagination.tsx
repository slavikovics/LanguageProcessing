import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, MoreHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";

function getPageNumbers(current: number, total: number): (number | "ellipsis")[] {
  const keep = new Set<number>([1, total, current - 1, current, current + 1]);
  const sorted = [...keep].filter((p) => p >= 1 && p <= total).sort((a, b) => a - b);

  const pages: (number | "ellipsis")[] = [];
  let prev = 0;
  for (const p of sorted) {
    if (prev && p - prev > 1) pages.push("ellipsis");
    pages.push(p);
    prev = p;
  }
  return pages;
}

export function Pagination(
  {
    page,
    totalPages,
    onPageChange,
  }: {
    page: number
    totalPages: number;
    onPageChange: (page: number) => void;
  }
) {
  const current = page + 1;
  const items = getPageNumbers(current, totalPages);
  const isFirst = page === 0;
  const isLast = page + 1 >= totalPages;

  return (
    <nav className="flex items-center justify-center gap-1" aria-label="Пагинация">
      <Button
        type="button"
        variant="outline"
        size="icon-sm"
        onClick={() => onPageChange(0)}
        disabled={isFirst}
        aria-label="Первая страница"
      >
        <ChevronsLeft className="size-4" />
      </Button>
      <Button
        type="button"
        variant="outline"
        size="icon-sm"
        onClick={() => onPageChange(page - 1)}
        disabled={isFirst}
        aria-label="Предыдущая страница"
      >
        <ChevronLeft className="size-4" />
      </Button>

      {items.map((it, i) =>
        it === "ellipsis" ? (
          <span
            key={`ellipsis-${i}`}
            className="flex size-8 shrink-0 items-center justify-center text-muted-foreground"
          >
            <MoreHorizontal className="size-4" />
          </span>
        ) : (
          <Button
            key={it}
            type="button"
            variant={it === current ? "default" : "outline"}
            size="icon-sm"
            onClick={() => onPageChange(it - 1)}
            aria-current={it === current ? "page" : undefined}
            className="tabular-nums"
          >
            {it}
          </Button>
        ),
      )}

      <Button
        type="button"
        variant="outline"
        size="icon-sm"
        onClick={() => onPageChange(page + 1)}
        disabled={isLast}
        aria-label="Следующая страница"
      >
        <ChevronRight className="size-4" />
      </Button>
      <Button
        type="button"
        variant="outline"
        size="icon-sm"
        onClick={() => onPageChange(totalPages - 1)}
        disabled={isLast}
        aria-label="Последняя страница"
      >
        <ChevronsRight className="size-4" />
      </Button>
    </nav>
  );
}
