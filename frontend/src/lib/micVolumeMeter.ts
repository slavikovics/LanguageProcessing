function getAudioContextConstructor(): typeof AudioContext | undefined {
  return (
    window.AudioContext ||
    (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
  );
}

export function isVolumeMeterSupported(): boolean {
  return getAudioContextConstructor() !== undefined;
}

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
    // Scaled up: raw speech RMS sits well under 1 and would barely move the UI.
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
