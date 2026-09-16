import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { synthesizeSpeech } from "@/api/client";
import { chunkTextForSpeech } from "@/lib/speechChunking";
import { useSpeechSettings } from "./SpeechSettingsContext";

type Status = "idle" | "requesting" | "playing";

/**
 * A single shared TTS player instead of one per SpeakButton: only one
 * document/snippet can sensibly be read aloud at a time (same mental model
 * as any audio player), and a single player is what lets the "stop_speaking"
 * voice command and the global speech-mode dispatcher stop whatever is
 * currently playing regardless of which SpeakButton started it.
 *
 * Playback goes through a shared Web Audio API AudioContext rather than a
 * plain <audio> element: Chrome blocks audio.play() with a NotAllowedError
 * unless it's called from inside a real user gesture, but a *voice command*
 * (e.g. "read this" heard by global speech mode) fires from an async
 * SpeechRecognition callback, which doesn't count as one. An AudioContext
 * only needs to be resumed *once* from a real click (see primeAudioContext,
 * called when global speech mode is toggled on) and then stays usable
 * indefinitely — unlike audio.play(), which re-checks activation every call.
 */
interface SpeechPlaybackContextValue {
  status: Status;
  activeText: string | null;
  error: string | null;
  errorText: string | null;
  speak: (text: string) => void;
  stop: () => void;
  primeAudioContext: () => void;
}

const SpeechPlaybackContext = createContext<SpeechPlaybackContextValue | null>(null);

function getAudioContextConstructor(): typeof AudioContext | null {
  const w = window as unknown as { AudioContext?: typeof AudioContext; webkitAudioContext?: typeof AudioContext };
  return w.AudioContext ?? w.webkitAudioContext ?? null;
}

export function SpeechPlaybackProvider({ children }: { children: ReactNode }) {
  const { voice, rate, volume } = useSpeechSettings();
  const [status, setStatus] = useState<Status>("idle");
  const [activeText, setActiveText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorText, setErrorText] = useState<string | null>(null);

  const controllerRef = useRef<AbortController | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);
  const sourceRef = useRef<AudioBufferSourceNode | null>(null);
  const chunksRef = useRef<string[]>([]);
  const chunkIndexRef = useRef(0);
  const nextChunkRef = useRef<Promise<Blob> | null>(null);
  const stoppedRef = useRef(true);

  // Settings can change mid-playback; refs keep the in-flight chunk queue
  // using whatever was selected when speak() was called, not a stale
  // closure, without re-running this whole effect-free class of logic.
  const settingsRef = useRef({ voice, rate, volume });
  settingsRef.current = { voice, rate, volume };

  useEffect(() => stop, []);

  function getAudioContext(): AudioContext | null {
    if (audioContextRef.current) return audioContextRef.current;
    const Ctor = getAudioContextConstructor();
    if (!Ctor) return null;
    const ctx = new Ctor();
    const gain = ctx.createGain();
    gain.connect(ctx.destination);
    audioContextRef.current = ctx;
    gainNodeRef.current = gain;
    return ctx;
  }

  /** Call from inside a real click handler (e.g. the global speech-mode
   * toggle) to unlock playback for voice-triggered speak() calls later,
   * whenever they happen. A no-op if already running. */
  function primeAudioContext() {
    const ctx = getAudioContext();
    if (ctx && ctx.state === "suspended") void ctx.resume();
  }

  function stop() {
    stoppedRef.current = true;
    controllerRef.current?.abort();
    controllerRef.current = null;
    if (sourceRef.current) {
      sourceRef.current.onended = null;
      try {
        sourceRef.current.stop();
      } catch {
        // already stopped/never started
      }
      sourceRef.current.disconnect();
      sourceRef.current = null;
    }
    nextChunkRef.current = null;
    setStatus("idle");
    setActiveText(null);
  }

  function fetchChunk(chunkText: string, signal: AbortSignal): Promise<Blob> {
    const { voice: v, rate: r } = settingsRef.current;
    return synthesizeSpeech({ text: chunkText, voice: v, rate: r }, { signal });
  }

  async function playChunk(blob: Blob) {
    const { volume: vol } = settingsRef.current;
    const ctx = getAudioContext();
    if (!ctx || !gainNodeRef.current) {
      setError("Воспроизведение звука не поддерживается этим браузером.");
      setErrorText(chunksRef.current[0] ?? null);
      stop();
      return;
    }
    if (ctx.state === "suspended") {
      try {
        await ctx.resume();
      } catch {
        // fall through — decodeAudioData/start below will surface the real error
      }
    }

    let audioBuffer: AudioBuffer;
    try {
      const arrayBuffer = await blob.arrayBuffer();
      audioBuffer = await ctx.decodeAudioData(arrayBuffer);
    } catch (err) {
      setError("Не удалось воспроизвести аудио.");
      setErrorText(chunksRef.current[0] ?? null);
      stop();
      return;
    }
    if (stoppedRef.current) return;

    gainNodeRef.current.gain.value = vol;
    const source = ctx.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(gainNodeRef.current);
    source.onended = () => void advance();
    sourceRef.current = source;

    setStatus("playing");
    try {
      source.start();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setErrorText(chunksRef.current[0] ?? null);
      stop();
      return;
    }

    const controller = controllerRef.current;
    const nextIndex = chunkIndexRef.current + 1;
    const prefetch =
      controller && nextIndex < chunksRef.current.length
        ? fetchChunk(chunksRef.current[nextIndex], controller.signal)
        : null;
    // Attach a no-op catch immediately: if stop() aborts the controller
    // before advance() ever consumes this promise, it would otherwise
    // surface as an unhandled promise rejection.
    prefetch?.catch(() => {});
    nextChunkRef.current = prefetch;
  }

  async function advance() {
    if (stoppedRef.current) return;
    chunkIndexRef.current += 1;
    if (chunkIndexRef.current >= chunksRef.current.length) {
      stop();
      return;
    }

    const controller = controllerRef.current;
    if (!controller) return;
    try {
      const blob = await (nextChunkRef.current ??
        fetchChunk(chunksRef.current[chunkIndexRef.current], controller.signal));
      if (stoppedRef.current) return;
      await playChunk(blob);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(err instanceof Error ? err.message : String(err));
      stop();
    }
  }

  async function speak(text: string) {
    stop();

    const chunks = chunkTextForSpeech(text);
    if (chunks.length === 0) return;

    setError(null);
    setErrorText(null);
    setActiveText(text);
    setStatus("requesting");
    stoppedRef.current = false;
    chunksRef.current = chunks;
    chunkIndexRef.current = 0;
    const controller = new AbortController();
    controllerRef.current = controller;

    try {
      const blob = await fetchChunk(chunks[0], controller.signal);
      if (stoppedRef.current) return;
      await playChunk(blob);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(err instanceof Error ? err.message : String(err));
      setErrorText(text);
      stop();
    }
  }

  return (
    <SpeechPlaybackContext.Provider
      value={{ status, activeText, error, errorText, speak, stop, primeAudioContext }}
    >
      {children}
    </SpeechPlaybackContext.Provider>
  );
}

export function useSpeechPlayback(): SpeechPlaybackContextValue {
  const ctx = useContext(SpeechPlaybackContext);
  if (!ctx) {
    throw new Error("useSpeechPlayback must be used within a SpeechPlaybackProvider");
  }
  return ctx;
}
