import { HelpCircle, Plus, RefreshCw, RotateCw, Square, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { cancelCrawlJob, cancelIndexJob, createIndexJob, deleteCollection, refreshCollection } from "../api/client";
import type { Collection } from "../api/types";
import { useCrawlJobProgress } from "../hooks/useCrawlJobProgress";
import { useIndexJobProgress } from "../hooks/useIndexJobProgress";

import { ProgressBar } from "@/components/ProgressBar";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useCollectionContext } from "@/context/CollectionContext";

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex flex-col items-center text-center">
      <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">{label}</span>
      <span className="text-2xl leading-tight font-semibold tracking-tight tabular-nums">{value}</span>
    </div>
  );
}

/** Stats + index/refresh/delete actions for the selected collection, with
 * their own live-progress tracking. Fetches the collection's document
 * count and index status itself via context rather than the page passing
 * them down, since this card is the only consumer of that state. */
export function CollectionHeaderCard({
  collection,
  onDocumentsChanged,
  onAddDocument,
}: {
  collection: Collection;
  onDocumentsChanged: () => void;
  onAddDocument: () => void;
}) {
  const { latestIndexJob, refreshIndexStatus, refreshCollections, isIndexing } = useCollectionContext();

  const [indexError, setIndexError] = useState<string | null>(null);
  const [activeJobId, setActiveJobId] = useState<number | null>(null);
  const { progress: liveJob } = useIndexJobProgress(activeJobId);
  const [cancellingIndex, setCancellingIndex] = useState(false);

  const [refreshJobId, setRefreshJobId] = useState<number | null>(null);
  const { progress: refreshProgress } = useCrawlJobProgress(refreshJobId);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [cancellingRefresh, setCancellingRefresh] = useState(false);

  const [deletingCollection, setDeletingCollection] = useState(false);

  // Picks up an already-running job (e.g. left running from another tab) so
  // the progress bar shows live state as soon as the page opens.
  useEffect(() => {
    if (latestIndexJob && (latestIndexJob.status === "pending" || latestIndexJob.status === "running")) {
      setActiveJobId(latestIndexJob.id);
    }
  }, [latestIndexJob]);

  useEffect(() => {
    if (liveJob && (liveJob.status === "completed" || liveJob.status === "failed")) {
      void refreshIndexStatus();
      setActiveJobId(null);
    }
  }, [liveJob, refreshIndexStatus]);

  useEffect(() => {
    if (refreshProgress && ["completed", "failed", "cancelled"].includes(refreshProgress.job.status)) {
      void refreshCollections();
      onDocumentsChanged();
      setRefreshJobId(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshProgress]);

  async function handleIndex() {
    setIndexError(null);
    try {
      const job = await createIndexJob(collection.id);
      setActiveJobId(job.id);
      void refreshIndexStatus();
    } catch (err) {
      setIndexError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleRefreshCollection() {
    setRefreshError(null);
    try {
      const job = await refreshCollection(collection.id);
      setRefreshJobId(job.id);
    } catch (err) {
      setRefreshError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleCancelIndex(jobId: number) {
    setCancellingIndex(true);
    setIndexError(null);
    try {
      await cancelIndexJob(jobId);
    } catch (err) {
      setIndexError(err instanceof Error ? err.message : String(err));
    } finally {
      setCancellingIndex(false);
    }
  }

  async function handleCancelRefresh(jobId: number) {
    setCancellingRefresh(true);
    setRefreshError(null);
    try {
      await cancelCrawlJob(jobId);
    } catch (err) {
      setRefreshError(err instanceof Error ? err.message : String(err));
    } finally {
      setCancellingRefresh(false);
    }
  }

  async function handleDeleteCollection() {
    if (
      !window.confirm(
        `Удалить коллекцию «${collection.name}» вместе со всеми документами, индексом и историей запросов? Это действие необратимо.`,
      )
    ) {
      return;
    }
    setDeletingCollection(true);
    try {
      await deleteCollection(collection.id);
      await refreshCollections();
    } catch (err) {
      window.alert(err instanceof Error ? err.message : String(err));
    } finally {
      setDeletingCollection(false);
    }
  }

  const displayedJob = liveJob ?? latestIndexJob;
  const isRefreshing =
    refreshProgress !== null && !["completed", "failed", "cancelled"].includes(refreshProgress.job.status);
  const isStale =
    displayedJob?.status === "completed" &&
    displayedJob.finished_at !== null &&
    collection.documents_changed_at !== null &&
    new Date(collection.documents_changed_at) > new Date(displayedJob.finished_at);

  return (
    <Card className="relative py-4">
      <Button
        asChild
        variant="ghost"
        size="icon-sm"
        aria-label="Справка о коллекциях"
        className="absolute top-3 right-3 text-muted-foreground"
      >
        <Link to="/help#collections">
          <HelpCircle className="size-4" />
        </Link>
      </Button>
      <CardContent className="flex flex-col items-center gap-3">
        <div className="mx-auto flex w-full flex-wrap items-start justify-center gap-x-12 gap-y-5">
          <Stat label="Коллекция" value={collection.name} />
          <Stat label="Документов" value={collection.document_count} />
          <Stat
            label="Терминов в индексе"
            value={displayedJob?.status === "completed" ? (displayedJob.terms_indexed ?? "—") : "—"}
          />
          <Stat
            label="Последняя индексация"
            value={
              displayedJob?.status === "completed" && displayedJob.finished_at
                ? new Date(displayedJob.finished_at).toLocaleString()
                : "не выполнялась"
            }
          />
        </div>
        {isStale && !isIndexing && (
          <span className="text-xs text-amber-600 dark:text-amber-400">
            Документы менялись после индексации — результаты поиска могут быть неточными.
          </span>
        )}
        {indexError && <p className="text-xs text-destructive">{indexError}</p>}
        {refreshError && <p className="text-xs text-destructive">{refreshError}</p>}
      </CardContent>

      <CardContent className="flex flex-wrap items-center justify-center gap-2 border-t pt-4">
        <Button
          type="button"
          variant="outline"
          onClick={handleDeleteCollection}
          disabled={deletingCollection || isIndexing || isRefreshing}
          title={isIndexing ? "Коллекция сейчас индексируется" : undefined}
          className="text-destructive hover:bg-destructive/10 hover:text-destructive"
        >
          <Trash2 className="size-4" />
          {deletingCollection ? "Удаление…" : "Удалить коллекцию"}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={handleRefreshCollection}
          disabled={isRefreshing || isIndexing || collection.document_count === 0}
          title={isIndexing ? "Коллекция сейчас индексируется" : undefined}
        >
          <RefreshCw className="size-4" />
          {isRefreshing ? "Обновление…" : "Обновить"}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={handleIndex}
          disabled={isIndexing || collection.document_count === 0}
        >
          <RotateCw className="size-4" />
          {isIndexing ? "Индексация…" : "Переиндексировать"}
        </Button>
        <Button type="button" onClick={onAddDocument}>
          <Plus className="size-4" />
          Добавить документ
        </Button>
      </CardContent>

      {isIndexing && displayedJob && (
        <CardContent className="flex flex-col gap-2 border-t pt-4">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-muted-foreground">
              {displayedJob.status === "pending"
                ? "Задача поставлена в очередь…"
                : `Обработано документов: ${displayedJob.documents_processed} из ${displayedJob.documents_total}`}
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => handleCancelIndex(displayedJob.id)}
              disabled={cancellingIndex}
              className="shrink-0 text-destructive hover:bg-destructive/10 hover:text-destructive"
            >
              <Square className="size-3.5" />
              {cancellingIndex ? "Прерывание…" : "Прервать"}
            </Button>
          </div>
          <ProgressBar
            value={displayedJob.documents_processed}
            max={Math.max(displayedJob.documents_total, 1)}
          />
        </CardContent>
      )}
      {displayedJob?.status === "failed" && (
        <CardContent className="border-t pt-4">
          <p className="text-sm text-destructive">Ошибка индексации: {displayedJob.error_message}</p>
        </CardContent>
      )}
      {displayedJob?.status === "cancelled" && (
        <CardContent className="border-t pt-4">
          <p className="text-sm text-muted-foreground">Индексация прервана.</p>
        </CardContent>
      )}
      {isRefreshing && refreshProgress && (
        <CardContent className="flex flex-col gap-2 border-t pt-4">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-muted-foreground">
              Перезагружено документов: {refreshProgress.job.documents_fetched} из{" "}
              {refreshProgress.job.max_documents}
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => handleCancelRefresh(refreshProgress.job.id)}
              disabled={cancellingRefresh}
              className="shrink-0 text-destructive hover:bg-destructive/10 hover:text-destructive"
            >
              <Square className="size-3.5" />
              {cancellingRefresh ? "Прерывание…" : "Прервать"}
            </Button>
          </div>
          <ProgressBar
            value={refreshProgress.job.documents_fetched}
            max={Math.max(refreshProgress.job.max_documents, 1)}
          />
        </CardContent>
      )}
    </Card>
  );
}
