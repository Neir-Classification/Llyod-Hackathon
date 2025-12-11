import { useEffect, useState, useMemo } from 'react';
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

interface User {
  id: number;
  email: string;
  full_name: string;
  is_admin: boolean;
}

interface AdminDashboardProps {
  user: User;
  authToken: string | null;
  onLogout: () => void;
}

function AdminDashboard({ user, authToken, onLogout }: AdminDashboardProps) {
  const [users, setUsers] = useState<any[]>([]);
  const [policies, setPolicies] = useState<any[]>([]);
  const [tickets, setTickets] = useState<any[]>([]);
  const [interventions, setInterventions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'users' | 'policies' | 'tickets' | 'interventions'>('users');

  useEffect(() => {
    fetchAdminData();
  }, []);

  const fetchAdminData = async () => {
    setLoading(true);
    try {
      const headers: Record<string, string> = authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
      
      // Fetch all users
      const usersRes = await fetch('http://localhost:8000/admin/users', { headers });
      if (usersRes.ok) setUsers(await usersRes.json());

      // Fetch all policies
      const policiesRes = await fetch('http://localhost:8000/admin/policies', { headers });
      if (policiesRes.ok) setPolicies(await policiesRes.json());

      // Fetch all tickets
      const ticketsRes = await fetch('http://localhost:8000/admin/tickets', { headers });
      if (ticketsRes.ok) setTickets(await ticketsRes.json());

      // Fetch interventions
      const interventionsRes = await fetch('http://localhost:8000/admin/interventions', { headers });
      if (interventionsRes.ok) setInterventions(await interventionsRes.json());
    } catch (err) {
      console.error('Failed to fetch admin data:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <div className="border-b border-white/10 bg-black/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-full border border-white/20 flex items-center justify-center">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-light">Admin Dashboard</h1>
              <p className="text-xs text-gray-500">Insurance Management System</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-sm font-light">{user.full_name}</p>
              <p className="text-xs text-gray-500">Administrator</p>
            </div>
            <button
              onClick={onLogout}
              className="w-10 h-10 rounded-full border border-white/10 hover:border-white/30 transition-all flex items-center justify-center"
              title="Logout"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-8">
            {(['users', 'policies', 'tickets', 'interventions'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-4 text-sm font-light border-b-2 transition-colors ${
                  activeTab === tab
                    ? 'border-white text-white'
                    : 'border-transparent text-gray-500 hover:text-gray-300'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
                <span className="ml-2 text-xs">
                  ({tab === 'users' ? users.length : tab === 'policies' ? policies.length : tab === 'tickets' ? tickets.length : interventions.length})
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {loading ? (
          <div className="text-center py-12 text-gray-500">Loading...</div>
        ) : (
          <>
            {activeTab === 'users' && (
              <div className="space-y-4">
                {users.map((u) => (
                  <div key={u.id} className="border border-white/10 rounded-lg p-4 hover:border-white/20 transition-colors">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-light text-lg">{u.full_name}</h3>
                        <p className="text-sm text-gray-500">{u.email}</p>
                        <div className="flex gap-2 mt-2">
                          <span className={`text-xs px-2 py-1 rounded-full border ${u.is_admin ? 'border-blue-500/30 text-blue-400' : 'border-gray-500/30 text-gray-400'}`}>
                            {u.is_admin ? 'Admin' : 'Customer'}
                          </span>
                          <span className={`text-xs px-2 py-1 rounded-full border ${u.is_active ? 'border-green-500/30 text-green-400' : 'border-red-500/30 text-red-400'}`}>
                            {u.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </div>
                      </div>
                      <span className="text-xs text-gray-600 font-mono">ID: {u.id}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'policies' && (
              <div className="space-y-4">
                {policies.map((p) => (
                  <div key={p.id} className="border border-white/10 rounded-lg p-4 hover:border-white/20 transition-colors">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-light text-lg">{p.policy_number}</h3>
                        <p className="text-sm text-gray-500">{p.policy_type.toUpperCase()} Insurance</p>
                        <div className="flex gap-4 mt-2 text-xs text-gray-400">
                          <span>Premium: ${p.premium_amount?.toFixed(2)}/mo</span>
                          <span>Coverage: ${p.coverage_amount?.toLocaleString()}</span>
                          <span>Deductible: ${p.deductible}</span>
                        </div>
                      </div>
                      <span className={`text-xs px-2 py-1 rounded-full border ${p.status === 'active' ? 'border-green-500/30 text-green-400' : 'border-gray-500/30 text-gray-400'}`}>
                        {p.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'tickets' && (
              <div className="space-y-4">
                {tickets.map((t) => (
                  <div key={t.id} className="border border-white/10 rounded-lg p-4 hover:border-white/20 transition-colors">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <h3 className="font-light">{t.ticket_number}</h3>
                        <p className="text-sm text-gray-400 mt-1">{t.title}</p>
                      </div>
                      <div className="flex gap-2">
                        <span className={`text-xs px-2 py-1 rounded-full border ${
                          t.priority === 'urgent' ? 'border-red-500/30 text-red-400' :
                          t.priority === 'high' ? 'border-orange-500/30 text-orange-400' :
                          'border-gray-500/30 text-gray-400'
                        }`}>
                          {t.priority}
                        </span>
                        <span className={`text-xs px-2 py-1 rounded-full border ${
                          t.status === 'resolved' || t.status === 'closed' ? 'border-green-500/30 text-green-400' :
                          t.status === 'in_progress' ? 'border-blue-500/30 text-blue-400' :
                          'border-gray-500/30 text-gray-400'
                        }`}>
                          {t.status}
                        </span>
                      </div>
                    </div>
                    <p className="text-xs text-gray-500">{t.description}</p>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'interventions' && (
              <div className="space-y-4">
                {interventions.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">No interventions recorded</div>
                ) : (
                  interventions.map((i) => (
                    <div key={i.id} className="border border-white/10 rounded-lg p-4 hover:border-white/20 transition-colors">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h3 className="font-light">{i.trigger_reason}</h3>
                          <p className="text-xs text-gray-500 mt-1">AI Confidence: {(i.ai_confidence_score * 100).toFixed(0)}%</p>
                        </div>
                        <span className={`text-xs px-2 py-1 rounded-full border ${
                          i.status === 'resolved' ? 'border-green-500/30 text-green-400' :
                          i.status === 'active' ? 'border-blue-500/30 text-blue-400' :
                          'border-yellow-500/30 text-yellow-400'
                        }`}>
                          {i.status}
                        </span>
                      </div>
                      {i.admin_notes && (
                        <p className="text-xs text-gray-400 mt-2">Notes: {i.admin_notes}</p>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
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
  const [currentCitations, setCurrentCitations] = useState<Citation[]>([]);
  const [showCitations, setShowCitations] = useState(false);
  const [detectedEmotion, setDetectedEmotion] = useState<string>('neutral');
  
  // Authentication state
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [showLogin, setShowLogin] = useState(true);
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [userPolicies, setUserPolicies] = useState<any[]>([]);
  const [userTickets, setUserTickets] = useState<any[]>([]);
  
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

  // Fetch user policies and tickets when logged in
  useEffect(() => {
    if (isLoggedIn && authToken && !user?.is_admin) {
      const fetchUserData = async () => {
        try {
          const headers = { 'Authorization': `Bearer ${authToken}` };
          
          const policiesRes = await fetch('http://localhost:8000/me/policies', { headers });
          if (policiesRes.ok) {
            const data = await policiesRes.json();
            setUserPolicies(data.policies || []);
          }

          const ticketsRes = await fetch('http://localhost:8000/me/tickets', { headers });
          if (ticketsRes.ok) {
            const data = await ticketsRes.json();
            setUserTickets(data.tickets || []);
          }
        } catch (err) {
          console.error('Failed to fetch user data:', err);
        }
      };
      fetchUserData();
    }
  }, [isLoggedIn, authToken, user]);

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

      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
      }

      const ragRes = await fetch('/rag-query', {
        method: 'POST',
        headers,
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
      const emotion = ragData.detected_emotion || 'neutral';

      setResponse(responseText);
      setCurrentCitations(citations);
      setDetectedEmotion(emotion);
      
      // NOW add both user message and assistant response to chat (with citations)
      setChatMessages(prev => [
        ...prev, 
        { text: query, role: 'user' },
        { text: responseText, role: 'assistant', citations: citations }
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

      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
      }

      const res = await fetch('/rag-query', {
        method: 'POST',
        headers,
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
      const emotion = data.detected_emotion || 'neutral';
      setCurrentCitations(citations);
      setDetectedEmotion(emotion);
      setChatMessages(prev => [...prev, { text: data.response, role: 'assistant', citations: citations }]);
    } catch (err: any) {
      setChatMessages(prev => [...prev, { text: `Error: ${err.message}`, role: 'assistant' }]);
    }
  };

  // Handle login
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError('');
    setIsLoggingIn(true);

    try {
      const res = await fetch('http://localhost:8000/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: loginEmail,
          password: loginPassword
        })
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Login failed');
      }

      const data = await res.json();
      setAuthToken(data.access_token);
      setUser(data.user);
      setIsLoggedIn(true);
      setShowLogin(false);
      setGreetingText(`Welcome back, ${data.user.full_name.split(' ')[0]}`);
    } catch (err: any) {
      setLoginError(err.message || 'Login failed. Please try again.');
    } finally {
      setIsLoggingIn(false);
    }
  };

  // Show admin dashboard if user is admin
  if (isLoggedIn && user?.is_admin) {
    return <AdminDashboard user={user} authToken={authToken} onLogout={() => {
      setIsLoggedIn(false);
      setUser(null);
      setAuthToken(null);
      setShowLogin(true);
    }} />;
  }

  // Show login screen if not logged in (and user hasn't chosen guest mode)
  if (showLogin && !isLoggedIn) {
    return (
      <div className="relative flex min-h-screen items-center justify-center bg-black text-white overflow-hidden">
        {/* Subtle background pattern */}
        <div className="fixed inset-0 opacity-[0.02]" style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, white 1px, transparent 0)`,
          backgroundSize: '40px 40px'
        }} />
        
        {/* Login Card */}
        <div className="relative z-10 w-full max-w-md mx-4 animate-fade-in">
          <div className="border border-white/10 rounded-2xl p-8">
            {/* Logo/Title */}
            <div className="text-center mb-8">
              <div className="w-12 h-12 mx-auto mb-4 rounded-full border border-white/20 flex items-center justify-center">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <h1 className="text-2xl font-light tracking-tight mb-2">Insurance Assistant</h1>
              <p className="text-sm text-gray-500">Sign in to access your policies</p>
            </div>

            {/* Login Form */}
            <form onSubmit={handleLogin} className="space-y-5">
              {loginError && (
                <div className="border border-red-500/30 rounded-lg p-3 text-sm text-red-400 animate-fade-in">
                  {loginError}
                </div>
              )}

              <div>
                <label htmlFor="email" className="block text-sm text-gray-500 mb-2 font-light">Email Address</label>
                <input
                  id="email"
                  type="email"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  required
                  className="w-full px-4 py-3 bg-transparent border border-white/10 rounded-lg focus:outline-none focus:border-white/30 transition-colors text-white placeholder-gray-600"
                  placeholder="your.email@example.com"
                  disabled={isLoggingIn}
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-sm text-gray-500 mb-2 font-light">Password</label>
                <input
                  id="password"
                  type="password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  required
                  className="w-full px-4 py-3 bg-transparent border border-white/10 rounded-lg focus:outline-none focus:border-white/30 transition-colors text-white placeholder-gray-600"
                  placeholder="••••••••"
                  disabled={isLoggingIn}
                />
              </div>

              <button
                type="submit"
                disabled={isLoggingIn}
                className="w-full py-3 bg-white text-black rounded-lg font-light hover:bg-gray-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoggingIn ? 'Signing in...' : 'Sign In'}
              </button>

              {/* Continue as Guest */}
              <button
                type="button"
                onClick={() => {
                  setShowLogin(false);
                  setIsLoggedIn(false);
                  setGreetingText('Welcome');
                }}
                className="w-full py-3 border border-white/10 rounded-lg font-light hover:border-white/30 transition-all text-sm"
              >
                Continue as Guest
              </button>
            </form>

            {/* Demo Credentials */}
            <div className="mt-6 pt-6 border-t border-white/10">
              <p className="text-xs text-gray-500 text-center mb-3 font-light">Demo Credentials</p>
              <div className="space-y-2 text-xs">
                <div className="border border-white/10 rounded-lg p-3">
                  <p className="text-gray-500 mb-1 font-light">Customer Account</p>
                  <p className="font-mono text-gray-300">michael.johnson0@email.com</p>
                  <p className="font-mono text-gray-300">password123</p>
                </div>
                <div className="border border-white/10 rounded-lg p-3">
                  <p className="text-gray-500 mb-1 font-light">Admin Account</p>
                  <p className="font-mono text-gray-300">admin1@insurance.com</p>
                  <p className="font-mono text-gray-300">admin123</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-black text-white overflow-hidden">
      {/* Background gradient */}
      <div className="fixed inset-0 bg-gradient-radial from-purple-900/5 via-transparent to-transparent pointer-events-none" />
      
      {/* Top Right - User Info & Logout or Sign In */}
      <div className="fixed top-8 right-8 flex items-center gap-3 z-30">
        {isLoggedIn && user ? (
          <div className="relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="border border-white/10 rounded-full px-4 py-2 flex items-center gap-3 hover:border-white/20 transition-colors"
            >
              <div className="text-right">
                <p className="text-sm font-light">{user.full_name}</p>
                <p className="text-xs text-gray-500">{user.is_admin ? 'Admin' : 'Customer'}</p>
              </div>
              <div className="w-8 h-8 rounded-full border border-white/20 flex items-center justify-center text-xs font-light">
                {user.full_name.charAt(0)}
              </div>
            </button>

          {/* User Dropdown Menu */}
          {showUserMenu && (
            <div className="absolute top-full right-0 mt-2 w-96 bg-black border border-white/10 rounded-2xl shadow-2xl overflow-hidden animate-fade-in">
              {/* User Info Header */}
              <div className="p-6 border-b border-white/10">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-12 h-12 rounded-full border border-white/20 flex items-center justify-center text-lg font-light">
                    {user?.full_name.charAt(0)}
                  </div>
                  <div>
                    <p className="font-light">{user?.full_name}</p>
                    <p className="text-sm text-gray-500">{user?.email}</p>
                  </div>
                </div>
              </div>

              {/* Policies Section */}
              <div className="p-6 border-b border-white/10">
                <h3 className="text-sm font-light mb-3 text-gray-400">Your Policies</h3>
                {userPolicies.length === 0 ? (
                  <p className="text-xs text-gray-600">No policies found</p>
                ) : (
                  <div className="space-y-3">
                    {userPolicies.map((policy) => (
                      <div key={policy.id} className="bg-white/5 rounded-lg p-3 border border-white/10">
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <p className="text-sm font-light">{policy.policy_type.toUpperCase()} Insurance</p>
                            <p className="text-xs text-gray-500 font-mono">{policy.policy_number}</p>
                          </div>
                          <span className={`text-xs px-2 py-1 rounded-full ${
                            policy.status === 'active' 
                              ? 'bg-green-500/10 text-green-400 border border-green-500/20' 
                              : 'bg-gray-500/10 text-gray-400 border border-gray-500/20'
                          }`}>
                            {policy.status}
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs text-gray-400">
                          <div>
                            <span className="text-gray-600">Premium:</span> ${policy.premium_amount?.toFixed(2)}/mo
                          </div>
                          <div>
                            <span className="text-gray-600">Coverage:</span> ${policy.coverage_amount?.toLocaleString()}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Recent Tickets */}
              <div className="p-6 border-b border-white/10">
                <h3 className="text-sm font-light mb-3 text-gray-400">Recent Tickets</h3>
                {userTickets.length === 0 ? (
                  <p className="text-xs text-gray-600">No tickets</p>
                ) : (
                  <div className="space-y-2">
                    {userTickets.slice(0, 3).map((ticket) => (
                      <div key={ticket.id} className="flex items-start justify-between text-xs">
                        <div className="flex-1">
                          <p className="font-mono text-gray-500">{ticket.ticket_number}</p>
                          <p className="text-gray-400">{ticket.title}</p>
                        </div>
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          ticket.status === 'resolved' || ticket.status === 'closed'
                            ? 'bg-green-500/10 text-green-400'
                            : ticket.status === 'in_progress'
                            ? 'bg-blue-500/10 text-blue-400'
                            : 'bg-gray-500/10 text-gray-400'
                        }`}>
                          {ticket.status}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Logout Button */}
              <div className="p-4">
                <button
                  onClick={() => {
                    setIsLoggedIn(false);
                    setUser(null);
                    setAuthToken(null);
                    setShowLogin(true);
                    setChatMessages([]);
                    setTranscript('Waiting for input...');
                    setShowUserMenu(false);
                  }}
                  className="w-full py-2 border border-white/10 rounded-lg hover:border-white/30 transition-colors text-sm font-light flex items-center justify-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  Sign Out
                </button>
              </div>
            </div>
          )}
          </div>
        ) : (
          <button
            onClick={() => setShowLogin(true)}
            className="border border-white/10 rounded-full px-4 py-2 hover:border-white/30 transition-colors flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
            </svg>
            <span className="text-sm font-light">Sign In</span>
          </button>
        )}
      </div>
      
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
        
        {/* Emotion Detection Badge */}
        {detectedEmotion !== 'neutral' && (
          <div className="mb-3 flex items-center justify-center gap-2">
            <span className="text-[10px] text-gray-500 uppercase tracking-widest font-medium">Emotion:</span>
            <span className="px-3 py-1 bg-white/5 border border-white/10 rounded-lg text-[11px] font-light uppercase tracking-wide text-gray-300">
              {detectedEmotion}
            </span>
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
      <div className="fixed bottom-8 left-0 right-0 px-8 h-[80px] flex items-center justify-center z-20">
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
