import { useEffect, useState } from "react";

const POLL_INTERVAL_MS = 1000;

interface UseJobProgressOptions<T> {
  fetchJob: (jobId: number) => Promise<T>;
  wsUrl: (jobId: number) => string;
  isTerminal: (data: T) => boolean;
}

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
        } catch {}
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
      } catch {}
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
