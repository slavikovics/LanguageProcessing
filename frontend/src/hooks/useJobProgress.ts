import { useEffect, useState } from "react";

const POLL_INTERVAL_MS = 1000;

interface UseJobProgressOptions<T> {
  fetchJob: (jobId: number) => Promise<T>;
  wsUrl: (jobId: number) => string;
  isTerminal: (data: T) => boolean;
}

/** Subscribes over WebSocket for job progress; falls back to REST polling
 * of the equivalent GET endpoint if the socket can't connect or drops. */
export function useJobProgress<T>(jobId: number | null, options: UseJobProgressOptions<T>) {
  const [progress, setProgress] = useState<T | null>(null);
  const [connection, setConnection] = useState<"websocket" | "polling" | "idle">("idle");

  useEffect(() => {
    if (jobId === null) {
      setProgress(null);
      setConnection("idle");
      return;
    }

    let cancelled = false;
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    const socket = new WebSocket(options.wsUrl(jobId));

    const startPolling = () => {
      if (pollTimer !== null || cancelled) return;
      setConnection("polling");
      const poll = async () => {
        try {
          const data = await options.fetchJob(jobId);
          if (cancelled) return;
          setProgress(data);
          if (options.isTerminal(data) && pollTimer !== null) {
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
        const data = JSON.parse(event.data) as T | { error: string };
        if (data && typeof data === "object" && "error" in data) return;
        setProgress(data as T);
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  return { progress, connection };
}
