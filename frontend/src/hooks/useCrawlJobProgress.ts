import { useEffect, useState } from "react";
import { crawlJobWebSocketUrl, getCrawlJob } from "../api/client";
import { TERMINAL_CRAWL_STATUSES, type CrawlJobProgress } from "../api/types";

const POLL_INTERVAL_MS = 1000;

/**
 * Live crawl-job progress: subscribes over WebSocket (the api service
 * pushes diffs by polling crawl_jobs/crawl_urls, see docs/PROJECT_PLAN.md
 * 3.1); if the socket cannot connect or drops, falls back to plain REST
 * polling of the same GET /crawl-jobs/{id} endpoint so the progress bar
 * keeps moving either way.
 */
export function useCrawlJobProgress(jobId: number | null) {
  const [progress, setProgress] = useState<CrawlJobProgress | null>(null);
  const [connection, setConnection] = useState<"websocket" | "polling" | "idle">("idle");

  useEffect(() => {
    if (jobId === null) {
      setProgress(null);
      setConnection("idle");
      return;
    }

    let cancelled = false;
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    const socket = new WebSocket(crawlJobWebSocketUrl(jobId));

    const startPolling = () => {
      if (pollTimer !== null || cancelled) return;
      setConnection("polling");
      const poll = async () => {
        try {
          const data = await getCrawlJob(jobId);
          if (cancelled) return;
          setProgress(data);
          if (TERMINAL_CRAWL_STATUSES.includes(data.job.status) && pollTimer !== null) {
            clearInterval(pollTimer);
            pollTimer = null;
          }
        } catch {
          // transient network error - next tick will retry
        }
      };
      void poll();
      pollTimer = setInterval(poll, POLL_INTERVAL_MS);
    };

    socket.onopen = () => {
      if (!cancelled) setConnection("websocket");
    };
    socket.onmessage = (event) => {
      if (cancelled) return;
      try {
        const data = JSON.parse(event.data) as CrawlJobProgress | { error: string };
        if ("error" in data) return;
        setProgress(data);
      } catch {
        // ignore malformed frame
      }
    };
    socket.onerror = () => {
      socket.close();
    };
    socket.onclose = () => {
      if (!cancelled) startPolling();
    };

    return () => {
      cancelled = true;
      socket.close();
      if (pollTimer !== null) clearInterval(pollTimer);
    };
  }, [jobId]);

  return { progress, connection };
}
