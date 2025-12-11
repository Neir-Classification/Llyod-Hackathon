/**
 * useDualPipeline - React hook for dual-pipeline RAG with instant acknowledgments
 * 
 * This hook manages the dual-pipeline architecture:
 * 1. Fast Pipeline: Instant acknowledgment responses (<100ms)
 * 2. Deep Pipeline: Full RAG responses with accurate information
 * 
 * Features:
 * - WebSocket support for real-time streaming
 * - Automatic fallback to HTTP if WebSocket fails
 * - Audio caching for instant playback
 * - Seamless transition from quick to full response
 */

import { useCallback, useEffect, useRef, useState } from 'react';

interface Citation {
  policy_name: string;
  page_number: number | string;
  content: string;
  score?: number;
}

interface DualPipelineState {
  isConnected: boolean;
  isProcessing: boolean;
  quickResponse: string | null;
  fullResponse: string | null;
  citations: Citation[];
  intent: string | null;
  error: string | null;
}

interface DualPipelineOptions {
  tone?: string;
  voice?: string;
  k?: number;
  useWebSocket?: boolean;
  onQuickResponse?: (text: string, audio: Blob | null) => void;
  onFullResponse?: (text: string, audio: Blob | null, citations: Citation[]) => void;
  onError?: (error: string) => void;
}

// Convert base64 to Blob
function base64ToBlob(base64: string, mimeType: string = 'audio/mpeg'): Blob {
  const byteCharacters = atob(base64);
  const byteNumbers = new Array(byteCharacters.length);
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  const byteArray = new Uint8Array(byteNumbers);
  return new Blob([byteArray], { type: mimeType });
}

export function useDualPipeline(options: DualPipelineOptions = {}) {
  const {
    tone = 'neutral',
    voice = 'alloy',
    k = 2,
    useWebSocket = true,
    onQuickResponse,
    onFullResponse,
    onError,
  } = options;

  const [state, setState] = useState<DualPipelineState>({
    isConnected: false,
    isProcessing: false,
    quickResponse: null,
    fullResponse: null,
    citations: [],
    intent: null,
    error: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const conversationHistoryRef = useRef<Array<{ role: string; content: string }>>([]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/dual-pipeline`;
    
    console.log('🔌 [WS] Connecting to:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('✅ [WS] Connected');
      setState(prev => ({ ...prev, isConnected: true, error: null }));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('📨 [WS] Received:', data.type);

        if (data.type === 'quick') {
          const audioBlob = data.audio_base64 ? base64ToBlob(data.audio_base64) : null;
          setState(prev => ({
            ...prev,
            quickResponse: data.text,
            intent: data.intent,
          }));
          onQuickResponse?.(data.text, audioBlob);
        } else if (data.type === 'full') {
          const audioBlob = data.audio_base64 ? base64ToBlob(data.audio_base64) : null;
          setState(prev => ({
            ...prev,
            fullResponse: data.text,
            citations: data.citations || [],
            isProcessing: false,
          }));
          onFullResponse?.(data.text, audioBlob, data.citations || []);
        } else if (data.type === 'error') {
          setState(prev => ({ ...prev, error: data.message, isProcessing: false }));
          onError?.(data.message);
        } else if (data.type === 'pong') {
          console.log('🏓 [WS] Pong received');
        }
      } catch (err) {
        console.error('❌ [WS] Failed to parse message:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('❌ [WS] Error:', error);
      setState(prev => ({ ...prev, error: 'WebSocket error', isConnected: false }));
    };

    ws.onclose = () => {
      console.log('🔌 [WS] Disconnected');
      setState(prev => ({ ...prev, isConnected: false }));
      wsRef.current = null;
      
      // Attempt reconnection after 3 seconds
      setTimeout(() => {
        if (useWebSocket) {
          console.log('🔄 [WS] Attempting reconnection...');
          connect();
        }
      }, 3000);
    };

    wsRef.current = ws;
  }, [useWebSocket, onQuickResponse, onFullResponse, onError]);

  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  // Send query via WebSocket
  const sendQueryWS = useCallback(async (query: string): Promise<boolean> => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('⚠️ [WS] Not connected, falling back to HTTP');
      return false;
    }

    setState(prev => ({
      ...prev,
      isProcessing: true,
      quickResponse: null,
      fullResponse: null,
      citations: [],
      error: null,
    }));

    wsRef.current.send(JSON.stringify({
      type: 'query',
      query,
      tone,
      voice,
      k,
      conversation_history: conversationHistoryRef.current,
    }));

    return true;
  }, [tone, voice, k]);

  // Send query via HTTP (fallback)
  const sendQueryHTTP = useCallback(async (query: string) => {
    console.log('📤 [HTTP] Sending dual-pipeline query:', query);

    setState(prev => ({
      ...prev,
      isProcessing: true,
      quickResponse: null,
      fullResponse: null,
      citations: [],
      error: null,
    }));

    try {
      // Step 1: Get quick response immediately
      const quickFormData = new FormData();
      quickFormData.append('query', query);
      quickFormData.append('tone', tone);
      quickFormData.append('voice', voice);

      const quickPromise = fetch('/quick-response-audio', {
        method: 'POST',
        body: quickFormData,
      });

      // Step 2: Start full response in parallel
      const fullPromise = (async () => {
        const fullRes = await fetch('/rag-query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query,
            tone,
            k,
            conversation_history: conversationHistoryRef.current,
          }),
        });

        if (!fullRes.ok) throw new Error('RAG query failed');
        const ragData = await fullRes.json();

        // Generate TTS for full response
        const ttsRes = await fetch('/text-to-speech', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: ragData.response, voice, audio_format: 'mp3' }),
        });

        if (!ttsRes.ok) throw new Error('TTS failed');
        const audioBlob = await ttsRes.blob();

        return { response: ragData.response, citations: ragData.citations || [], audioBlob };
      })();

      // Handle quick response
      const quickRes = await quickPromise;
      if (quickRes.ok) {
        const quickBlob = await quickRes.blob();
        const quickText = quickRes.headers.get('X-Quick-Response-Text') || 'Processing...';
        const intent = quickRes.headers.get('X-Intent') || 'unknown';

        setState(prev => ({ ...prev, quickResponse: quickText, intent }));
        onQuickResponse?.(quickText, quickBlob);
      }

      // Handle full response
      const { response: fullText, citations, audioBlob } = await fullPromise;
      setState(prev => ({
        ...prev,
        fullResponse: fullText,
        citations,
        isProcessing: false,
      }));
      onFullResponse?.(fullText, audioBlob, citations);

    } catch (err: any) {
      console.error('❌ [HTTP] Dual pipeline error:', err);
      setState(prev => ({ ...prev, error: err.message, isProcessing: false }));
      onError?.(err.message);
    }
  }, [tone, voice, k, onQuickResponse, onFullResponse, onError]);

  // Main send function - tries WebSocket first, falls back to HTTP
  const sendQuery = useCallback(async (query: string) => {
    if (useWebSocket && wsRef.current?.readyState === WebSocket.OPEN) {
      const sent = await sendQueryWS(query);
      if (sent) return;
    }
    
    // Fallback to HTTP
    await sendQueryHTTP(query);
  }, [useWebSocket, sendQueryWS, sendQueryHTTP]);

  // Add message to conversation history
  const addToHistory = useCallback((role: 'user' | 'assistant', content: string) => {
    conversationHistoryRef.current.push({ role, content });
  }, []);

  // Clear conversation history
  const clearHistory = useCallback(() => {
    conversationHistoryRef.current = [];
  }, []);

  // Initialize WebSocket on mount
  useEffect(() => {
    if (useWebSocket) {
      connect();
    }
    return () => disconnect();
  }, [useWebSocket, connect, disconnect]);

  // Ping to keep connection alive
  useEffect(() => {
    if (!useWebSocket) return;

    const interval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [useWebSocket]);

  return {
    ...state,
    sendQuery,
    addToHistory,
    clearHistory,
    connect,
    disconnect,
  };
}

export default useDualPipeline;
