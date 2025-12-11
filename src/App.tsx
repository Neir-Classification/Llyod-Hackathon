import { useEffect, useState, useMemo } from 'react';
import Iridescence from './components/Iridescence';
import { useAudioLevel } from './hooks/useAudioLevel';

interface ChatMessage {
  text: string;
  role: 'user' | 'assistant';
}

export default function App() {
  const { levelRef, ready, error, start } = useAudioLevel();
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
  const [audioContext, setAudioContext] = useState<AudioContext | null>(null);
  const vadFrameRef = useState<{ id: number | null }>({ id: null })[0];

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

  // Calculate orb properties based on animation state
  const orbColor: [number, number, number] = 
    animationState === 'listening' ? [0.3, 0.5, 1.0] : // Blue when listening
    [0.8, 0.4, 0.9]; // Purple for idle/thinking/responding
  
  const amplitude = 
    animationState === 'idle' ? 0.15 :
    animationState === 'listening' ? 0.18 + level * 1.7 : // Audio-reactive
    animationState === 'thinking' ? 0.3 : // Pulsing
    0.25; // Steady
  
  const speed = 
    animationState === 'idle' ? 0.5 :
    animationState === 'listening' ? 0.75 + level * 0.5 : // Audio-reactive
    animationState === 'thinking' ? 1.5 : // Fast pulsing
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
    console.log('🎬 Starting recording, ready:', ready, 'isRecording:', isRecording);
    
    // Prevent multiple simultaneous recordings
    if (isRecording) {
      console.log('⚠️ Already recording, ignoring request');
      return;
    }
    
    // Cancel any lingering VAD animation frame
    if (vadFrameRef.id !== null) {
      console.log('🧹 Canceling previous VAD frame:', vadFrameRef.id);
      cancelAnimationFrame(vadFrameRef.id);
      vadFrameRef.id = null;
    }
    
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
        console.log('🛑 Recorder stopped - cleaning up');
        
        // Stop all tracks
        stream.getTracks().forEach(t => {
          t.stop();
          console.log('🔌 Stopped track:', t.kind);
        });
        
        // Close audio context
        if (audioCtx) {
          try {
            await audioCtx.close();
            console.log('🔇 Audio context closed');
          } catch (e) {
            console.warn('Audio context close error:', e);
          }
        }
        
        // Cancel VAD animation frame
        if (vadFrameRef.id !== null) {
          console.log('🧹 Canceling VAD frame on stop:', vadFrameRef.id);
          cancelAnimationFrame(vadFrameRef.id);
          vadFrameRef.id = null;
        }
        
        setRecordedChunks(allChunks);
        setMediaRecorder(null);
        setAudioContext(null);
        setIsRecording(false);
        
        // Process full audio immediately
        await processVoiceInput(allChunks, mimeType || 'audio/webm');
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
        // Check if we should continue monitoring
        if (!isChecking) {
          console.log('⛔ VAD checking stopped by flag');
          vadFrameRef.id = null;
          return;
        }
        
        if (!recorder || recorder.state !== 'recording') {
          console.log('⛔ VAD stopped - recorder state:', recorder?.state);
          vadFrameRef.id = null;
          return;
        }

        const rms = calculateRMS();
        const level = rms * 100; // Scale to 0-100
        
        // Calibrate noise floor in first second
        if (calibrationSamples < CALIBRATION_FRAMES) {
          noiseFloor = Math.max(noiseFloor, level);
          calibrationSamples++;
          if (calibrationSamples === CALIBRATION_FRAMES) {
            console.log('🎚️ Noise floor calibrated:', noiseFloor.toFixed(2));
          }
          vadFrameRef.id = requestAnimationFrame(checkAudioLevel);
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
              console.log('🔇 Silence started');
            } else {
              const silenceDuration = Date.now() - silenceStart;
              if (silenceDuration > SILENCE_DURATION) {
                console.log('🛑 AUTO-STOP: Silence detected for', silenceDuration, 'ms');
                isChecking = false;
                vadFrameRef.id = null;
                if (recorder.state === 'recording') {
                  recorder.stop();
                }
                return;
              }
            }
          } else {
            if (silenceStart !== null) {
              console.log('🔊 Speech resumed');
            }
            silenceStart = null;
          }
        }

        vadFrameRef.id = requestAnimationFrame(checkAudioLevel);
      };

      // Start VAD after setup
      setTimeout(() => {
        console.log('🎬 Starting Voice Activity Detection (VAD)');
        checkAudioLevel();
      }, 100);
    } catch (err) {
      console.error('Microphone access error:', err);
      setStatusText('Microphone access denied');
    }
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

  // Process voice input
  const processVoiceInput = async (chunks: Blob[], mimeType: string) => {
    if (chunks.length === 0) return;

    setIsProcessing(true);
    setAnimationState('thinking');
    setStatusText('Processing...');

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

      // Get RAG response
      await sendQuery(query);
    } catch (err: any) {
      console.error('Error processing voice input:', err);
      setStatusText('Error. Try again.');
      setTranscript(`Error: ${err.message}`);
      setIsProcessing(false);
      setAnimationState('idle');
    }
  };

  // Send query to backend with conversation history
  const sendQuery = async (query: string) => {
    if (!query.trim()) return;

    setIsProcessing(true);
    setStatusText('Sending query...');

    try {
      // Prepare conversation history BEFORE adding new message
      // This sends the history WITHOUT the current query (backend uses it as context)
      const conversationHistory = chatMessages.map(msg => ({
        role: msg.role,
        content: msg.text
      }));

      console.log('📤 Sending query with history:', conversationHistory.length, 'messages');
      console.log('📝 History:', conversationHistory);

      const ragRes = await fetch('/rag-query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query, 
          tone: 'neutral', 
          k: 2,
          conversation_history: conversationHistory
        })
      });

      if (!ragRes.ok) throw new Error('RAG query failed');
      const ragData = await ragRes.json();
      const responseText = ragData.response;

      setResponse(responseText);
      
      // NOW add both user message and assistant response to chat
      setChatMessages(prev => [
        ...prev, 
        { text: query, role: 'user' },
        { text: responseText, role: 'assistant' }
      ]);

      // Show subtitle
      setSubtitle(responseText);
      setShowSubtitle(true);

      // Generate and play speech
      setStatusText('Generating response...');
      console.log('🔊 Requesting TTS for:', responseText);
      
      const ttsRes = await fetch('/text-to-speech', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: responseText, voice: 'alloy', audio_format: 'mp3' })
      });

      if (!ttsRes.ok) {
        const errorText = await ttsRes.text();
        console.error('TTS failed:', ttsRes.status, errorText);
        throw new Error(`TTS failed: ${ttsRes.status}`);
      }
      
      console.log('✅ TTS response received');
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

  // Send chat message with conversation history
  const sendChatMessage = async () => {
    const text = chatInput.trim();
    if (!text) return;

    const newUserMessage = { text, role: 'user' as const };
    setChatMessages(prev => [...prev, newUserMessage]);
    setChatInput('');

    try {
      // Prepare conversation history (exclude the message we just added)
      const conversationHistory = chatMessages.map(msg => ({
        role: msg.role,
        content: msg.text
      }));

      const res = await fetch('/rag-query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: text, 
          tone: 'neutral', 
          k: 2,
          conversation_history: conversationHistory
        })
      });

      if (!res.ok) throw new Error('Query failed');
      const data = await res.json();
      setChatMessages(prev => [...prev, { text: data.response, role: 'assistant' }]);
    } catch (err: any) {
      setChatMessages(prev => [...prev, { text: `Error: ${err.message}`, role: 'assistant' }]);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-black text-white overflow-hidden">
      {/* Background gradient */}
      <div className="fixed inset-0 bg-gradient-radial from-purple-900/5 via-transparent to-transparent pointer-events-none" />
      
      {/* Top Left Buttons */}
      <div className="fixed top-8 left-8 flex gap-3 z-30">
        {/* Message button */}
        <button
          onClick={() => setShowChat(true)}
          className="w-12 h-12 rounded-full bg-white/10 hover:bg-white/15 border border-white/10 transition-all duration-300 flex items-center justify-center"
          title="Text chat"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        </button>
        
        {/* Clear History button */}
        {chatMessages.length > 0 && (
          <button
            onClick={() => {
              setChatMessages([]);
              setTranscript('Waiting for input...');
              setResponse('Processing...');
              console.log('🗑️ Conversation history cleared');
            }}
            className="w-12 h-12 rounded-full bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 transition-all duration-300 flex items-center justify-center"
            title="Clear conversation history"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        )}
      </div>
      
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
        <p className="text-lg text-gray-400 mb-2 animate-fade-in font-light tracking-wide">
          {isRecording ? 'Listening... (speak naturally, will auto-stop)' : statusText}
        </p>
        
        {/* Conversation Context Indicator */}
        {chatMessages.length > 0 && (
          <p className="text-sm text-purple-400/60 mb-8 animate-fade-in font-light">
            {chatMessages.length} message{chatMessages.length !== 1 ? 's' : ''} in conversation
          </p>
        )}
        {chatMessages.length === 0 && <div className="mb-8"></div>}

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
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}>
                  <div className={`max-w-[75%] px-5 py-3 rounded-2xl text-[14px] leading-relaxed font-light ${
                    msg.role === 'user' 
                      ? 'bg-white text-black rounded-tr-sm' 
                      : 'bg-white/10 text-gray-100 rounded-tl-sm'
                  }`}>
                    {msg.text}
                  </div>
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
