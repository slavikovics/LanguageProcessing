import { Check, ChevronDown, Plus } from "lucide-react";
import { useState, type FormEvent, type KeyboardEvent } from "react";

import { createCollection } from "@/api/client";
import type { IndexJobStatus } from "@/api/types";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { useCollectionContext } from "@/context/CollectionContext";
import { cn } from "@/lib/utils";

const STATUS_DOT: Record<IndexJobStatus, string> = {
  pending: "bg-primary",
  running: "bg-primary animate-pulse",
  completed: "bg-emerald-500",
  failed: "bg-destructive",
  cancelled: "bg-destructive",
};

const STATUS_LABEL: Record<IndexJobStatus, string> = {
  pending: "в очереди",
  running: "индексация…",
  completed: "проиндексировано",
  failed: "ошибка индексации",
  cancelled: "индексация прервана",
};

/** Single source of "what am I working with right now": picks the active
 * collection, shows its indexing status at a glance, and creates new
 * collections — everything else (Crawl/Search/Metrics) just reads this. */
export function CollectionSwitcher() {
  const { collections, selectedId, selected, setSelectedId, refreshCollections, latestIndexJob, loading } =
    useCollectionContext();
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (!next) {
      setCreating(false);
      setError(null);
      setName("");
    }
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const created = await createCollection({ name: name.trim(), language: "en" });
      await refreshCollections();
      setSelectedId(created.id);
      setOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  const noDocs = selected ? selected.document_count === 0 : false;
  const isStale =
    !!selected &&
    latestIndexJob?.status === "completed" &&
    latestIndexJob.finished_at !== null &&
    selected.documents_changed_at !== null &&
    new Date(selected.documents_changed_at) > new Date(latestIndexJob.finished_at);

  const statusText = !selected
    ? null
    : noDocs
      ? "нет документов"
      : isStale
        ? "индекс устарел"
        : latestIndexJob
          ? STATUS_LABEL[latestIndexJob.status]
          : "не проиндексировано";
  const dotClass =
    !selected || noDocs
      ? "bg-muted-foreground/40"
      : isStale
        ? "bg-amber-500"
        : latestIndexJob
          ? STATUS_DOT[latestIndexJob.status]
          : "bg-amber-500";

  return (
    <DropdownMenu open={open} onOpenChange={handleOpenChange}>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" className="h-10 gap-2.5 rounded-lg pl-3 pr-2.5">
          <span className={cn("size-2 shrink-0 rounded-full", dotClass)} />
          <span className="flex flex-col items-start leading-tight">
            <span className="max-w-40 truncate text-sm font-medium">
              {loading ? "Загрузка…" : (selected?.name ?? "Нет коллекций")}
            </span>
            {statusText && <span className="text-[11px] text-muted-foreground">{statusText}</span>}
          </span>
          <ChevronDown className="size-4 text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-72">
        {collections.length === 0 && (
          <p className="px-2 py-3 text-center text-sm text-muted-foreground">Пока нет коллекций</p>
        )}
        {collections.map((c) => (
          <DropdownMenuItem key={c.id} onSelect={() => setSelectedId(c.id)} className="justify-between">
            <span className="min-w-0 flex-1 truncate" title={c.name}>
              {c.name}
            </span>
            <span className="flex shrink-0 items-center gap-1.5 text-xs text-muted-foreground">
              {c.document_count}
              {c.id === selectedId && <Check className="size-3.5 text-foreground" />}
            </span>
          </DropdownMenuItem>
        ))}

        <DropdownMenuSeparator />

        {!creating ? (
          <DropdownMenuItem
            onSelect={(event) => {
              event.preventDefault();
              setCreating(true);
            }}
          >
            <Plus className="size-4" />
            Новая коллекция
          </DropdownMenuItem>
        ) : (
          <form
            onSubmit={handleCreate}
            className="flex items-center gap-1.5 p-1.5"
            onKeyDown={(event: KeyboardEvent) => event.stopPropagation()}
          >
            <Input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Название коллекции"
              className="h-8"
            />
            <Button type="submit" size="sm" disabled={submitting} className="shrink-0">
              {submitting ? "…" : "OK"}
            </Button>
          </form>
        )}
        {error && <p className="px-2 pb-1 text-xs text-destructive">{error}</p>}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
