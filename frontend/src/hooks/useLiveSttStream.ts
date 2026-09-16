import { useCallback, useRef, useState } from "react";
import { speechStreamWebSocketUrl } from "@/api/client";
import type { SpeechCommand } from "@/api/types";
import { attachVolumeMeter } from "@/lib/micVolumeMeter";
import { PHRASE_PAUSE_MS } from "@/lib/speechTiming";

export type LiveSttUnavailableReason =
  | "unsupported_browser"
  | "mic_denied"
  | "connection_lost"
  | "mic_lost";

const SILENCE_LEVEL_THRESHOLD = 0.06;
// Must outlast backend's ~20s chunk ceiling plus cold-model-load time, or a slow final looks lost.
const STOP_SAFETY_NET_MS = 22000;

interface UseLiveSttStreamOptions {
  language?: string;
  chunkMs?: number;
  // Recorder stopped too soon after starting can yield a blob too short for the browser encoder to finalize.
  minChunkMs?: number;
  autoStopOnSilence?: boolean;
  silenceTimeoutMs?: number;
  matchCommands?: boolean;
  onPartial?: (chunkText: string, fullText: string) => void;
  onFinal?: (fullText: string, matchedCommand: SpeechCommand | null) => void;
  onError?: (detail: string) => void;
  onUnavailable?: (reason: LiveSttUnavailableReason) => void;
  onVolume?: (level: number) => void;
}

interface UseLiveSttStreamResult {
  isStreaming: boolean;
  start: () => Promise<boolean>;
  stop: () => void;
}

export function isLiveSttSupported(): boolean {
  return typeof MediaRecorder !== "undefined" && typeof WebSocket !== "undefined";
}

export function useLiveSttStream(options: UseLiveSttStreamOptions): UseLiveSttStreamResult {
  const {
    language,
    chunkMs = 3500,
    minChunkMs = 800,
    autoStopOnSilence = false,
    silenceTimeoutMs = PHRASE_PAUSE_MS,
    matchCommands = true,
    onPartial,
    onFinal,
    onError,
    onUnavailable,
    onVolume,
  } = options;
  const [isStreaming, setIsStreaming] = useState(false);

  // Refs (not closures) so already-open sessions pick up new callback props without a restart.
  const onPartialRef = useRef(onPartial);
  onPartialRef.current = onPartial;
  const onFinalRef = useRef(onFinal);
  onFinalRef.current = onFinal;
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;
  const onUnavailableRef = useRef(onUnavailable);
  onUnavailableRef.current = onUnavailable;
  const onVolumeRef = useRef(onVolume);
  onVolumeRef.current = onVolume;

  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const restartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const volumeMeterCleanupRef = useRef<(() => void) | null>(null);
  const silenceCheckIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastLoudAtRef = useRef(0);
  const hasSpokenRef = useRef(false);
  const stoppingRef = useRef(false);
  const gotFinalRef = useRef(false);
  const micLostRef = useRef(false);
  const chunkStartedAtRef = useRef(0);
  // Guards against overlapping start() calls before the first connects (seen: 7 sessions from rapid clicks).
  const activeRef = useRef(false);

  const cleanup = useCallback(() => {
    if (restartTimerRef.current !== null) {
      clearTimeout(restartTimerRef.current);
      restartTimerRef.current = null;
    }
    if (silenceCheckIntervalRef.current !== null) {
      clearInterval(silenceCheckIntervalRef.current);
      silenceCheckIntervalRef.current = null;
    }
    volumeMeterCleanupRef.current?.();
    volumeMeterCleanupRef.current = null;
    recorderRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    wsRef.current = null;
    activeRef.current = false;
    setIsStreaming(false);
  }, []);

  const reportMicLost = useCallback(() => {
    if (stoppingRef.current) return;
    stoppingRef.current = true;
    micLostRef.current = true;
    onUnavailableRef.current?.("mic_lost");
    wsRef.current?.close();
    cleanup();
  }, [cleanup]);

  const scheduleChunk = useCallback(() => {
    const stream = streamRef.current;
    const ws = wsRef.current;
    if (!stream || !ws) return;

    let recorder: MediaRecorder;
    try {
      recorder = new MediaRecorder(stream);
    } catch {
      // A stream whose track already ended throws synchronously here rather than firing an event.
      reportMicLost();
      return;
    }
    recorderRef.current = recorder;

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
        ws.send(event.data);
      }
    };
    recorder.onstop = () => {
      if (stoppingRef.current) {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "stop" }));
        }
        return;
      }
      scheduleChunk();
    };
    recorder.start();
    chunkStartedAtRef.current = Date.now();
    restartTimerRef.current = setTimeout(() => recorder.stop(), chunkMs);
  }, [chunkMs, reportMicLost]);

  const stop = useCallback(() => {
    stoppingRef.current = true;
    if (restartTimerRef.current !== null) {
      clearTimeout(restartTimerRef.current);
      restartTimerRef.current = null;
    }
    if (silenceCheckIntervalRef.current !== null) {
      clearInterval(silenceCheckIntervalRef.current);
      silenceCheckIntervalRef.current = null;
    }
    const elapsed = Date.now() - chunkStartedAtRef.current;
    const remaining = minChunkMs - elapsed;
    if (remaining > 0) {
      setTimeout(() => recorderRef.current?.stop(), remaining);
    } else {
      recorderRef.current?.stop();
    }
    // Safety net if the server never answers the stop frame with "final".
    setTimeout(() => {
      if (!gotFinalRef.current && wsRef.current) {
        wsRef.current.close();
        cleanup();
      }
    }, Math.max(remaining, 0) + STOP_SAFETY_NET_MS);
  }, [cleanup, minChunkMs]);

  const start = useCallback(async (): Promise<boolean> => {
    if (activeRef.current) return false;
    activeRef.current = true;

    if (!isLiveSttSupported()) {
      activeRef.current = false;
      onUnavailableRef.current?.("unsupported_browser");
      return false;
    }

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      activeRef.current = false;
      onUnavailableRef.current?.("mic_denied");
      return false;
    }

    const ws = new WebSocket(speechStreamWebSocketUrl());
    ws.binaryType = "blob";
    stoppingRef.current = false;
    gotFinalRef.current = false;
    micLostRef.current = false;
    hasSpokenRef.current = false;
    lastLoudAtRef.current = Date.now();
    streamRef.current = stream;
    wsRef.current = ws;
    // { once: true }: cleanup()'s own track.stop() also dispatches "ended", which would otherwise re-fire this.
    stream.getTracks().forEach((track) => track.addEventListener("ended", reportMicLost, { once: true }));
    volumeMeterCleanupRef.current = attachVolumeMeter(stream, (level) => {
      if (level > SILENCE_LEVEL_THRESHOLD) {
        lastLoudAtRef.current = Date.now();
        hasSpokenRef.current = true;
      }
      onVolumeRef.current?.(level);
    });

    return new Promise<boolean>((resolve) => {
      let settled = false;
      const settle = (connected: boolean) => {
        if (!settled) {
          settled = true;
          resolve(connected);
        }
      };

      ws.onopen = () => {
        ws.send(
          JSON.stringify({
            type: "start",
            backend: "local",
            language: language ?? null,
            match_commands: matchCommands,
          }),
        );
        setIsStreaming(true);
        scheduleChunk();
        if (autoStopOnSilence) {
          silenceCheckIntervalRef.current = setInterval(() => {
            if (hasSpokenRef.current && Date.now() - lastLoudAtRef.current > silenceTimeoutMs) {
              stop();
            }
          }, 150);
        }
        settle(true);
      };

      ws.onmessage = (event) => {
        let message: Record<string, unknown>;
        try {
          message = JSON.parse(event.data as string);
        } catch {
          return;
        }
        if (message.type === "partial") {
          onPartialRef.current?.(message.chunk_text as string, message.full_text as string);
        } else if (message.type === "final") {
          gotFinalRef.current = true;
          onFinalRef.current?.(message.text as string, (message.matched_command as SpeechCommand | null) ?? null);
          ws.close();
          cleanup();
          settle(true);
        } else if (message.type === "error") {
          onErrorRef.current?.((message.detail as string) ?? "unknown streaming error");
        }
      };

      ws.onclose = () => {
        if (!gotFinalRef.current && !micLostRef.current) {
          onUnavailableRef.current?.("connection_lost");
        }
        cleanup();
        settle(false);
      };
      ws.onerror = () => {
        // onclose fires right after and does the actual cleanup/reporting.
      };
    });
  }, [language, autoStopOnSilence, silenceTimeoutMs, matchCommands, scheduleChunk, stop, cleanup, reportMicLost]);

  return { isStreaming, start, stop };
}
