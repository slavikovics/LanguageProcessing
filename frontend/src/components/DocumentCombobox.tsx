import { Check, ChevronsUpDown, Loader2, Search, X } from "lucide-react";
import { useEffect, useState } from "react";

import { listDocuments } from "@/api/client";
import type { DocumentSummary } from "@/api/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

const RESULT_LIMIT = 30;
const SEARCH_DEBOUNCE_MS = 250;

/**
 * Server-searched document picker: fetches only a page of title-matching
 * documents per keystroke instead of loading (and rendering) the whole
 * collection, so it stays fast whether the collection has 20 or 20 000
 * documents. `value` of `null` means "no document" — pass `null` to
 * `onChange` (via the clear button) to go back to that state.
 */
export function DocumentCombobox({
  collectionId,
  value,
  onChange,
  placeholder = "Выберите документ",
  id,
}: {
  collectionId: number;
  value: DocumentSummary | null;
  onChange: (document: DocumentSummary | null) => void;
  placeholder?: string;
  id?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    const handle = setTimeout(
      () => {
        listDocuments(collectionId, { limit: RESULT_LIMIT, search: query || undefined })
          .then((docs) => {
            if (!cancelled) setResults(docs);
          })
          .finally(() => {
            if (!cancelled) setLoading(false);
          });
      },
      query ? SEARCH_DEBOUNCE_MS : 0,
    );
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
  }, [collectionId, query, open]);

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          id={id}
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between font-normal"
        >
          <span className="truncate">{value ? value.title : placeholder}</span>
          <span className="flex shrink-0 items-center gap-1">
            {value && (
              <span
                role="button"
                tabIndex={0}
                aria-label="Очистить выбор документа"
                className="flex size-5 items-center justify-center rounded-sm text-muted-foreground hover:bg-accent hover:text-foreground"
                onPointerDown={(event) => event.stopPropagation()}
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  onChange(null);
                }}
              >
                <X className="size-4" />
              </span>
            )}
            <ChevronsUpDown className="size-4 opacity-50" />
          </span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-(--radix-popover-trigger-width) p-0" align="start">
        <div className="flex items-center gap-2 border-b px-3 py-2">
          <Search className="size-4 shrink-0 text-muted-foreground" />
          <Input
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Поиск по названию…"
            className="h-8 border-0 px-1 shadow-none focus-visible:ring-0"
          />
          {loading && <Loader2 className="size-4 shrink-0 animate-spin text-muted-foreground" />}
        </div>
        <ScrollArea className="h-72">
          <div className="p-1">
            {!loading && results.length === 0 && (
              <p className="px-2 py-4 text-center text-sm text-muted-foreground">
                {query ? "Ничего не найдено" : "В коллекции нет документов"}
              </p>
            )}
            {results.map((doc) => (
              <button
                key={doc.id}
                type="button"
                onClick={() => {
                  onChange(doc);
                  setOpen(false);
                }}
                className={cn(
                  "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm hover:bg-accent hover:text-accent-foreground",
                  doc.id === value?.id && "bg-accent/50",
                )}
              >
                <Check className={cn("size-4 shrink-0", doc.id === value?.id ? "opacity-100" : "opacity-0")} />
                <span className="truncate">{doc.title}</span>
              </button>
            ))}
            {results.length === RESULT_LIMIT && (
              <p className="px-2 py-1.5 text-xs text-muted-foreground">
                Показаны первые {RESULT_LIMIT} — уточните поиск, чтобы найти другой документ
              </p>
            )}
          </div>
        </ScrollArea>
      </PopoverContent>
    </Popover>
  );
}
