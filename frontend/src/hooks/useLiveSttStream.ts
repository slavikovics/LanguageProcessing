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
/** How long after stop() to wait for a "final" before giving up on the
 * connection and force-closing it ourselves. Must outlast the backend's own
 * per-chunk ceiling (_STREAM_CHUNK_TIMEOUT_SECONDS = 20s in routers/
 * speech.py) plus some room for a cold Whisper model load — the previous
 * 5s was tight enough that a single slow-but-legitimate final chunk (first
 * request after the speech-service container/model just started, or one
 * queued behind another concurrent live session) could get force-closed by
 * the client while the server was still genuinely working on it, which then
 * surfaced to the user as a false "Соединение ... потеряно" even though
 * nothing had actually failed. */
const STOP_SAFETY_NET_MS = 22000;
/** Above this normalized mic loudness (see micVolumeMeter's 0..1 scale) a
 * frame counts as "the user is talking" for silence-based auto-stop. */

interface UseLiveSttStreamOptions {
  language?: string;
  /** How often (ms) MediaRecorder is stopped and restarted on the same
   * stream — each restart yields one independently-decodable audio chunk,
   * sent to the server as soon as it's ready. Default 3500ms: short enough
   * to feel live, long enough that faster-whisper's "base" stream model
   * (see speech-service/app/stt_local.py) stays comfortably faster than
   * real-time on the container's CPU budget. */
  chunkMs?: number;
  /** Floor (ms) on how long the *current* chunk's recorder has been running
   * before stop() is honored — a MediaRecorder stopped only a few hundred ms
   * after starting can produce a blob too short for the browser's encoder to
   * finalize into a valid container, which faster-whisper can't decode. A
   * user calling stop() right after a chunk restarted (or right after a
   * short utterance) is the common way to hit that, so stop() waits out the
   * remainder of this floor instead of stopping immediately. */
  minChunkMs?: number;
  /** When set, stop() is called automatically once the mic has gone quiet
   * for `silenceTimeoutMs` after having heard some speech — the
   * Siri/Google-Assistant style "keep listening until you stop talking"
   * turn-taking, instead of requiring an explicit manual stop. Needs
   * AudioContext support to detect silence at all (see
   * micVolumeMeter.isVolumeMeterSupported); where it's unavailable this is
   * silently a no-op and the caller's own stop() control remains the only
   * way to end the turn. */
  autoStopOnSilence?: boolean;
  /** How long (ms) the mic must stay under SILENCE_LEVEL_THRESHOLD after
   * having heard speech before autoStopOnSilence ends the turn. */
  silenceTimeoutMs?: number;
  /** Whether the server should check the finished transcript against
   * speech_commands at all. Default true; a caller with no onFinal
   * consumer for `matchedCommand` (e.g. Settings' STT accuracy preview,
   * which only wants plain text back) should pass false so the widget
   * doesn't look like it's "reacting" to what was said. */
  matchCommands?: boolean;
  onPartial?: (chunkText: string, fullText: string) => void;
  onFinal?: (fullText: string, matchedCommand: SpeechCommand | null) => void;
  onError?: (detail: string) => void;
  onUnavailable?: (reason: LiveSttUnavailableReason) => void;
  /** Fired on every animation frame while the mic is live with a normalized
   * 0..1 loudness reading, for driving a volume-reactive UI (e.g. a ring
   * around the mic button) — separate from onPartial/onFinal, which only
   * fire once per ~3.5s chunk and are far too coarse for that. */
  onVolume?: (level: number) => void;
}

interface UseLiveSttStreamResult {
  isStreaming: boolean;
  /** Resolves once the outcome is known: true if the connection actually
   * opened, false if it failed/was rejected (onUnavailable has already been
   * called in that case) or if a start() was already in flight. */
  start: () => Promise<boolean>;
  stop: () => void;
}

export function isLiveSttSupported(): boolean {
  return typeof MediaRecorder !== "undefined" && typeof WebSocket !== "undefined";
}

/**
 * Drives live speech-to-text: restarts MediaRecorder every `chunkMs` on one
 * shared mic stream (see the plan — a rolling buffer of ondataavailable
 * timeslices isn't reliably independently-decodable; a fresh MediaRecorder
 * per chunk always is) and streams each chunk to /speech/stt/stream over a
 * WebSocket, relaying partial/final transcripts back through callbacks.
 * Local faster-whisper backend only — this is the only STT backend the app
 * supports.
 *
 * Deliberately not built on useJobProgress's shape: that hook is read-only
 * JSON-over-WS with a polling fallback; this one is bidirectional
 * (binary audio out, JSON in) and owns mic lifecycle, with no meaningful
 * polling fallback — on an unexpected disconnect it just reports
 * "connection_lost" and stops, leaving the caller to fall back to a batch
 * recording if it wants to.
 */
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

  // Latest-value refs for the callback props: start() only actually runs
  // once per session (its WebSocket handlers are set up a single time, when
  // the connection opens) but the calling component can re-render with new
  // callback closures at any point during that session — e.g.
  // SpeechModeContext recreates its onVolume/onPartial/etc. whenever
  // activationPhrase or the command list changes. Closing directly over
  // `options.onX` in the handlers below would freeze them at whatever those
  // callbacks happened to be at connect time, silently ignoring any settings
  // change made while already listening until the mic was restarted.
  // Dereferencing through a ref instead means every already-open session
  // picks up the latest callback on its very next event.
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
  /** Set by reportMicLost so ws.onclose (which fires right after its own
   * wsRef.current?.close() call) reports the more specific "mic_lost"
   * reason instead of also reporting a redundant "connection_lost" for the
   * very same event. */
  const micLostRef = useRef(false);
  const chunkStartedAtRef = useRef(0);
  /** Set synchronously the instant start() is called, before any await —
   * guards against a caller invoking start() again while a previous call is
   * still connecting (e.g. a UI that only flips its "listening" state after
   * start()'s promise resolves lets a second rapid click race in during that
   * window). Without this, each racing call opens its own mic stream and
   * WebSocket, and only the last one written into these refs is ever
   * stopped — the earlier ones leak, silently keep transcribing, and queue
   * up behind each other and any other live session on the shared backend
   * concurrency limit (a real incident: a burst of un-debounced clicks on
   * the ambient mic button opened 7 overlapping sessions in ~1.5s). */
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

  /** Ends the session the same way an unrecoverable failure would (report,
   * close, clean up) when the mic itself disappears mid-session — device
   * unplugged, OS/browser revoked the permission, another app took
   * exclusive access. Without this, the recorder-restart cycle either threw
   * uncaught inside a MediaRecorder event handler or just silently stopped
   * producing chunks, leaving the UI stuck showing "listening" forever with
   * no further transcript and no explanation — easy to hit on a long
   * recording simply by being open for longer. */
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
      // Constructing on a stream whose track already ended throws
      // synchronously rather than ever firing an event — see
      // reportMicLost's comment.
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
    // Safety net: if the server never answers the stop frame with "final"
    // (dropped connection, server error), don't leave the mic indicator on
    // forever.
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
    // { once: true } also protects against the normal-stop path re-firing
    // this: cleanup() below calls track.stop(), which itself dispatches
    // "ended" — reportMicLost's stoppingRef guard would no-op that second
    // call anyway, but this avoids even queuing it.
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
