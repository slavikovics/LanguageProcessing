import type { CrawlJob } from "@/api/types";

export const STATUS_LABELS: Record<CrawlJob["status"], string> = {
  pending: "в очереди",
  running: "выполняется",
  completed: "завершён",
  failed: "ошибка",
  cancelled: "отменён",
};

export const STATUS_BADGE_CLASS: Record<CrawlJob["status"], string> = {
  pending: "border-primary/40 text-primary",
  running: "border-primary/40 text-primary",
  completed: "border-emerald-600/40 text-emerald-600 dark:border-emerald-400/40 dark:text-emerald-400",
  failed: "border-destructive/40 text-destructive",
  cancelled: "border-destructive/40 text-destructive",
};
