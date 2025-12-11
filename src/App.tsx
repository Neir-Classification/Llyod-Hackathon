import { useEffect, useState, useRef } from 'react';
import Iridescence from './components/Iridescence';
import { useAudioLevel, AudioMetrics } from './hooks/useAudioLevel';

interface Citation {
  id: number;
  source: string;
  policy_name: string;
  page: number | string;
  excerpt: string;
  relevance_rank: number;
}

interface EmpathyAnalysis {
  detected_emotion: string;
  confidence: number;
  is_emergency: boolean;
  emergency_type: string | null;
  mode: 'emergency_triage' | 'standard';
  signals: {
    keyword_signals: string[];
    acoustic_signals: string[];
    sentiment_indicators: string[];
  };
}

interface TTSSettings {
  speed: number;
  voice: string;
}

interface ChatMessage {
  text: string;
  role: 'user' | 'assistant';
  citations?: Citation[];
  empathyAnalysis?: EmpathyAnalysis;
}

export default function App() {
  const { levelRef, metricsRef, ready, error, start } = useAudioLevel();
  const [level, setLevel] = useState(0);
  const [greetingText, setGreetingText] = useState('');
  const [greetingTime, setGreetingTime] = useState('');
  const [statusText, setStatusText] = useState('Click to start');
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState('Waiting for input...');
  const [response, setResponse] = useState('Processing...');
  const [subtitle, setSubtitle] = useState('');
  const [showSubtitle, setShowSubtitle] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [recordedChunks, setRecordedChunks] = useState<Blob[]>([]);
  const [animationState, setAnimationState] = useState<'idle' | 'listening' | 'thinking' | 'responding'>('idle');
  const [citations, setCitations] = useState<Citation[]>([]);
  const [showCitations, setShowCitations] = useState(false);
  const [audioContext, setAudioContext] = useState<AudioContext | null>(null);

  // Empathy Engine State
  const [currentEmotion, setCurrentEmotion] = useState<string>('neutral');
  const [isEmergency, setIsEmergency] = useState(false);
  const [emergencyType, setEmergencyType] = useState<string | null>(null);
  const [empathyMode, setEmpathyMode] = useState<'standard' | 'emergency_triage'>('standard');
  const [empathyConfidence, setEmpathyConfidence] = useState(0);
  const [ttsSettings, setTtsSettings] = useState<TTSSettings>({ speed: 1.0, voice: 'alloy' });
  const [showEmpathyDetails, setShowEmpathyDetails] = useState(false);
  
  // Track audio metrics during recording
  const recordingMetricsRef = useRef<AudioMetrics[]>([]);

  // Smooth level animation
  useEffect(() => {
    let raf = 0;
    const update = () => {
      setLevel(prev => prev + (levelRef.current - prev) * 0.25);
      raf = requestAnimationFrame(update);
    };
    update();
    return () => cancelAnimationFrame(raf);
  }, [levelRef]);

  // Calculate orb properties based on animation state AND detected emotion
  const getEmotionColor = (): [number, number, number] => {
    if (animationState === 'listening') return [0.3, 0.5, 1.0]; // Blue when listening
    
    // Emotion-based colors for thinking/responding
    switch (currentEmotion) {
      case 'panicked':
        return [0.2, 0.8, 0.6]; // Calming teal/green
      case 'angry':
        return [0.4, 0.6, 0.9]; // Cool blue
      case 'anxious':
        return [0.5, 0.7, 0.8]; // Soft cyan
      case 'confused':
        return [0.6, 0.5, 0.9]; // Gentle purple
      case 'happy':
        return [0.9, 0.6, 0.3]; // Warm orange
      case 'distressed':
        return [0.3, 0.7, 0.7]; // Soothing teal
      default:
        return [0.8, 0.4, 0.9]; // Default purple
    }
  };

  const orbColor: [number, number, number] = getEmotionColor();
  
  const amplitude = 
    animationState === 'idle' ? 0.15 :
    animationState === 'listening' ? 0.18 + level * 1.7 : // Audio-reactive
    animationState === 'thinking' ? 0.3 : // Pulsing
    isEmergency ? 0.2 : // Calmer for emergency
    0.25; // Steady
  
  const speed = 
    animationState === 'idle' ? 0.5 :
    animationState === 'listening' ? 0.75 + level * 0.5 : // Audio-reactive
    animationState === 'thinking' ? 1.5 : // Fast pulsing
    isEmergency ? 0.4 : // Slower, calmer for emergency
    0.8; // Medium
  
  const scale = 
    animationState === 'idle' ? 1 :
    animationState === 'listening' ? 1 + level * 0.35 : // Audio-reactive
    animationState === 'thinking' ? 1.1 : // Slightly larger
    1.05; // Normal
  
  const glowOpacity = 
    animationState === 'idle' ? 0.2 :
    animationState === 'listening' ? 0.25 + level * 2.45 : // Audio-reactive
    animationState === 'thinking' ? 0.8 : // Bright
    0.5; // Medium

  // Initialize greeting
  useEffect(() => {
    const updateGreeting = () => {
      const hour = new Date().getHours();
      const minutes = String(new Date().getMinutes()).padStart(2, '0');
      const period = hour >= 12 ? 'PM' : 'AM';
      const displayHour = hour % 12 || 12;

      let greeting = 'Good morning';
      if (hour >= 12 && hour < 17) greeting = 'Good afternoon';
      if (hour >= 17) greeting = 'Good evening';

      setGreetingText(greeting);
      setGreetingTime(`${displayHour}:${minutes} ${period}`);
    };
    updateGreeting();
  }, []);

  // Start recording with silence detection
  const startRecording = async () => {
    console.log('startRecording called, ready:', ready, 'isRecording:', isRecording);
    
    // Reset empathy state for new recording
    recordingMetricsRef.current = [];
    
    try {
      // Enable audio context if not ready (user gesture requirement)
      if (!ready) {
        await start();
      }

      // Start recording
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported('audio/webm') 
        ? 'audio/webm' 
        : MediaRecorder.isTypeSupported('audio/ogg') 
        ? 'audio/ogg' 
        : '';
      
      // Set up audio context for silence detection FIRST
      const audioCtx = new AudioContext();
      setAudioContext(audioCtx);
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 512;
      analyser.smoothingTimeConstant = 0.3;
      source.connect(analyser);

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      
      const recorder = mimeType 
        ? new MediaRecorder(stream, { mimeType, audioBitsPerSecond: 128000 }) 
        : new MediaRecorder(stream);
      
      const allChunks: Blob[] = [];
      
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          allChunks.push(e.data);
        }
      };

      recorder.onstop = async () => {
        console.log('🛑 Recorder stopped - processing audio');
        stream.getTracks().forEach(t => t.stop());
        if (audioCtx) {
          audioCtx.close();
        }
        setRecordedChunks(allChunks);
        setMediaRecorder(null);
        setAudioContext(null);
        
        // Calculate average audio metrics from recording session
        const avgMetrics = calculateAverageMetrics();
        console.log('📊 Recording metrics:', avgMetrics);
        
        // Process full audio immediately with metrics
        await processVoiceInput(allChunks, mimeType || 'audio/webm', avgMetrics);
      };

      // Start recording without timeslice for faster processing
      recorder.start();
      console.log('🎙️ Recording started');
      
      setMediaRecorder(recorder);
      setIsRecording(true);
      setAnimationState('listening');
      setStatusText('Listening...');
      setTranscript('Listening...');

      // Voice Activity Detection with RMS (Root Mean Square) method
      let silenceStart: number | null = null;
      let speechDetected = false;
      let isChecking = true;
      let audioLevelHistory: number[] = [];
      const HISTORY_SIZE = 10;
      
      // Dynamic thresholds based on environment
      let noiseFloor = 0;
      let calibrationSamples = 0;
      const CALIBRATION_FRAMES = 30;
      
      const SILENCE_DURATION = 1800; // 1.8 seconds
      const SPEECH_MULTIPLIER = 3; // Speech must be 3x noise floor
      const SILENCE_MULTIPLIER = 1.5; // Silence is 1.5x noise floor

      const calculateRMS = () => {
        analyser.getByteTimeDomainData(dataArray);
        
        let sumSquares = 0;
        for (let i = 0; i < bufferLength; i++) {
          const normalized = (dataArray[i] - 128) / 128; // Normalize to -1 to 1
          sumSquares += normalized * normalized;
        }
        return Math.sqrt(sumSquares / bufferLength);
      };

      const checkAudioLevel = () => {
        if (!isChecking || !recorder || recorder.state !== 'recording') {
          return;
        }

        const rms = calculateRMS();
        const level = rms * 100; // Scale to 0-100
        
        // Capture metrics from the hook for empathy analysis
        if (metricsRef.current) {
          recordingMetricsRef.current.push({ ...metricsRef.current });
        }
        
        // Calibrate noise floor in first second
        if (calibrationSamples < CALIBRATION_FRAMES) {
          noiseFloor = Math.max(noiseFloor, level);
          calibrationSamples++;
          if (calibrationSamples === CALIBRATION_FRAMES) {
            console.log('🎚️ Noise floor calibrated:', noiseFloor.toFixed(2));
          }
          requestAnimationFrame(checkAudioLevel);
          return;
        }
        
        // Keep rolling average
        audioLevelHistory.push(level);
        if (audioLevelHistory.length > HISTORY_SIZE) {
          audioLevelHistory.shift();
        }
        
        const avgLevel = audioLevelHistory.reduce((a, b) => a + b, 0) / audioLevelHistory.length;
        const speechThreshold = noiseFloor * SPEECH_MULTIPLIER;
        const silenceThreshold = noiseFloor * SILENCE_MULTIPLIER;

        // Detect speech start
        if (!speechDetected && avgLevel > speechThreshold) {
          speechDetected = true;
          console.log('🎤 Speech detected! Level:', avgLevel.toFixed(2), 'Threshold:', speechThreshold.toFixed(2));
        }

        // Detect silence after speech
        if (speechDetected) {
          if (avgLevel < silenceThreshold) {
            if (silenceStart === null) {
              silenceStart = Date.now();
            } else {
              const silenceDuration = Date.now() - silenceStart;
              if (silenceDuration > SILENCE_DURATION) {
                console.log('🛑 Auto-stop: Silence detected for', silenceDuration, 'ms');
                isChecking = false;
                if (recorder.state === 'recording') {
                  recorder.stop();
                  setIsRecording(false);
                }
                return;
              }
            }
          } else {
            silenceStart = null;
          }
        }

        requestAnimationFrame(checkAudioLevel);
      };

      setTimeout(() => {
        console.log('🎬 Starting Voice Activity Detection');
        checkAudioLevel();
      }, 100);
    } catch (err) {
      console.error('Microphone access error:', err);
      setStatusText('Microphone access denied');
    }
  };

  // Calculate average metrics from recording session for empathy analysis
  const calculateAverageMetrics = () => {
    const metrics = recordingMetricsRef.current;
    if (metrics.length === 0) {
      return { speechRate: 120, pitchVariance: 0.3, volumeLevel: 0.5 };
    }
    
    // Filter to only speaking moments
    const speakingMetrics = metrics.filter(m => m.isSpeaking);
    const toAverage = speakingMetrics.length > 5 ? speakingMetrics : metrics;
    
    const avgSpeechRate = toAverage.reduce((sum, m) => sum + m.speechRate, 0) / toAverage.length;
    const avgPitchVariance = toAverage.reduce((sum, m) => sum + m.pitchVariance, 0) / toAverage.length;
    const avgLevel = toAverage.reduce((sum, m) => sum + m.level, 0) / toAverage.length;
    
    return {
      speechRate: Math.round(avgSpeechRate),
      pitchVariance: Number(avgPitchVariance.toFixed(3)),
      volumeLevel: Number(avgLevel.toFixed(3))
    };
  };

  // Stop recording
  const stopRecording = () => {
    console.log('stopRecording called, mediaRecorder:', mediaRecorder, 'isRecording:', isRecording);
    if (mediaRecorder && isRecording) {
      console.log('Stopping recorder...');
      mediaRecorder.stop();
      setIsRecording(false);
      setStatusText('Processing...');
    }
  };

  // Process voice input with Empathy Engine
  const processVoiceInput = async (
    chunks: Blob[], 
    mimeType: string, 
    audioMetrics?: { speechRate: number; pitchVariance: number; volumeLevel: number }
  ) => {
    if (chunks.length === 0) return;

    setIsProcessing(true);
    setAnimationState('thinking');
    setStatusText('Analyzing...');

    try {
      const ext = mimeType.includes('ogg') ? 'ogg' : 'webm';
      const file = new File(chunks, `recording.${ext}`, { type: mimeType });

      const formData = new FormData();
      formData.append('audio_file', file);

      const transcribeRes = await fetch('/speech-to-text', {
        method: 'POST',
        body: formData
      });

      if (!transcribeRes.ok) throw new Error('Transcription failed');
      const transcribeData = await transcribeRes.json();
      const query = transcribeData.text;

      setTranscript(query);

      if (!query.trim() || query.length < 2) {
        setStatusText('Ready to listen');
        setIsProcessing(false);
        setAnimationState('idle');
        return;
      }

      // Get Empathy-powered RAG response with audio metrics
      await sendQueryWithEmpathy(query, audioMetrics);
    } catch (err: any) {
      console.error('Error processing voice input:', err);
      setStatusText('Error. Try again.');
      setTranscript(`Error: ${err.message}`);
      setIsProcessing(false);
      setAnimationState('idle');
    }
  };

  // Send query with Empathy Engine analysis
  const sendQueryWithEmpathy = async (
    query: string, 
    audioMetrics?: { speechRate: number; pitchVariance: number; volumeLevel: number }
  ) => {
    if (!query.trim()) return;

    setIsProcessing(true);
    setStatusText('Understanding your needs...');

    try {
      setChatMessages(prev => [...prev, { text: query, role: 'user' }]);

      // Use the Empathy RAG endpoint
      const ragRes = await fetch('/empathy-rag-query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query, 
          speech_rate: audioMetrics?.speechRate,
          pitch_variance: audioMetrics?.pitchVariance,
          volume_level: audioMetrics?.volumeLevel,
          k: 2 
        })
      });

      if (!ragRes.ok) throw new Error('Query failed');
      const ragData = await ragRes.json();
      const responseText = ragData.response;
      const responseCitations = ragData.citations || [];
      const empathyAnalysis = ragData.empathy_analysis as EmpathyAnalysis;
      const adaptiveTtsSettings = ragData.tts_settings as TTSSettings;

      // Update empathy state
      setCurrentEmotion(empathyAnalysis.detected_emotion);
      setIsEmergency(empathyAnalysis.is_emergency);
      setEmergencyType(empathyAnalysis.emergency_type);
      setEmpathyMode(empathyAnalysis.mode);
      setEmpathyConfidence(empathyAnalysis.confidence);
      setTtsSettings(adaptiveTtsSettings);

      console.log('🧠 Empathy Engine:', empathyAnalysis);
      console.log('🔊 TTS Settings:', adaptiveTtsSettings);

      setResponse(responseText);
      setCitations(responseCitations);
      setChatMessages(prev => [...prev, { 
        text: responseText, 
        role: 'assistant', 
        citations: responseCitations,
        empathyAnalysis 
      }]);

      // Show subtitle
      setSubtitle(responseText);
      setShowSubtitle(true);

      // Generate and play speech with ADAPTIVE TTS (emotion-aware)
      setStatusText(empathyAnalysis.is_emergency ? 'I\'m here to help...' : 'Generating response...');
      console.log('🔊 Requesting Adaptive TTS for:', responseText);
      
      // Use adaptive TTS endpoint with emotion-based settings
      const ttsRes = await fetch('/adaptive-tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          text: responseText, 
          emotion: empathyAnalysis.detected_emotion,
          voice: adaptiveTtsSettings.voice,
          speed: adaptiveTtsSettings.speed,
          audio_format: 'mp3' 
        })
      });

      if (!ttsRes.ok) {
        const errorText = await ttsRes.text();
        console.error('Adaptive TTS failed:', ttsRes.status, errorText);
        throw new Error(`TTS failed: ${ttsRes.status}`);
      }
      
      console.log('✅ Adaptive TTS response received');
      const audioBlob = await ttsRes.blob();
      console.log('📦 Audio blob size:', audioBlob.size, 'bytes');
      
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      
      // Set volume to ensure it's audible
      audio.volume = 1.0;

      setAnimationState('responding');
      
      audio.addEventListener('ended', async () => {
        console.log('🎵 Audio playback ended - returning to listening mode');
        setShowSubtitle(false);
        setAnimationState('idle');
        setTranscript('Waiting for input...');
        setResponse('Processing...');
        setIsProcessing(false);
        // Reset empathy state after response
        setCurrentEmotion('neutral');
        setIsEmergency(false);
        setEmergencyType(null);
        setEmpathyMode('standard');
        URL.revokeObjectURL(audioUrl);
        
        // Automatically start listening again after a brief pause
        setTimeout(async () => {
          console.log('🔄 Auto-starting next recording...');
          await startRecording();
        }, 500);
      });

      audio.addEventListener('error', (e) => {
        console.error('❌ Audio playback error:', e);
        setStatusText('Audio error - Click to retry');
        setIsProcessing(false);
        setAnimationState('idle');
        URL.revokeObjectURL(audioUrl);
      });

      setStatusText('Speaking...');
      console.log('▶️ Playing audio...');
      
      try {
        await audio.play();
        console.log('✅ Audio playing successfully');
      } catch (playErr) {
        console.error('❌ Play failed:', playErr);
        setStatusText('Audio play failed - check browser permissions');
        setIsProcessing(false);
        setAnimationState('idle');
      }
    } catch (err: any) {
      console.error('Error sending query:', err);
      setStatusText('Error. Try again.');
      setResponse(`Error: ${err.message}`);
      setIsProcessing(false);
      setAnimationState('idle');
    }
  };

  // Send chat message (also uses empathy engine for text input)
  const sendChatMessage = async () => {
    const text = chatInput.trim();
    if (!text) return;

    setChatMessages(prev => [...prev, { text, role: 'user' }]);
    setChatInput('');

    try {
      // Use empathy RAG for chat too (no audio metrics for text)
      const res = await fetch('/empathy-rag-query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text, k: 2 })
      });

      if (!res.ok) throw new Error('Query failed');
      const data = await res.json();
      const empathyAnalysis = data.empathy_analysis as EmpathyAnalysis;
      
      setChatMessages(prev => [...prev, { 
        text: data.response, 
        role: 'assistant', 
        citations: data.citations || [],
        empathyAnalysis
      }]);
      
      // Update global empathy state for UI
      setCurrentEmotion(empathyAnalysis.detected_emotion);
      setIsEmergency(empathyAnalysis.is_emergency);
    } catch (err: any) {
      setChatMessages(prev => [...prev, { text: `Error: ${err.message}`, role: 'assistant' }]);
    }
  };

  // Get emotion label for display
  const getEmotionLabel = (emotion: string): string => {
    const labels: Record<string, string> = {
      neutral: 'Neutral',
      happy: 'Positive',
      confused: 'Needs Clarity',
      anxious: 'Concerned',
      angry: 'Frustrated',
      panicked: 'Urgent',
      distressed: 'Distressed'
    };
    return labels[emotion] || emotion;
  };

  // Get emotion icon
  const getEmotionIcon = (emotion: string): string => {
    const icons: Record<string, string> = {
      neutral: '😊',
      happy: '😄',
      confused: '🤔',
      anxious: '😰',
      angry: '😤',
      panicked: '🆘',
      distressed: '💙'
    };
    return icons[emotion] || '💬';
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-black text-white overflow-hidden">
      {/* Background gradient - changes with emotion */}
      <div className={`fixed inset-0 pointer-events-none transition-colors duration-1000 ${
        isEmergency ? 'bg-gradient-radial from-teal-900/10 via-transparent to-transparent' :
        currentEmotion === 'angry' ? 'bg-gradient-radial from-blue-900/10 via-transparent to-transparent' :
        currentEmotion === 'anxious' ? 'bg-gradient-radial from-cyan-900/10 via-transparent to-transparent' :
        'bg-gradient-radial from-purple-900/5 via-transparent to-transparent'
      }`} />
      
      {/* Empathy Engine Indicator - Top Right */}
      {(isProcessing || animationState === 'responding') && currentEmotion !== 'neutral' && (
        <div 
          className="fixed top-8 right-8 bg-black/80 backdrop-blur-xl border border-white/10 rounded-2xl px-4 py-3 z-30 animate-fade-in cursor-pointer"
          onClick={() => setShowEmpathyDetails(true)}
        >
          <div className="flex items-center gap-3">
            <span className="text-xl">{getEmotionIcon(currentEmotion)}</span>
            <div>
              <div className="text-xs text-gray-400 uppercase tracking-wider">Empathy Mode</div>
              <div className="text-sm font-medium">
                {isEmergency ? (
                  <span className="text-teal-400">Emergency Triage</span>
                ) : (
                  <span className="text-purple-300">{getEmotionLabel(currentEmotion)}</span>
                )}
              </div>
            </div>
            {isEmergency && (
              <div className="w-2 h-2 bg-teal-400 rounded-full animate-pulse" />
            )}
          </div>
        </div>
      )}
      
      {/* Message button - Top Left */}
      <button
        onClick={() => setShowChat(true)}
        className="fixed top-8 left-8 w-12 h-12 rounded-full bg-white/10 hover:bg-white/15 border border-white/10 transition-all duration-300 flex items-center justify-center z-30"
        title="Text chat"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      </button>
      {/* Citations button - Top Left below chat */}
      <button
        onClick={() => setShowCitations(true)}
        className={`fixed top-24 left-8 w-12 h-12 rounded-full border transition-all duration-300 flex items-center justify-center z-30 ${
          citations.length > 0 
            ? 'bg-purple-500/20 hover:bg-purple-500/30 border-purple-500/30' 
            : 'bg-white/10 hover:bg-white/15 border-white/10'
        }`}
        title="View sources & citations"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        {citations.length > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 bg-purple-500 text-white text-[10px] rounded-full flex items-center justify-center font-medium">
            {citations.length}
          </span>
        )}
      </button>
      
      <main className="relative z-10 flex flex-col items-center justify-center w-full max-w-2xl px-5 py-10">
        {/* Greeting */}
        <div className="mb-16 text-center animate-fade-in">
          <h1 className="text-5xl font-light mb-3 tracking-tight">{greetingText}</h1>
          <p className="text-gray-500 text-sm font-light tracking-widest">{greetingTime}</p>
        </div>

        {/* Orb Container */}
        <div className="relative w-[200px] h-[200px] mb-16">
          {/* Glow effect */}
          <div 
            className="absolute inset-0 rounded-full bg-purple-500 blur-[130px] transition-opacity duration-150" 
            style={{ opacity: glowOpacity }} 
          />
          
          {/* Orb */}
          <div 
            className="relative h-full w-full rounded-full overflow-hidden shadow-[0_0_90px_rgba(102,126,234,0.45)] transition-transform duration-150 ease-out cursor-pointer hover:scale-105"
            style={{ transform: `scale(${scale})` }}
            onClick={isRecording ? stopRecording : startRecording}
            title={isRecording ? "Click to stop" : "Click to start listening"}
          >
            <Iridescence 
              amplitude={amplitude} 
              speed={speed} 
              color={orbColor} 
              animationState={animationState}
            />
          </div>
        </div>

        {/* Status Text */}
        <p className="text-lg text-gray-400 mb-8 animate-fade-in font-light tracking-wide">
          {isRecording ? 'Listening... (speak naturally, will auto-stop)' : statusText}
        </p>

        {/* Bottom Controls - No manual stop button needed */}
      </main>

      {/* Transcript Display - Always reserve space, fade in content */}
      <div className="fixed top-8 right-8 w-96 h-[280px] bg-black/80 backdrop-blur-2xl border border-white/10 rounded-2xl p-6 shadow-2xl transition-opacity duration-300">
        <div className="mb-5">
          <div className="text-[10px] font-medium text-gray-500 uppercase tracking-widest mb-3">
            Transcript
          </div>
          <div className={`bg-white/5 rounded-xl p-4 h-[80px] overflow-y-auto text-[13px] leading-relaxed text-gray-200 font-light transition-all duration-300 ${
            transcript === 'Waiting for input...' || transcript === 'Listening...' ? 'opacity-40 blur-sm' : 'opacity-100 blur-0'
          }`}>
            {transcript}
          </div>
        </div>
        
        <div>
          <div className="text-[10px] font-medium text-gray-500 uppercase tracking-widest mb-3">Response</div>
          <div className={`bg-white/5 rounded-xl p-4 h-[80px] overflow-y-auto text-[13px] leading-relaxed text-gray-200 font-light transition-all duration-500 ${
            response === 'Processing...' ? 'opacity-40 blur-sm' : 'opacity-100 blur-0'
          }`}>
            {response}
          </div>
        </div>
      </div>

      {/* Subtitle - Reserved space with blur transition */}
      <div className="fixed bottom-20 left-1/2 -translate-x-1/2 max-w-2xl w-[90%] h-[80px] flex items-center justify-center z-20">
        <div className={`w-full bg-black/90 backdrop-blur-2xl border border-white/10 rounded-2xl px-8 py-5 shadow-2xl transition-all duration-500 ${
          showSubtitle ? 'opacity-100 blur-0 scale-100' : 'opacity-0 blur-md scale-95 pointer-events-none'
        }`}>
          <p className="text-base text-gray-100 leading-relaxed font-light text-center">{subtitle}</p>
        </div>
      </div>

      {/* Chat Modal */}
      {showChat && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-md flex items-end justify-center z-50 animate-fade-in">
          <div className="w-full max-w-2xl bg-gray-900/95 backdrop-blur-xl border-t border-white/10 rounded-t-3xl flex flex-col h-[85vh] max-h-[700px] animate-slide-up">
            {/* Chat Header */}
            <div className="flex justify-between items-center px-6 py-5 border-b border-white/10">
              <h2 className="text-xl font-light tracking-tight">Chat</h2>
              <button
                onClick={() => setShowChat(false)}
                className="w-9 h-9 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-all text-xl font-light"
              >
                ×
              </button>
            </div>

            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
              {chatMessages.map((msg, idx) => (
                <div key={idx} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} animate-fade-in`}>
                  {/* Empathy badge for assistant messages */}
                  {msg.role === 'assistant' && msg.empathyAnalysis && msg.empathyAnalysis.detected_emotion !== 'neutral' && (
                    <div className={`mb-2 px-2.5 py-1 rounded-full text-[10px] font-medium flex items-center gap-1.5 ${
                      msg.empathyAnalysis.is_emergency 
                        ? 'bg-teal-500/20 text-teal-400 border border-teal-500/30' 
                        : 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                    }`}>
                      <span>{getEmotionIcon(msg.empathyAnalysis.detected_emotion)}</span>
                      <span>
                        {msg.empathyAnalysis.is_emergency 
                          ? 'Emergency Triage' 
                          : `${getEmotionLabel(msg.empathyAnalysis.detected_emotion)} Response`}
                      </span>
                    </div>
                  )}
                  <div className={`max-w-[75%] px-5 py-3 rounded-2xl text-[14px] leading-relaxed font-light ${
                    msg.role === 'user' 
                      ? 'bg-white text-black rounded-tr-sm' 
                      : 'bg-white/10 text-gray-100 rounded-tl-sm'
                  }`}>
                    {msg.text}
                  </div>
                  {/* Inline citations for assistant messages */}
                  {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                    <div className="mt-2 max-w-[75%]">
                      <div className="flex flex-wrap gap-2">
                        {msg.citations.map((citation) => (
                          <button
                            key={citation.id}
                            onClick={() => {
                              setCitations(msg.citations || []);
                              setShowCitations(true);
                            }}
                            className="inline-flex items-center gap-1 px-2 py-1 bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/30 rounded-lg text-[11px] text-purple-300 transition-all"
                          >
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            Page {citation.page}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Chat Input */}
            <div className="px-5 py-5 border-t border-white/10 flex gap-3">
              <textarea
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendChatMessage();
                  }
                }}
                placeholder="Type your message..."
                className="flex-1 bg-white/10 border border-white/10 text-white placeholder:text-gray-500 px-4 py-3 rounded-2xl resize-none max-h-32 focus:outline-none focus:border-white/25 focus:bg-white/15 transition-all font-light text-[14px]"
                rows={1}
              />
              <button
                onClick={sendChatMessage}
                className="px-6 py-3 bg-white text-black rounded-full font-light hover:bg-gray-100 transition-all text-[14px]"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Citations Modal */}
      {showCitations && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-md flex items-center justify-center z-50 animate-fade-in">
          <div className="w-full max-w-2xl bg-gray-900/95 backdrop-blur-xl border border-white/10 rounded-3xl flex flex-col max-h-[85vh] animate-fade-in mx-4">
            {/* Citations Header */}
            <div className="flex justify-between items-center px-6 py-5 border-b border-white/10">
              <div>
                <h2 className="text-xl font-light tracking-tight">Sources & Citations</h2>
                <p className="text-[12px] text-gray-500 mt-1">Data used to generate the response</p>
              </div>
              <button
                onClick={() => setShowCitations(false)}
                className="w-9 h-9 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-all text-xl font-light"
              >
                ×
              </button>
            </div>

            {/* Citations List */}
            <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
              {citations.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <svg className="w-12 h-12 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p className="text-sm">No citations available yet.</p>
                  <p className="text-xs mt-1">Ask a question to see source references.</p>
                </div>
              ) : (
                citations.map((citation) => (
                  <div 
                    key={citation.id} 
                    className="bg-white/5 border border-white/10 rounded-2xl p-5 hover:bg-white/10 transition-all"
                  >
                    {/* Citation Header */}
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
                          <span className="text-purple-300 text-sm font-medium">{citation.id}</span>
                        </div>
                        <div>
                          <h3 className="text-sm font-medium text-white">{citation.source}</h3>
                          <p className="text-[11px] text-gray-500">Page {citation.page}</p>
                        </div>
                      </div>
                      <span className="px-2 py-1 bg-green-500/20 text-green-400 text-[10px] rounded-full font-medium">
                        Rank #{citation.relevance_rank}
                      </span>
                    </div>
                    
                    {/* Citation Excerpt */}
                    <div className="bg-black/30 rounded-xl p-4">
                      <p className="text-[12px] text-gray-300 leading-relaxed font-light italic">
                        "{citation.excerpt}"
                      </p>
                    </div>
                    
                    {/* Citation Footer */}
                    <div className="mt-3 flex items-center gap-2 text-[10px] text-gray-500">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span>Policy: {citation.policy_name}</span>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Citations Footer */}
            {citations.length > 0 && (
              <div className="px-6 py-4 border-t border-white/10 bg-white/5">
                <p className="text-[11px] text-gray-500 text-center">
                  💡 These excerpts from your policy documents were used to generate the response above.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Empathy Engine Details Modal */}
      {showEmpathyDetails && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-md flex items-center justify-center z-50 animate-fade-in">
          <div className="w-full max-w-lg bg-gray-900/95 backdrop-blur-xl border border-white/10 rounded-3xl flex flex-col max-h-[80vh] animate-fade-in mx-4">
            {/* Header */}
            <div className="flex justify-between items-center px-6 py-5 border-b border-white/10">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{getEmotionIcon(currentEmotion)}</span>
                <div>
                  <h2 className="text-xl font-light tracking-tight">Empathy Engine</h2>
                  <p className="text-[12px] text-gray-500 mt-0.5">Dynamic Tone & Strategy Adjustment</p>
                </div>
              </div>
              <button
                onClick={() => setShowEmpathyDetails(false)}
                className="w-9 h-9 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-all text-xl font-light"
              >
                ×
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
              {/* Current State */}
              <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
                <div className="text-[10px] font-medium text-gray-500 uppercase tracking-widest mb-3">
                  Detected Emotional State
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                      isEmergency ? 'bg-teal-500/20' : 'bg-purple-500/20'
                    }`}>
                      <span className="text-2xl">{getEmotionIcon(currentEmotion)}</span>
                    </div>
                    <div>
                      <div className="text-lg font-medium">{getEmotionLabel(currentEmotion)}</div>
                      <div className="text-xs text-gray-500">
                        {Math.round(empathyConfidence * 100)}% confidence
                      </div>
                    </div>
                  </div>
                  {isEmergency && (
                    <span className="px-3 py-1.5 bg-teal-500/20 text-teal-400 text-xs rounded-full font-medium flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 bg-teal-400 rounded-full animate-pulse" />
                      Emergency Mode
                    </span>
                  )}
                </div>
              </div>

              {/* Mode Explanation */}
              <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
                <div className="text-[10px] font-medium text-gray-500 uppercase tracking-widest mb-3">
                  Current Mode
                </div>
                <div className="text-sm text-gray-300 leading-relaxed">
                  {empathyMode === 'emergency_triage' ? (
                    <>
                      <div className="font-medium text-teal-400 mb-2">🆘 Emergency Triage Active</div>
                      <p>Detected urgency in your message. I've switched to emergency mode:</p>
                      <ul className="mt-2 space-y-1 text-xs text-gray-400">
                        <li>• Providing immediate safety steps first</li>
                        <li>• Using slower, calmer voice delivery</li>
                        <li>• Focusing on one action at a time</li>
                        <li>• Policy details will come after safety</li>
                      </ul>
                    </>
                  ) : currentEmotion === 'angry' ? (
                    <>
                      <div className="font-medium text-blue-400 mb-2">😤 De-escalation Mode</div>
                      <p>I sense frustration. I'm here to help:</p>
                      <ul className="mt-2 space-y-1 text-xs text-gray-400">
                        <li>• Acknowledging your concerns first</li>
                        <li>• Using a calm, measured tone</li>
                        <li>• Providing clear solutions quickly</li>
                      </ul>
                    </>
                  ) : currentEmotion === 'anxious' ? (
                    <>
                      <div className="font-medium text-cyan-400 mb-2">😰 Reassurance Mode</div>
                      <p>I understand you may be worried. I'm adapting to:</p>
                      <ul className="mt-2 space-y-1 text-xs text-gray-400">
                        <li>• Speak more slowly and clearly</li>
                        <li>• Emphasize what's covered</li>
                        <li>• Provide clear next steps</li>
                      </ul>
                    </>
                  ) : currentEmotion === 'confused' ? (
                    <>
                      <div className="font-medium text-purple-400 mb-2">🤔 Clarity Mode</div>
                      <p>I'll make sure to explain things simply:</p>
                      <ul className="mt-2 space-y-1 text-xs text-gray-400">
                        <li>• Using everyday language</li>
                        <li>• Breaking down complex terms</li>
                        <li>• Speaking at a comfortable pace</li>
                      </ul>
                    </>
                  ) : (
                    <>
                      <div className="font-medium text-gray-300 mb-2">😊 Standard Mode</div>
                      <p>Providing efficient, clear responses:</p>
                      <ul className="mt-2 space-y-1 text-xs text-gray-400">
                        <li>• Direct and factual information</li>
                        <li>• Professional tone</li>
                        <li>• Concise answers</li>
                      </ul>
                    </>
                  )}
                </div>
              </div>

              {/* Voice Adaptation */}
              <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
                <div className="text-[10px] font-medium text-gray-500 uppercase tracking-widest mb-3">
                  Voice Adaptation
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Voice Style</div>
                    <div className="text-sm font-medium capitalize">{ttsSettings.voice}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Speech Speed</div>
                    <div className="text-sm font-medium">
                      {ttsSettings.speed < 0.9 ? 'Slower (calming)' : 
                       ttsSettings.speed > 1.0 ? 'Slightly faster' : 'Normal'}
                    </div>
                  </div>
                </div>
                <div className="mt-3 h-2 bg-black/30 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-teal-500 to-purple-500 transition-all duration-500"
                    style={{ width: `${ttsSettings.speed * 100}%` }}
                  />
                </div>
                <div className="flex justify-between text-[10px] text-gray-500 mt-1">
                  <span>Calm</span>
                  <span>Normal</span>
                  <span>Efficient</span>
                </div>
              </div>

              {emergencyType && (
                <div className="bg-teal-500/10 border border-teal-500/30 rounded-2xl p-5">
                  <div className="text-[10px] font-medium text-teal-400 uppercase tracking-widest mb-2">
                    Emergency Type Detected
                  </div>
                  <div className="text-sm font-medium text-white capitalize">{emergencyType}</div>
                  <p className="text-xs text-gray-400 mt-2">
                    Safety instructions are being prioritized over policy information.
                  </p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-white/10 bg-white/5">
              <p className="text-[11px] text-gray-500 text-center">
                💡 The Empathy Engine analyzes your voice patterns and words to provide emotionally intelligent responses.
              </p>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes fade-in {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes slide-up {
          from { opacity: 0; transform: translateY(100%); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fade-in {
          animation: fade-in 0.6s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .animate-slide-up {
          animation: slide-up 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        }
      `}</style>
    </div>
  );
}
