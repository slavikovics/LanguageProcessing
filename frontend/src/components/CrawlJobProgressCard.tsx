import { Square } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { cancelCrawlJob } from "../api/client";
import { TERMINAL_CRAWL_STATUSES } from "../api/types";
import { useCrawlJobProgress } from "../hooks/useCrawlJobProgress";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ProgressBar } from "@/components/ProgressBar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useCollectionContext } from "@/context/CollectionContext";
import { STATUS_BADGE_CLASS, STATUS_LABELS } from "@/lib/crawlJobStatus";
import { cn } from "@/lib/utils";

const URL_STATUS_COLOR: Record<string, string> = {
  success: "text-emerald-600 dark:text-emerald-400",
  failed: "text-destructive",
  skipped: "text-destructive",
};

export function CrawlJobProgressCard({ jobId }: { jobId: number }) {
  const { refreshCollections } = useCollectionContext();
  const { progress } = useCrawlJobProgress(jobId);
  const [cancelling, setCancelling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  // The document count shown in the header switcher is fetched once on
  // load; without this the "Индексировать" button on Collections stays
  // disabled (0 documents) until a manual page reload.
  useEffect(() => {
    if (progress?.job.status === "completed") {
      void refreshCollections();
    }
  }, [progress?.job.status, refreshCollections]);

  if (!progress) return null;

  const isActive = progress.job.status === "pending" || progress.job.status === "running";

  async function handleCancel() {
    setCancelling(true);
    setCancelError(null);
    try {
      await cancelCrawlJob(jobId);
    } catch (err) {
      setCancelError(err instanceof Error ? err.message : String(err));
    } finally {
      setCancelling(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <CardTitle className="flex items-center gap-2">
            <span>Задача #{progress.job.id}</span>
            <Badge variant="outline" className={STATUS_BADGE_CLASS[progress.job.status]}>
              {STATUS_LABELS[progress.job.status]}
            </Badge>
          </CardTitle>
          <div className="flex shrink-0 items-center gap-3">
            <p className="text-right text-xs text-muted-foreground">
              Посещено: {progress.job.urls_visited} · В очереди: {progress.job.urls_queued} · Ошибок:{" "}
              {progress.job.urls_failed}
            </p>
            {isActive && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleCancel}
                disabled={cancelling}
                className="text-destructive hover:bg-destructive/10 hover:text-destructive"
              >
                <Square className="size-3.5" />
                {cancelling ? "Прерывание…" : "Прервать"}
              </Button>
            )}
          </div>
        </div>
        {cancelError && <p className="text-sm text-destructive">{cancelError}</p>}
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <span className="max-w-full truncate text-xs text-muted-foreground" title={progress.job.seed_urls[0]}>
          {progress.job.seed_urls[0]}
        </span>

        <ProgressBar
          value={progress.job.documents_fetched}
          max={progress.job.max_documents}
          complete={TERMINAL_CRAWL_STATUSES.includes(progress.job.status)}
        />

        {progress.job.error_message && (
          <p className="text-sm text-destructive">{progress.job.error_message}</p>
        )}

        {progress.job.status === "completed" && (
          <div className="flex items-center gap-2 rounded-md border border-emerald-600/30 bg-emerald-600/5 px-3 py-2 text-sm dark:border-emerald-400/30">
            <span>Готово: {progress.job.documents_fetched} документов сохранено.</span>
            <Button asChild size="sm" variant="secondary" className="ml-auto shrink-0">
              <Link to="/collections">К индексации</Link>
            </Button>
          </div>
        )}

        <div>
          <h3 className="mb-2 text-xs font-medium text-muted-foreground">Последние URL</h3>
          <ScrollArea className="h-56 rounded-md border">
            <ul className="flex flex-col gap-0.5 p-2">
              {progress.recent_urls.map((u) => (
                <li
                  key={u.id}
                  className="flex items-baseline gap-2 rounded px-2 py-1 text-xs transition-colors duration-150 hover:bg-muted"
                >
                  <span className={cn("shrink-0 font-semibold uppercase", URL_STATUS_COLOR[u.status])}>
                    {u.status}
                  </span>
                  <span className="shrink-0 text-muted-foreground">d{u.depth}</span>
                  <span className="min-w-0 flex-1 truncate" title={u.url}>
                    {u.url}
                  </span>
                  {u.error && (
                    <span className="max-w-[35%] shrink-0 truncate text-destructive" title={u.error}>
                      {u.error}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </ScrollArea>
        </div>
      </CardContent>
    </Card>
  );
}
