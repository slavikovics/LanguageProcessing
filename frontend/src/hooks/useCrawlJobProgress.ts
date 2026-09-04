import { crawlJobWebSocketUrl, getCrawlJob } from "../api/client";
import { TERMINAL_CRAWL_STATUSES, type CrawlJobProgress } from "../api/types";
import { useJobProgress } from "./useJobProgress";

export function useCrawlJobProgress(jobId: number | null) {
  return useJobProgress<CrawlJobProgress>(jobId, {
    fetchJob: getCrawlJob,
    wsUrl: crawlJobWebSocketUrl,
    isTerminal: (data) => TERMINAL_CRAWL_STATUSES.includes(data.job.status),
  });
}
