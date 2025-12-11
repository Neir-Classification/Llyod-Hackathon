import { useCallback, useEffect, useRef, useState } from 'react';

export interface AudioMetrics {
  level: number;           // 0-1 normalized volume
  pitchVariance: number;   // 0-1 normalized pitch variation
  speechRate: number;      // Estimated words per minute (based on energy bursts)
  isSpeaking: boolean;     // Whether currently detecting speech
}

export function useAudioLevel() {
  const levelRef = useRef(0);
  const metricsRef = useRef<AudioMetrics>({
    level: 0,
    pitchVariance: 0,
    speechRate: 120, // Default normal rate
    isSpeaking: false
  });
  const streamRef = useRef<MediaStream | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const rafRef = useRef<number>(0);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // For pitch and speech rate estimation
  const pitchHistoryRef = useRef<number[]>([]);
  const energyBurstsRef = useRef<number[]>([]); // Timestamps of speech bursts
  const lastSpeechTimeRef = useRef<number>(0);

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
      analyser.fftSize = 2048; // Larger for better pitch detection
      analyser.smoothingTimeConstant = 0.8;
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const source = ctx.createMediaStreamSource(stream);
      source.connect(analyser);
      analyserRef.current = analyser;

      const frequencyData = new Uint8Array(analyser.frequencyBinCount);
      const timeData = new Uint8Array(analyser.fftSize);
      
      // Reset tracking
      pitchHistoryRef.current = [];
      energyBurstsRef.current = [];
      lastSpeechTimeRef.current = 0;

      const tick = () => {
        // Get frequency and time domain data
        analyser.getByteFrequencyData(frequencyData);
        analyser.getByteTimeDomainData(timeData);
        
        // Calculate average level (volume)
        const avg = frequencyData.reduce((a, b) => a + b) / frequencyData.length;
        const norm = Math.min(1, Math.max(0, (avg - 16) / 90));
        levelRef.current += (norm - levelRef.current) * 0.15;
        
        // Detect if speaking (voice activity detection)
        const isSpeaking = norm > 0.15;
        const now = Date.now();
        
        if (isSpeaking && now - lastSpeechTimeRef.current > 200) {
          // Record energy burst for speech rate estimation
          energyBurstsRef.current.push(now);
          lastSpeechTimeRef.current = now;
          
          // Keep only last 5 seconds of bursts
          const fiveSecondsAgo = now - 5000;
          energyBurstsRef.current = energyBurstsRef.current.filter(t => t > fiveSecondsAgo);
        }
        
        // Estimate pitch from frequency data (simplified)
        // Find peak frequency in voice range (85Hz - 400Hz for human voice)
        const voiceStartBin = Math.floor(85 * analyser.fftSize / ctx.sampleRate);
        const voiceEndBin = Math.floor(400 * analyser.fftSize / ctx.sampleRate);
        
        let maxVal = 0;
        let maxBin = voiceStartBin;
        for (let i = voiceStartBin; i < voiceEndBin; i++) {
          if (frequencyData[i] > maxVal) {
            maxVal = frequencyData[i];
            maxBin = i;
          }
        }
        
        if (isSpeaking && maxVal > 50) {
          const estimatedPitch = (maxBin * ctx.sampleRate) / analyser.fftSize;
          pitchHistoryRef.current.push(estimatedPitch);
          
          // Keep last 50 pitch samples
          if (pitchHistoryRef.current.length > 50) {
            pitchHistoryRef.current.shift();
          }
        }
        
        // Calculate pitch variance (high variance = emotional/stressed)
        let pitchVariance = 0;
        if (pitchHistoryRef.current.length > 5) {
          const pitchMean = pitchHistoryRef.current.reduce((a, b) => a + b, 0) / pitchHistoryRef.current.length;
          const variance = pitchHistoryRef.current.reduce((sum, p) => sum + Math.pow(p - pitchMean, 2), 0) / pitchHistoryRef.current.length;
          const stdDev = Math.sqrt(variance);
          // Normalize: stdDev of ~50Hz is normal, >100Hz is high
          pitchVariance = Math.min(1, stdDev / 100);
        }
        
        // Estimate speech rate from energy bursts
        // More bursts in a time period = faster speech
        let speechRate = 120; // Default normal rate
        if (energyBurstsRef.current.length > 3) {
          const timePeriod = (now - energyBurstsRef.current[0]) / 1000; // seconds
          const burstsPerSecond = energyBurstsRef.current.length / Math.max(timePeriod, 1);
          // Rough conversion: ~2-3 bursts/sec = ~120-180 WPM
          speechRate = Math.round(burstsPerSecond * 60);
          // Clamp to reasonable range
          speechRate = Math.max(60, Math.min(250, speechRate));
        }
        
        // Update metrics
        metricsRef.current = {
          level: levelRef.current,
          pitchVariance,
          speechRate,
          isSpeaking
        };
        
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

  return { 
    levelRef, 
    metricsRef,
    ready, 
    error, 
    start, 
    stop, 
    analyser: analyserRef.current 
  };
}
