import { useEffect, useState, useRef } from 'react';
import Iridescence from './components/Iridescence';
import { useAudioLevel } from './hooks/useAudioLevel';

interface Citation {
  policy_name: string;
  page_number: number | string;
  content: string;
  score?: number;
}

interface ChatMessage {
  text: string;
  role: 'user' | 'assistant';
  citations?: Citation[];
}

// Demo mode prompts - easily configurable
const DEMO_PROMPTS = [
  "My house got burned down in a recent forest fire what can I do to claim insurance",
  "I'm in urgent need of money and I want you to help me with right away",
  "I need more money it's not enough I need atleast then thousand euros",
  "I want to talk to a human"
];

export default function App() {
  const { levelRef, ready, error, start } = useAudioLevel();
  const [level, setLevel] = useState(0);
  const [greetingText, setGreetingText] = useState('');
  const [greetingTime, setGreetingTime] = useState('');
  const [statusText, setStatusText] = useState('Listening...');
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState('Waiting for input...');
  const [response, setResponse] = useState('Processing...');
  const [subtitle, setSubtitle] = useState('');
  const [showSubtitle, setShowSubtitle] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [currentCitations, setCurrentCitations] = useState<Citation[]>([]);
  const [showCitations, setShowCitations] = useState(false);
  
  // Demo mode state - REMOVE THIS SECTION TO DISABLE DEMO MODE
  const [demoIndex, setDemoIndex] = useState(0);
  const [demoActive, setDemoActive] = useState(true); // Set to false to disable demo mode
  const [showHandoff, setShowHandoff] = useState(false);
  const [conversationSummary, setConversationSummary] = useState('');
  // END DEMO MODE STATE
  
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [recordedChunks, setRecordedChunks] = useState<Blob[]>([]);
  const [animationState, setAnimationState] = useState<'idle' | 'listening' | 'thinking' | 'responding'>('idle');
  const [audioContext, setAudioContext] = useState<AudioContext | null>(null);
  const vadFrameRef = useState<{ id: number | null }>({ id: null })[0];
  
  // Dual-pipeline state
  const [quickResponsePlaying, setQuickResponsePlaying] = useState(false);
  const [fullResponseReady, setFullResponseReady] = useState(false);
  const pendingFullAudioRef = useState<{ audio: HTMLAudioElement | null, text: string, citations: Citation[] }>({ audio: null, text: '', citations: [] })[0];
  
  // Audio playback tracking - prevents overlapping audio
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  
  // Stop any currently playing audio
  const stopCurrentAudio = () => {
    if (currentAudioRef.current) {
      console.log('🔇 Stopping current audio');
      currentAudioRef.current.pause();
      currentAudioRef.current.currentTime = 0;
      // Revoke the object URL if it exists
      if (currentAudioRef.current.src.startsWith('blob:')) {
        URL.revokeObjectURL(currentAudioRef.current.src);
      }
      currentAudioRef.current = null;
    }
  };
  
  // Play audio and track it
  const playAudio = async (audio: HTMLAudioElement): Promise<void> => {
    // Stop any currently playing audio first
    stopCurrentAudio();
    
    // Track this audio
    currentAudioRef.current = audio;
    
    try {
      await audio.play();
      console.log('▶️ Audio playing');
    } catch (err) {
      console.error('❌ Audio play failed:', err);
      currentAudioRef.current = null;
      throw err;
    }
  };

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

  // DEMO MODE: Key press handler - Press 'e' to advance to next prompt
  // REMOVE THIS SECTION TO DISABLE DEMO MODE
  useEffect(() => {
    if (!demoActive) return;

    const handleKeyPress = async (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === 'e' && !isProcessing && !showHandoff) {
        e.preventDefault();
        
        if (demoIndex < DEMO_PROMPTS.length) {
          console.log(`🎬 [DEMO] Running prompt ${demoIndex + 1}/${DEMO_PROMPTS.length}`);
          const query = DEMO_PROMPTS[demoIndex];
          setDemoIndex(prev => prev + 1);
          
          // Check if this is the last prompt (human handoff)
          if (demoIndex === DEMO_PROMPTS.length - 1) {
            await sendDemoQuery(query, true);
          } else {
            await sendDemoQuery(query, false);
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [demoActive, demoIndex, isProcessing, showHandoff]);
  // END DEMO MODE KEY HANDLER

  // DEMO MODE: Send demo query function
  // REMOVE THIS SECTION TO DISABLE DEMO MODE
  const sendDemoQuery = async (query: string, isHandoff: boolean) => {
    // Stop any currently playing audio before starting new query
    stopCurrentAudio();
    
    setIsProcessing(true);
    setAnimationState('thinking');
    setStatusText('Processing...');
    setTranscript(query);

    try {
      // If this is the handoff query, skip RAG and just play handoff message
      if (isHandoff) {
        console.log('📞 [DEMO] Handoff requested - skipping RAG, connecting to human');
        
        const handoffMessage = "I understand you'd like to speak with a human agent. I'm connecting you now to one of our customer service representatives who will be able to assist you further with your insurance claim. Please hold for just a moment while I transfer your call and provide them with a summary of our conversation.";
        
        // Add to chat messages
        setChatMessages(prev => [
          ...prev, 
          { text: query, role: 'user' },
          { text: handoffMessage, role: 'assistant' }
        ]);
        
        // Generate TTS for handoff message
        const ttsRes = await fetch('/text-to-speech', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: handoffMessage, voice: 'alloy', audio_format: 'mp3' })
        });
        
        if (!ttsRes.ok) throw new Error('TTS failed');
        const audioBlob = await ttsRes.blob();
        
        setSubtitle(handoffMessage);
        setShowSubtitle(true);
        setAnimationState('responding');
        setStatusText('Connecting to human...');
        setResponse(handoffMessage);
        
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        audio.volume = 1.0;
        
        audio.addEventListener('ended', () => {
          console.log('🎵 [DEMO] Handoff message ended');
          setShowSubtitle(false);
          setAnimationState('idle');
          setIsProcessing(false);
          URL.revokeObjectURL(audioUrl);
          currentAudioRef.current = null;
          
          // Generate conversation summary and show handoff modal
          const allMessages = [...chatMessages, { text: query, role: 'user' as const }, { text: handoffMessage, role: 'assistant' as const }];
          const summary = generateConversationSummary(allMessages);
          setConversationSummary(summary);
          setShowHandoff(true);
          setStatusText('Connected to human agent');
        });
        
        audio.addEventListener('error', (e) => {
          console.error('❌ Handoff audio error:', e);
          setIsProcessing(false);
          setAnimationState('idle');
          URL.revokeObjectURL(audioUrl);
          currentAudioRef.current = null;
        });
        
        await playAudio(audio);
        return;
      }

      // Normal demo query flow (not handoff)
      // Prepare conversation history BEFORE adding new message
      const conversationHistory = chatMessages.map(msg => ({
        role: msg.role,
        content: msg.text
      }));

      console.log('📤 [DEMO] Sending query:', query);

      // Step 1: Get quick response audio immediately
      const quickFormData = new FormData();
      quickFormData.append('query', query);
      quickFormData.append('tone', 'neutral');
      quickFormData.append('voice', 'alloy');

      const quickRes = await fetch('/quick-response-audio', {
        method: 'POST',
        body: quickFormData,
      });

      if (quickRes.ok) {
        // Play quick response immediately
        const quickBlob = await quickRes.blob();
        const quickUrl = URL.createObjectURL(quickBlob);
        const quickAudio = new Audio(quickUrl);
        quickAudio.volume = 1.0;
        
        const quickText = quickRes.headers.get('X-Quick-Response-Text') || 'Processing...';
        setSubtitle(quickText);
        setShowSubtitle(true);
        setAnimationState('responding');
        setStatusText('Acknowledging...');
        setQuickResponsePlaying(true);
        
        console.log('🎵 [DEMO-QUICK] Playing quick response:', quickText);
        
        // Start fetching full response in parallel
        const fullResponsePromise = (async () => {
          const fullRes = await fetch('/rag-query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
              query, 
              tone: 'neutral', 
              k: 2,
              conversation_history: conversationHistory
            })
          });
          
          if (!fullRes.ok) throw new Error('RAG query failed');
          const ragData = await fullRes.json();
          
          // Generate TTS for full response
          const ttsRes = await fetch('/text-to-speech', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: ragData.response, voice: 'alloy', audio_format: 'mp3' })
          });
          
          if (!ttsRes.ok) throw new Error('TTS failed');
          const audioBlob = await ttsRes.blob();
          
          return { response: ragData.response, citations: ragData.citations || [], audioBlob };
        })();
        
        // Set up quick audio end handler
        quickAudio.addEventListener('ended', async () => {
          console.log('🎵 [DEMO-QUICK] Quick response ended');
          URL.revokeObjectURL(quickUrl);
          setQuickResponsePlaying(false);
          currentAudioRef.current = null;
          
          try {
            const { response: fullText, citations, audioBlob } = await fullResponsePromise;
            
            setResponse(fullText);
            setCurrentCitations(citations);
            setChatMessages(prev => [
              ...prev, 
              { text: query, role: 'user' },
              { text: fullText, role: 'assistant', citations }
            ]);
            
            // Update subtitle and play full audio
            setSubtitle(fullText);
            const fullUrl = URL.createObjectURL(audioBlob);
            const fullAudio = new Audio(fullUrl);
            fullAudio.volume = 1.0;
            
            setStatusText('Speaking...');
            console.log('🎵 [DEMO-FULL] Playing full response');
            
            fullAudio.addEventListener('ended', async () => {
              console.log('🎵 [DEMO-FULL] Full response ended');
              setShowSubtitle(false);
              setAnimationState('idle');
              setIsProcessing(false);
              URL.revokeObjectURL(fullUrl);
              currentAudioRef.current = null;
              setStatusText('Listening...');
            });
            
            fullAudio.addEventListener('error', (e) => {
              console.error('❌ Full audio playback error:', e);
              setStatusText('Audio error');
              setIsProcessing(false);
              setAnimationState('idle');
              URL.revokeObjectURL(fullUrl);
              currentAudioRef.current = null;
            });
            
            await playAudio(fullAudio);
            
          } catch (err: any) {
            console.error('❌ Full response failed:', err);
            setStatusText('Error getting full response');
            setIsProcessing(false);
            setAnimationState('idle');
          }
        });
        
        quickAudio.addEventListener('error', (e) => {
          console.error('❌ Quick audio error:', e);
          URL.revokeObjectURL(quickUrl);
          setQuickResponsePlaying(false);
          currentAudioRef.current = null;
          setIsProcessing(false);
          setAnimationState('idle');
        });
        
        // Play quick audio
        await playAudio(quickAudio);
        
      } else {
        console.warn('⚠️ Quick response failed');
        setStatusText('Error. Try again.');
        setIsProcessing(false);
        setAnimationState('idle');
      }
      
    } catch (err: any) {
      console.error('Error in demo query:', err);
      setStatusText('Error. Try again.');
      setIsProcessing(false);
      setAnimationState('idle');
    }
  };

  // Generate conversation summary for handoff
  const generateConversationSummary = (messages: ChatMessage[]) => {
    const userMessages = messages.filter(m => m.role === 'user');
    
    let summary = '📋 CONVERSATION SUMMARY\n\n';
    summary += '👤 Customer Issue:\n';
    summary += '• House burned down in forest fire\n';
    summary += '• Seeking insurance claim assistance\n';
    summary += '• Urgent need for funds\n';
    summary += '• Requesting €10,00,000\n\n';
    summary += '🤖 AI Actions Taken:\n';
    summary += '• Provided initial claim filing guidance\n';
    summary += '• Explained documentation requirements\n';
    summary += '• Discussed claim limits and process\n\n';
    summary += '⚠️ Escalation Reason:\n';
    summary += '• Customer requested human agent\n';
    summary += '• Complex claim amount negotiation needed\n\n';
    summary += `💬 Total Exchanges: ${userMessages.length} user messages`;
    
    return summary;
  };
  // END DEMO MODE FUNCTIONS

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

  // Send query to backend with dual-pipeline (quick + full response)
  const sendQuery = async (query: string) => {
    if (!query.trim()) return;

    // Stop any currently playing audio before starting new query
    stopCurrentAudio();
    
    setIsProcessing(true);
    setStatusText('Processing...');

    try {
      // Prepare conversation history BEFORE adding new message
      const conversationHistory = chatMessages.map(msg => ({
        role: msg.role,
        content: msg.text
      }));

      console.log('📤 [DUAL-PIPELINE] Sending query:', query);

      // Step 1: Get quick response audio immediately
      const quickFormData = new FormData();
      quickFormData.append('query', query);
      quickFormData.append('tone', 'neutral');
      quickFormData.append('voice', 'alloy');

      const quickRes = await fetch('/quick-response-audio', {
        method: 'POST',
        body: quickFormData,
      });

      if (quickRes.ok) {
        // Play quick response immediately
        const quickBlob = await quickRes.blob();
        const quickUrl = URL.createObjectURL(quickBlob);
        const quickAudio = new Audio(quickUrl);
        quickAudio.volume = 1.0;
        
        const quickText = quickRes.headers.get('X-Quick-Response-Text') || 'Processing...';
        setSubtitle(quickText);
        setShowSubtitle(true);
        setAnimationState('responding');
        setStatusText('Acknowledging...');
        setQuickResponsePlaying(true);
        
        console.log('🎵 [QUICK] Playing quick response:', quickText);
        
        // Start fetching full response in parallel
        const fullResponsePromise = (async () => {
          const fullRes = await fetch('/rag-query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
              query, 
              tone: 'neutral', 
              k: 2,
              conversation_history: conversationHistory
            })
          });
          
          if (!fullRes.ok) throw new Error('RAG query failed');
          const ragData = await fullRes.json();
          
          // Generate TTS for full response
          const ttsRes = await fetch('/text-to-speech', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: ragData.response, voice: 'alloy', audio_format: 'mp3' })
          });
          
          if (!ttsRes.ok) throw new Error('TTS failed');
          const audioBlob = await ttsRes.blob();
          
          return { response: ragData.response, citations: ragData.citations || [], audioBlob };
        })();
        
        // Set up quick audio end handler
        quickAudio.addEventListener('ended', async () => {
          console.log('🎵 [QUICK] Quick response ended, transitioning to full response');
          URL.revokeObjectURL(quickUrl);
          setQuickResponsePlaying(false);
          currentAudioRef.current = null; // Clear ref since audio ended
          
          // Wait for full response if not ready yet
          try {
            const { response: fullText, citations, audioBlob } = await fullResponsePromise;
            
            setResponse(fullText);
            setCurrentCitations(citations);
            setChatMessages(prev => [
              ...prev, 
              { text: query, role: 'user' },
              { text: fullText, role: 'assistant', citations }
            ]);
            
            // Update subtitle and play full audio
            setSubtitle(fullText);
            const fullUrl = URL.createObjectURL(audioBlob);
            const fullAudio = new Audio(fullUrl);
            fullAudio.volume = 1.0;
            
            setStatusText('Speaking...');
            console.log('🎵 [FULL] Playing full response:', fullText.substring(0, 50) + '...');
            
            fullAudio.addEventListener('ended', async () => {
              console.log('🎵 [FULL] Full response ended');
              setShowSubtitle(false);
              setAnimationState('idle');
              setTranscript('Waiting for input...');
              setResponse('Processing...');
              setIsProcessing(false);
              URL.revokeObjectURL(fullUrl);
              currentAudioRef.current = null; // Clear ref since audio ended
              
              // Auto-restart listening
              setTimeout(async () => {
                console.log('🔄 Auto-starting next recording...');
                await startRecording();
              }, 500);
            });
            
            fullAudio.addEventListener('error', (e) => {
              console.error('❌ Full audio playback error:', e);
              setStatusText('Audio error - Click to retry');
              setIsProcessing(false);
              setAnimationState('idle');
              URL.revokeObjectURL(fullUrl);
              currentAudioRef.current = null;
            });
            
            await playAudio(fullAudio);
            
          } catch (err: any) {
            console.error('❌ Full response failed:', err);
            setStatusText('Error getting full response');
            setIsProcessing(false);
            setAnimationState('idle');
          }
        });
        
        quickAudio.addEventListener('error', async (e) => {
          console.error('❌ Quick audio error:', e);
          URL.revokeObjectURL(quickUrl);
          setQuickResponsePlaying(false);
          currentAudioRef.current = null;
          
          // Fall back to waiting for full response
          try {
            const { response: fullText, citations, audioBlob } = await fullResponsePromise;
            setResponse(fullText);
            setCurrentCitations(citations);
            setChatMessages(prev => [
              ...prev, 
              { text: query, role: 'user' },
              { text: fullText, role: 'assistant', citations }
            ]);
            
            // Play full audio directly
            setSubtitle(fullText);
            setShowSubtitle(true);
            const fullUrl = URL.createObjectURL(audioBlob);
            const fullAudio = new Audio(fullUrl);
            fullAudio.volume = 1.0;
            
            fullAudio.addEventListener('ended', async () => {
              setShowSubtitle(false);
              setAnimationState('idle');
              setTranscript('Waiting for input...');
              setResponse('Processing...');
              setIsProcessing(false);
              URL.revokeObjectURL(fullUrl);
              currentAudioRef.current = null;
              setTimeout(() => startRecording(), 500);
            });
            
            await playAudio(fullAudio);
          } catch (err) {
            console.error('❌ Fallback also failed:', err);
            setStatusText('Error. Try again.');
            setIsProcessing(false);
            setAnimationState('idle');
          }
        });
        
        // Play quick audio
        await playAudio(quickAudio);
        
      } else {
        // Fallback to original single-pipeline if quick response fails
        console.warn('⚠️ Quick response failed, falling back to single pipeline');
        await sendQuerySinglePipeline(query, conversationHistory);
      }
      
    } catch (err: any) {
      console.error('Error in dual pipeline:', err);
      setStatusText('Error. Try again.');
      setResponse(`Error: ${err.message}`);
      setIsProcessing(false);
      setAnimationState('idle');
    }
  };

  // Fallback single-pipeline query (original implementation)
  const sendQuerySinglePipeline = async (query: string, conversationHistory: any[]) => {
    console.log('📤 [SINGLE] Sending query with history:', conversationHistory.length, 'messages');

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
    const citations = ragData.citations || [];

    setResponse(responseText);
    setCurrentCitations(citations);
    
    setChatMessages(prev => [
      ...prev, 
      { text: query, role: 'user' },
      { text: responseText, role: 'assistant', citations: citations }
    ]);

    setSubtitle(responseText);
    setShowSubtitle(true);

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
      currentAudioRef.current = null;
      
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
      currentAudioRef.current = null;
    });

    setStatusText('Speaking...');
    console.log('▶️ Playing audio...');
    
    try {
      await playAudio(audio);
      console.log('✅ Audio playing successfully');
    } catch (playErr) {
      console.error('❌ Play failed:', playErr);
      setStatusText('Audio play failed - check browser permissions');
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
      const citations = data.citations || [];
      setCurrentCitations(citations);
      setChatMessages(prev => [...prev, { text: data.response, role: 'assistant', citations: citations }]);
    } catch (err: any) {
      setChatMessages(prev => [...prev, { text: `Error: ${err.message}`, role: 'assistant' }]);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-black text-white overflow-hidden">
      {/* Background gradient */}
      <div className="fixed inset-0 bg-gradient-radial from-purple-900/5 via-transparent to-transparent pointer-events-none" />
      
      {/* DEMO MODE: Progress Bar - REMOVE THIS SECTION TO DISABLE DEMO MODE */}
      {/* Hidden for demo presentation - set to false to hide completely */}
      {false && demoActive && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 flex flex-col items-center gap-2">
          <div className="flex items-center gap-3 bg-black/80 backdrop-blur-xl border border-white/10 rounded-full px-4 py-2">
            <span className="text-xs text-gray-400 font-light">Demo Mode</span>
            <div className="flex gap-1">
              {DEMO_PROMPTS.map((_, idx) => (
                <div
                  key={idx}
                  className={`w-8 h-1.5 rounded-full transition-all duration-300 ${
                    idx < demoIndex 
                      ? 'bg-green-400' 
                      : idx === demoIndex 
                        ? isProcessing ? 'bg-yellow-400 animate-pulse' : 'bg-purple-400'
                        : 'bg-white/20'
                  }`}
                />
              ))}
            </div>
            <span className="text-xs text-gray-500">{demoIndex}/{DEMO_PROMPTS.length}</span>
          </div>
          {!isProcessing && demoIndex < DEMO_PROMPTS.length && !showHandoff && (
            <span className="text-xs text-gray-500 animate-pulse">Press E for next prompt</span>
          )}
        </div>
      )}
      {/* END DEMO MODE PROGRESS BAR */}
      
      {/* DEMO MODE: Handoff Modal - REMOVE THIS SECTION TO DISABLE DEMO MODE */}
      {showHandoff && (
        <div className="fixed inset-0 bg-black flex items-center justify-center z-50 animate-fade-in">
          <div className="w-full max-w-3xl mx-6 animate-slide-up">
            {/* Connecting Status */}
            <div className="text-center mb-16">
              <div className="inline-flex items-center gap-3 mb-6">
                <div className="relative">
                  <div className="w-3 h-3 bg-white rounded-full" />
                  <div className="absolute inset-0 w-3 h-3 bg-white rounded-full animate-ping opacity-75" />
                </div>
                <span className="text-2xl font-light tracking-tight text-white">Connecting to Agent</span>
              </div>
              <p className="text-white/40 text-sm font-light tracking-wide">
                Transferring conversation to a human representative
              </p>
            </div>
            
            {/* Summary Card */}
            <div className="bg-white/[0.03] backdrop-blur-sm border border-white/[0.08] rounded-2xl overflow-hidden">
              {/* Header */}
              <div className="px-8 py-6 border-b border-white/[0.08]">
                <h2 className="text-lg font-medium text-white tracking-tight">Conversation Summary</h2>
                <p className="text-white/40 text-sm font-light mt-1">Prepared for customer service agent</p>
              </div>
              
              {/* Summary Content */}
              <div className="px-8 py-8">
                {/* Issue Section */}
                <div className="mb-8">
                  <div className="text-xs font-medium text-white/30 uppercase tracking-widest mb-4">Customer Issue</div>
                  <div className="space-y-3">
                    <div className="flex items-start gap-3">
                      <div className="w-1 h-1 rounded-full bg-white/40 mt-2 flex-shrink-0" />
                      <span className="text-white/80 font-light">House burned down in forest fire</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-1 h-1 rounded-full bg-white/40 mt-2 flex-shrink-0" />
                      <span className="text-white/80 font-light">Seeking insurance claim assistance</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-1 h-1 rounded-full bg-white/40 mt-2 flex-shrink-0" />
                      <span className="text-white/80 font-light">Urgent need for funds</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-1 h-1 rounded-full bg-white/40 mt-2 flex-shrink-0" />
                      <span className="text-white/80 font-light">Requesting €10,000 coverage</span>
                    </div>
                  </div>
                </div>
                
                {/* Actions Section */}
                <div className="mb-8">
                  <div className="text-xs font-medium text-white/30 uppercase tracking-widest mb-4">AI Actions Taken</div>
                  <div className="space-y-3">
                    <div className="flex items-start gap-3">
                      <div className="w-1 h-1 rounded-full bg-white/40 mt-2 flex-shrink-0" />
                      <span className="text-white/80 font-light">Provided initial claim filing guidance</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-1 h-1 rounded-full bg-white/40 mt-2 flex-shrink-0" />
                      <span className="text-white/80 font-light">Explained documentation requirements</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-1 h-1 rounded-full bg-white/40 mt-2 flex-shrink-0" />
                      <span className="text-white/80 font-light">Discussed claim limits and process</span>
                    </div>
                  </div>
                </div>
                
                {/* Escalation Reason */}
                <div className="p-4 bg-white/[0.03] rounded-xl border border-white/[0.05]">
                  <div className="text-xs font-medium text-white/30 uppercase tracking-widest mb-3">Escalation Reason</div>
                  <p className="text-white/80 font-light">Customer requested human agent for complex claim negotiation</p>
                </div>
              </div>
              
              {/* Footer Stats */}
              <div className="px-8 py-5 border-t border-white/[0.08] flex items-center justify-between">
                <div className="flex items-center gap-6">
                  <div>
                    <div className="text-2xl font-light text-white">{chatMessages.filter(m => m.role === 'user').length}</div>
                    <div className="text-xs text-white/30 font-light">Messages</div>
                  </div>
                  <div className="w-px h-8 bg-white/10" />
                  <div>
                    <div className="text-2xl font-light text-white">4</div>
                    <div className="text-xs text-white/30 font-light">Topics</div>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setShowHandoff(false);
                    setDemoIndex(0);
                    setChatMessages([]);
                    setTranscript('Waiting for input...');
                    setResponse('Processing...');
                    setStatusText('Listening...');
                  }}
                  className="px-5 py-2.5 bg-white text-black rounded-full text-sm font-medium hover:bg-white/90 transition-all"
                >
                  End Session
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      {/* END DEMO MODE HANDOFF MODAL */}
      
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
        
        {/* Dual Pipeline Indicator */}
        {quickResponsePlaying && (
          <div className="flex items-center gap-2 mb-2 animate-fade-in">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span className="text-xs text-green-400/80 font-light">Quick response • Full answer loading...</span>
          </div>
        )}
        
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
      <div className="fixed top-8 right-8 w-96 bg-black/80 backdrop-blur-2xl border border-white/10 rounded-2xl p-6 shadow-2xl transition-opacity duration-300">
        {/* Citations Button */}
        {currentCitations.length > 0 && (
          <button
            onClick={() => setShowCitations(true)}
            className="w-full mb-4 px-4 py-2 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 rounded-xl flex items-center justify-center gap-2 transition-all text-xs text-purple-300"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            View {currentCitations.length} Source{currentCitations.length !== 1 ? 's' : ''}
          </button>
        )}
        
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
                  <div className="flex flex-col gap-2 max-w-[75%]">
                    <div className={`px-5 py-3 rounded-2xl text-[14px] leading-relaxed font-light ${
                      msg.role === 'user' 
                        ? 'bg-white text-black rounded-tr-sm' 
                        : 'bg-white/10 text-gray-100 rounded-tl-sm'
                    }`}>
                      {msg.text}
                    </div>
                    {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                      <button
                        onClick={() => {
                          setCurrentCitations(msg.citations || []);
                          setShowCitations(true);
                        }}
                        className="self-start text-xs text-gray-400 hover:text-gray-200 flex items-center gap-1 transition-colors"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        View {msg.citations.length} source{msg.citations.length !== 1 ? 's' : ''}
                      </button>
                    )}
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

      {/* Citations Panel */}
      {showCitations && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-md flex items-center justify-end z-50 animate-fade-in" onClick={() => setShowCitations(false)}>
          <div 
            className="w-full max-w-md h-full bg-gray-900/95 backdrop-blur-xl border-l border-white/10 flex flex-col animate-slide-left"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Citations Header */}
            <div className="flex justify-between items-center px-6 py-5 border-b border-white/10">
              <div>
                <h2 className="text-xl font-light tracking-tight">Source Citations</h2>
                <p className="text-xs text-gray-400 mt-1">Retrieved from policy documents</p>
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
              {currentCitations.length === 0 ? (
                <div className="text-center text-gray-400 py-12">
                  <svg className="w-12 h-12 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p className="text-sm">No citations available</p>
                </div>
              ) : (
                currentCitations.map((citation, idx) => (
                  <div key={idx} className="bg-white/5 border border-white/10 rounded-xl p-4 space-y-3 animate-fade-in">
                    {/* Citation Header */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <svg className="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                          <span className="text-sm font-medium text-gray-200">{citation.policy_name}</span>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-gray-400">
                          <span>Page {citation.page_number}</span>
                          {citation.score !== undefined && (
                            <span className="px-2 py-0.5 bg-purple-500/20 text-purple-300 rounded-full">
                              {(1 / (1 + citation.score) * 100).toFixed(0)}% match
                            </span>
                          )}
                        </div>
                      </div>
                      <span className="text-xs text-gray-500 font-mono">#{idx + 1}</span>
                    </div>

                    {/* Citation Content */}
                    <div className="text-xs text-gray-300 leading-relaxed bg-black/30 rounded-lg p-3 border border-white/5">
                      {citation.content}
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Citations Footer */}
            <div className="px-6 py-4 border-t border-white/10 text-xs text-gray-400 text-center">
              Powered by FAISS vector similarity search
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes fade-in {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes slide-left {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
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
        .animate-slide-left {
          animation: slide-left 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
      `}</style>
    </div>
  );
}
