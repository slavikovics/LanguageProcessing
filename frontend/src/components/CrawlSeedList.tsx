import { FileStack, Globe, Layers, Lock, Pencil, X } from "lucide-react";
import type { CrawlJob, CrawlSeed } from "../api/types";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { STATUS_BADGE_CLASS, STATUS_LABELS } from "@/lib/crawlJobStatus";
import { cn } from "@/lib/utils";

export function CrawlSeedList({
  seeds,
  loading,
  latestJobBySeedUrl,
  editingSeedId,
  onEdit,
  onDelete,
  deletingSeedId,
}: {
  seeds: CrawlSeed[];
  loading: boolean;
  latestJobBySeedUrl: Map<string, CrawlJob>;
  editingSeedId: number | null;
  onEdit: (seed: CrawlSeed) => void;
  onDelete: (seed: CrawlSeed) => void;
  deletingSeedId: number | null;
}) {
  return (
    <div className="flex min-h-40 w-full flex-col rounded-md border">
      {loading ? (
        <p className="flex flex-1 items-center justify-center px-6 py-8 text-center text-xs text-muted-foreground">
          Загрузка…
        </p>
      ) : seeds.length === 0 ? (
        <p className="flex flex-1 items-center justify-center px-6 py-8 text-center text-xs text-muted-foreground">
          Добавьте хотя бы один адрес, чтобы начать обход.
        </p>
      ) : (
        <ScrollArea className="h-40 min-w-0">
          <div className="min-w-0 divide-y">
            {seeds.map((seed, index) => {
              const lastJob = latestJobBySeedUrl.get(seed.url);
              return (
                <div
                  key={seed.id}
                  className={cn(
                    "flex items-center gap-2 px-3 py-2 text-xs transition-colors duration-150 hover:bg-muted/50",
                    editingSeedId === seed.id && "bg-accent/60",
                  )}
                >
                  <span className="w-5 shrink-0 text-muted-foreground">{index + 1}.</span>
                  <span className="min-w-0 flex-1 truncate" title={seed.url}>
                    {seed.url}
                  </span>
                  <span className="hidden shrink-0 items-center gap-1 sm:flex">
                    <Badge variant="outline" className="gap-1 text-[10px]">
                      <Globe className="size-3" />
                      {seed.language.toUpperCase()}
                    </Badge>
                    <Badge variant="outline" className="gap-1 text-[10px]">
                      <FileStack className="size-3" />
                      {seed.max_documents}
                    </Badge>
                    <Badge variant="outline" className="gap-1 text-[10px]">
                      <Layers className="size-3" />
                      {seed.max_depth}
                    </Badge>
                    {seed.same_domain_only && (
                      <Badge variant="outline" className="gap-1 text-[10px]">
                        <Lock className="size-3" />
                        домен
                      </Badge>
                    )}
                    {lastJob && (
                      <Badge
                        variant="outline"
                        className={cn("gap-1 text-[10px]", STATUS_BADGE_CLASS[lastJob.status])}
                        title={
                          lastJob.finished_at
                            ? `Последний запуск: ${new Date(lastJob.finished_at).toLocaleString()}`
                            : undefined
                        }
                      >
                        {STATUS_LABELS[lastJob.status]}
                      </Badge>
                    )}
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => onEdit(seed)}
                    aria-label="Редактировать адрес"
                    className="shrink-0 text-muted-foreground transition-all duration-150 hover:scale-110 hover:text-primary active:scale-95"
                  >
                    <Pencil className="size-3.5" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => onDelete(seed)}
                    disabled={deletingSeedId === seed.id}
                    aria-label="Удалить адрес"
                    className="shrink-0 text-muted-foreground transition-all duration-150 hover:scale-110 hover:text-destructive active:scale-95"
                  >
                    <X className="size-3.5" />
                  </Button>
                </div>
              );
            })}
          </div>
        </ScrollArea>
      )}
    </div>
  );
}
