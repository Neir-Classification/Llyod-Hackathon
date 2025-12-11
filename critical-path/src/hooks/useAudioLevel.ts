import { useCallback, useEffect, useRef, useState } from 'react';

export function useAudioLevel() {
  const levelRef = useRef(0);
  const streamRef = useRef<MediaStream | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const rafRef = useRef<number>(0);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const stop = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    ctxRef.current?.close();
    streamRef.current?.getTracks().forEach(t => t.stop());
    setReady(false);
  }, []);

  const start = useCallback(async () => {
    stop();
    try {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      ctxRef.current = ctx;
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 1024;
      analyser.smoothingTimeConstant = 0.8;
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const source = ctx.createMediaStreamSource(stream);
      source.connect(analyser);
      analyserRef.current = analyser;

      const data = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteFrequencyData(data);
        const avg = data.reduce((a, b) => a + b) / data.length;
        const norm = Math.min(1, Math.max(0, (avg - 16) / 90));
        levelRef.current += (norm - levelRef.current) * 0.15;
        rafRef.current = requestAnimationFrame(tick);
      };
      tick();
      setReady(true);
      setError(null);
    } catch (err: any) {
      setError(err.message);
      setReady(false);
    }
  }, [stop]);

  useEffect(() => stop, [stop]);

  return { levelRef, ready, error, start, stop, analyser: analyserRef.current };
}
