function getAudioContextConstructor(): typeof AudioContext | undefined {
  return (
    window.AudioContext ||
    (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
  );
}

/**
 * Whether attachVolumeMeter can report real loudness readings in this
 * browser — callers that derive end-of-speech (silence) detection from those
 * readings need to know when there's no signal at all, rather than silently
 * treating "no AudioContext" the same as "the user isn't talking".
 */
export function isVolumeMeterSupported(): boolean {
  return getAudioContextConstructor() !== undefined;
}

/**
 * Attaches a Web Audio AnalyserNode to a live mic MediaStream and reports a
 * normalized 0..1 loudness level on every animation frame via `onLevel` —
 * driving a volume-reactive UI (e.g. a ring around the mic button) without
 * any server round-trip. Returns a cleanup function that tears down the
 * AudioContext/AnalyserNode and cancels the animation loop.
 */
export function attachVolumeMeter(stream: MediaStream, onLevel: (level: number) => void): () => void {
  const AudioContextCtor = getAudioContextConstructor();
  if (!AudioContextCtor) return () => {};

  const audioContext = new AudioContextCtor();
  const source = audioContext.createMediaStreamSource(stream);
  const analyser = audioContext.createAnalyser();
  analyser.fftSize = 256;
  analyser.smoothingTimeConstant = 0.6;
  source.connect(analyser);

  const data = new Uint8Array(analyser.frequencyBinCount);
  let rafId = 0;

  const tick = () => {
    analyser.getByteTimeDomainData(data);
    let sumSquares = 0;
    for (let i = 0; i < data.length; i++) {
      const normalized = (data[i] - 128) / 128;
      sumSquares += normalized * normalized;
    }
    const rms = Math.sqrt(sumSquares / data.length);
    // Typical speech RMS on this metric sits well under 1 — scale up so
    // normal talking volume visibly moves the UI instead of barely twitching it.
    onLevel(Math.min(1, rms * 4));
    rafId = requestAnimationFrame(tick);
  };
  rafId = requestAnimationFrame(tick);

  return () => {
    cancelAnimationFrame(rafId);
    source.disconnect();
    analyser.disconnect();
    void audioContext.close();
  };
}
