import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel

# RAG imports
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.documents import Document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(title="Speech-Text Bridge", version="0.1.0")
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Load environment variables from a local .env file if present (for local dev convenience).
load_dotenv(BASE_DIR / ".env")

# RAG Configuration
PRAJAS_NIER_DIR = BASE_DIR / "Prajas-Nier"
DATASET_DIR = PRAJAS_NIER_DIR / "Dataset"
PDF_PATHS = [DATASET_DIR / "policy-booklet.pdf", DATASET_DIR / "policy-limits.pdf"]
FAISS_DIR = PRAJAS_NIER_DIR / "artifacts" / "faiss_index"

# ============================================================================
# EMPATHY ENGINE: Sentiment-Adaptive Response System
# ============================================================================
# The Empathy Engine detects user emotional state through:
# 1. Acoustic features (speech rate, pitch variation)
# 2. Keyword/phrase detection
# 3. Transcript sentiment analysis
# It then adapts BOTH the response strategy AND voice delivery.
# ============================================================================

TONE_PROMPTS = {
    "angry": "You're a helpful agent who gets straight to the point. The user is frustrated - don't be overly apologetic or robotic. Just acknowledge briefly and solve their problem fast. Sound human, not scripted. 2 sentences max.",
    "confused": "Explain it simply like you're talking to a friend. No corporate speak. 2 sentences, plain English.",
    "neutral": "Be helpful and direct. Answer the question clearly. 2 sentences.",
    "happy": "Be friendly and helpful. Match their positive energy briefly. 2 sentences.",
    "anxious": "Be reassuring but not patronizing. Give them the key info they need to feel better. 2 sentences.",
    "panicked": "EMERGENCY MODE: Give ONE clear safety instruction. Be calm but urgent. No fluff. 1-2 sentences only.",
    "distressed": "Be warm and human. Acknowledge what they're going through briefly, then help. 2 sentences."
}

# Emergency keywords that trigger immediate triage mode
EMERGENCY_KEYWORDS = [
    "emergency", "urgent", "help", "fire", "flood", "water everywhere", 
    "accident", "crash", "injured", "hurt", "hospital", "ambulance",
    "broken into", "burglary", "theft", "stolen", "break in",
    "flooding", "pipe burst", "gas leak", "smoke", "burning",
    "trapped", "stuck", "can't get out", "danger"
]

# Emergency triage responses for common scenarios
EMERGENCY_TRIAGE = {
    "water": {
        "keywords": ["water", "flood", "flooding", "pipe", "burst", "leak", "plumber"],
        "immediate_action": "Turn off your main water valve now - it's usually near the water meter.",
        "followup": "Once that's done, move valuables away from the water and don't touch electrical outlets."
    },
    "fire": {
        "keywords": ["fire", "smoke", "burning", "flames"],
        "immediate_action": "Get everyone out now and call 999.",
        "followup": "Don't go back inside. We'll sort the claim once you're safe."
    },
    "breakin": {
        "keywords": ["broken into", "burglary", "burglar", "thief", "stolen", "break in", "intruder"],
        "immediate_action": "If you're not sure it's safe, get out and call 999.",
        "followup": "Don't touch anything - police need to see it. Then we'll start your claim."
    },
    "accident": {
        "keywords": ["accident", "crash", "collision", "hit", "injured", "hurt"],
        "immediate_action": "Anyone hurt? Call 999 if needed. Get to safety first.",
        "followup": "Once safe, get the other driver's details and take photos."
    }
}

# TTS voice settings adapted by emotional state
# More realistic speeds - not too slow for any emotion
ADAPTIVE_TTS_SETTINGS = {
    "neutral": {"speed": 1.0, "voice": "alloy"},
    "happy": {"speed": 1.05, "voice": "shimmer"},
    "confused": {"speed": 0.95, "voice": "alloy"},      # Slightly slower, clear
    "anxious": {"speed": 0.95, "voice": "nova"},        # Warm, steady
    "angry": {"speed": 1.0, "voice": "onyx"},           # Normal speed, calm deep voice - NOT slow
    "panicked": {"speed": 0.9, "voice": "onyx"},        # Slightly slower, grounding
    "distressed": {"speed": 0.95, "voice": "nova"}      # Warm, natural pace
}

# Global vector store (cached)
_vector_store = None


def get_vector_store():
    """Get or initialize the FAISS vector store."""
    global _vector_store
    if _vector_store is not None:
        return _vector_store
    
    if FAISS_DIR.exists():
        try:
            embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
            _vector_store = FAISS.load_local(str(FAISS_DIR), embeddings, allow_dangerous_deserialization=True)
            return _vector_store
        except Exception as e:
            logger.warning(f"Failed to load existing FAISS index: {e}. Rebuilding...")
    
    # Build new index if not found
    return build_vector_store()


def load_pdfs(pdf_paths):
    """Load PDFs and add metadata."""
    docs = []
    for path in pdf_paths:
        if not path.exists():
            logger.warning(f"PDF not found: {path}")
            continue
        loader = PyPDFLoader(str(path))
        loaded_docs = loader.load()
        policy_name = path.name
        for doc in loaded_docs:
            doc.metadata["policy_name"] = policy_name
            if "page" in doc.metadata:
                doc.metadata["page_number"] = doc.metadata["page"]
        docs.extend(loaded_docs)
    return docs


def chunk_docs(docs, chunk_size=500, chunk_overlap=100):
    """Split documents into chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_documents(docs)
    for chunk in chunks:
        if "policy_name" not in chunk.metadata:
            chunk.metadata["policy_name"] = chunk.metadata.get("source", "unknown")
        if "page_number" not in chunk.metadata and "page" in chunk.metadata:
            chunk.metadata["page_number"] = chunk.metadata["page"]
    return chunks


def build_vector_store():
    """Build a new FAISS vector store from PDFs."""
    global _vector_store
    logger.info("Building FAISS index from PDFs...")
    docs = load_pdfs(PDF_PATHS)
    if not docs:
        raise RuntimeError("No PDFs found to index")
    chunks = chunk_docs(docs)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    _vector_store = FAISS.from_documents(chunks, embeddings)
    FAISS_DIR.mkdir(parents=True, exist_ok=True)
    _vector_store.save_local(str(FAISS_DIR))
    logger.info(f"FAISS index built and saved to {FAISS_DIR}")
    return _vector_store


def retrieve(query: str, vector_db: FAISS, k: int = 2):
    """Retrieve relevant chunks from the vector store."""
    enhanced_query = f"policy coverage clause: {query}"
    docs = vector_db.max_marginal_relevance_search(enhanced_query, k=k, fetch_k=20)
    
    # Limit chunk length for voice output
    for doc in docs:
        doc.page_content = doc.page_content[:600]
    
    return [(doc, 0.0) for doc in docs]


def adjust_tone_with_llm(
    retrieved_chunks, 
    user_question: str, 
    tone: str = "neutral",
    emergency_type: Optional[str] = None
) -> str:
    """Use LLM to generate a tone-appropriate response from retrieved chunks.
    
    For emergency/panicked tones, switches to Emergency Triage mode with
    immediate safety-focused responses.
    """
    if tone not in TONE_PROMPTS:
        tone = "neutral"
    
    # Combine retrieved chunks into context (limit size)
    context = "\n".join([doc.page_content[:300] for doc, _ in retrieved_chunks[:2]])
    
    # EMERGENCY TRIAGE MODE: Override normal flow for emergencies
    if tone == "panicked" and emergency_type and emergency_type in EMERGENCY_TRIAGE:
        triage_info = EMERGENCY_TRIAGE[emergency_type]
        system_prompt = f"""{TONE_PROMPTS[tone]}

EMERGENCY: {emergency_type.upper()}
ACTION: {triage_info['immediate_action']}

Reply with the safety action ONLY. No policy info. 2 sentences max."""
    elif tone == "panicked":
        system_prompt = f"""{TONE_PROMPTS[tone]}

User is distressed. Give ONE calming action. 2 sentences max. No policy details."""
    else:
        # Normal tone-adjusted response - enforce brevity
        system_prompt = f"""{TONE_PROMPTS[tone]}

Answer the question using ONLY relevant policy info below. Be CONCISE - 2-3 sentences max for voice output.

Policy Context:
{context}

IMPORTANT: Only include information that DIRECTLY answers the question. No extra details."""

    user_prompt = f"Question: {user_question}"
    
    # Adjust temperature based on tone - more deterministic for emergencies
    temperature = 0.2 if tone in ["panicked", "angry"] else 0.3
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=temperature)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    response = llm.invoke(messages)
    return response.content


def get_openai_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set the OPENAI_API_KEY environment variable.")
    return OpenAI(api_key=api_key)


def detect_emergency_type(text: str) -> Optional[str]:
    """Detect if text contains emergency keywords and return the emergency type."""
    text_lower = text.lower()
    for emergency_type, config in EMERGENCY_TRIAGE.items():
        if any(keyword in text_lower for keyword in config["keywords"]):
            return emergency_type
    return None


def analyze_sentiment(
    transcript: str,
    speech_rate: Optional[float] = None,  # Words per minute
    pitch_variance: Optional[float] = None,  # 0-1 normalized
    volume_level: Optional[float] = None,  # 0-1 normalized
) -> dict:
    """
    Empathy Engine: Analyze user's emotional state from multiple signals.
    
    Returns:
        {
            "detected_emotion": str,
            "confidence": float,
            "is_emergency": bool,
            "emergency_type": Optional[str],
            "recommended_tone": str,
            "tts_settings": dict,
            "signals": dict  # For transparency/debugging
        }
    """
    text_lower = transcript.lower()
    signals = {
        "keyword_signals": [],
        "acoustic_signals": [],
        "sentiment_indicators": []
    }
    
    # 1. Check for emergency keywords first (highest priority)
    is_emergency = any(kw in text_lower for kw in EMERGENCY_KEYWORDS)
    emergency_type = detect_emergency_type(transcript)
    
    if is_emergency:
        signals["keyword_signals"].append("emergency_keyword_detected")
    
    # 2. Analyze acoustic features if provided
    acoustic_score = 0  # -1 (calm) to +1 (distressed)
    
    if speech_rate is not None:
        # Normal: 120-150 WPM, Panicked: >180 WPM, Slow/sad: <100 WPM
        if speech_rate > 180:
            acoustic_score += 0.4
            signals["acoustic_signals"].append(f"fast_speech_rate:{speech_rate:.0f}wpm")
        elif speech_rate > 160:
            acoustic_score += 0.2
            signals["acoustic_signals"].append(f"elevated_speech_rate:{speech_rate:.0f}wpm")
        elif speech_rate < 100:
            acoustic_score -= 0.2
            signals["acoustic_signals"].append(f"slow_speech_rate:{speech_rate:.0f}wpm")
    
    if pitch_variance is not None:
        # High variance = emotional, low variance = monotone/sad
        if pitch_variance > 0.7:
            acoustic_score += 0.3
            signals["acoustic_signals"].append(f"high_pitch_variance:{pitch_variance:.2f}")
        elif pitch_variance < 0.2:
            signals["acoustic_signals"].append(f"monotone:{pitch_variance:.2f}")
    
    if volume_level is not None:
        if volume_level > 0.8:
            acoustic_score += 0.2
            signals["acoustic_signals"].append(f"loud_volume:{volume_level:.2f}")
    
    # 3. Keyword-based sentiment analysis
    panic_words = ["help", "please", "urgent", "now", "hurry", "emergency", "asap"]
    anger_words = ["ridiculous", "unacceptable", "terrible", "worst", "angry", "furious", "useless", "incompetent"]
    confusion_words = ["confused", "don't understand", "what does", "unclear", "lost", "how do i", "explain"]
    anxiety_words = ["worried", "scared", "afraid", "nervous", "stress", "anxious", "concern"]
    positive_words = ["thank", "great", "appreciate", "helpful", "good", "excellent", "wonderful"]
    
    panic_count = sum(1 for w in panic_words if w in text_lower)
    anger_count = sum(1 for w in anger_words if w in text_lower)
    confusion_count = sum(1 for w in confusion_words if w in text_lower)
    anxiety_count = sum(1 for w in anxiety_words if w in text_lower)
    positive_count = sum(1 for w in positive_words if w in text_lower)
    
    # 4. Determine emotional state
    detected_emotion = "neutral"
    confidence = 0.5
    
    # Emergency overrides everything
    if is_emergency and (acoustic_score > 0.3 or panic_count >= 2):
        detected_emotion = "panicked"
        confidence = 0.9
        signals["sentiment_indicators"].append("emergency_with_distress_signals")
    elif is_emergency:
        detected_emotion = "anxious"
        confidence = 0.8
        signals["sentiment_indicators"].append("emergency_keywords_present")
    elif anger_count >= 2 or (anger_count >= 1 and acoustic_score > 0.2):
        detected_emotion = "angry"
        confidence = 0.7 + (anger_count * 0.1)
        signals["sentiment_indicators"].append(f"anger_indicators:{anger_count}")
    elif panic_count >= 2 or acoustic_score > 0.5:
        detected_emotion = "panicked"
        confidence = 0.8
        signals["sentiment_indicators"].append("high_distress_signals")
    elif anxiety_count >= 1 or (acoustic_score > 0.2 and acoustic_score <= 0.5):
        detected_emotion = "anxious"
        confidence = 0.6 + (anxiety_count * 0.1)
        signals["sentiment_indicators"].append(f"anxiety_indicators:{anxiety_count}")
    elif confusion_count >= 1:
        detected_emotion = "confused"
        confidence = 0.6 + (confusion_count * 0.1)
        signals["sentiment_indicators"].append(f"confusion_indicators:{confusion_count}")
    elif positive_count >= 2:
        detected_emotion = "happy"
        confidence = 0.7
        signals["sentiment_indicators"].append(f"positive_indicators:{positive_count}")
    
    # Get recommended TTS settings
    tts_settings = ADAPTIVE_TTS_SETTINGS.get(detected_emotion, ADAPTIVE_TTS_SETTINGS["neutral"])
    
    return {
        "detected_emotion": detected_emotion,
        "confidence": min(confidence, 1.0),
        "is_emergency": is_emergency,
        "emergency_type": emergency_type,
        "recommended_tone": detected_emotion,
        "tts_settings": tts_settings,
        "signals": signals
    }


class SpeechRequest(BaseModel):
    text: str
    voice: Optional[str] = "alloy"
    audio_format: Optional[str] = "mp3"


class RAGQueryRequest(BaseModel):
    query: str
    tone: Optional[str] = "neutral"
    k: Optional[int] = 2


class SentimentAnalysisRequest(BaseModel):
    transcript: str
    speech_rate: Optional[float] = None  # Words per minute
    pitch_variance: Optional[float] = None  # 0-1 normalized
    volume_level: Optional[float] = None  # 0-1 normalized


class AdaptiveTTSRequest(BaseModel):
    text: str
    emotion: Optional[str] = "neutral"
    voice: Optional[str] = None  # Will be auto-selected based on emotion if not provided
    speed: Optional[float] = None  # Will be auto-selected based on emotion if not provided
    audio_format: Optional[str] = "mp3"


class EmpathyRAGRequest(BaseModel):
    """Full Empathy Engine request with sentiment analysis + RAG."""
    query: str
    speech_rate: Optional[float] = None
    pitch_variance: Optional[float] = None
    volume_level: Optional[float] = None
    k: Optional[int] = 2


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/speech-to-text")
async def speech_to_text(audio_file: UploadFile = File(...), language: Optional[str] = None) -> JSONResponse:
    client = get_openai_client()

    audio_bytes = await audio_file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio payload")

    try:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=(audio_file.filename or "audio.wav", audio_bytes, audio_file.content_type or "audio/wav"),
            language=language,
        )
        logger.info(f"[SPEECH-TO-TEXT] Transcribed: '{transcript.text}'")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}") from exc

    return JSONResponse({"text": transcript.text})


@app.post("/speech-to-text-chunk")
async def speech_to_text_chunk(
    audio_chunk: UploadFile = File(...),
    language: Optional[str] = None,
    mime_type: Optional[str] = Form(None),
) -> JSONResponse:
    client = get_openai_client()

    chunk_bytes = await audio_chunk.read()
    if not chunk_bytes:
        raise HTTPException(status_code=400, detail="Empty audio payload")

    supported = {
        "audio/webm": "webm",
        "audio/ogg": "ogg",
        "audio/mp3": "mp3",
        "audio/mpeg": "mp3",
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/mp4": "mp4",
        "audio/m4a": "m4a",
        "video/webm": "webm",
    }

    def pick_mime() -> str:
        for candidate in [mime_type, audio_chunk.content_type, "audio/webm"]:
            if not candidate:
                continue
            base = candidate.split(";")[0].strip().lower()
            if base in supported:
                return base
        return "audio/webm"

    mime = pick_mime()
    ext = supported[mime]

    filename = audio_chunk.filename or f"chunk.{ext}"
    content_type = mime

    logger.info(f"[chunk] filename={filename}, content_type={content_type}, size={len(chunk_bytes)}, provided_mime_type={mime_type}, upload_content_type={audio_chunk.content_type}")

    try:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, chunk_bytes, content_type),
            language=language,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Transcription failed")
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}") from exc

    return JSONResponse({"text": transcript.text})


@app.post("/text-to-speech")
async def text_to_speech(body: SpeechRequest) -> StreamingResponse:
    client = get_openai_client()

    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    response_format = body.audio_format or "mp3"

    try:
        stream = client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice=body.voice or "alloy",
            input=body.text,
            response_format=response_format,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"TTS failed: {exc}") from exc

    def iter_audio():
        # Stream audio bytes so large responses do not exhaust memory.
        with stream as response:
            for chunk in response.iter_bytes():
                yield chunk

    media_type = "audio/mpeg" if response_format == "mp3" else f"audio/{response_format}"
    headers = {"Content-Disposition": "inline; filename=tts-output." + response_format}
    return StreamingResponse(iter_audio(), media_type=media_type, headers=headers)


# ============================================================================
# EMPATHY ENGINE API ENDPOINTS
# ============================================================================

@app.post("/analyze-sentiment")
async def analyze_sentiment_endpoint(body: SentimentAnalysisRequest) -> JSONResponse:
    """
    Analyze user's emotional state from transcript and acoustic features.
    
    This is the core of the Empathy Engine - it detects:
    - Emergency situations requiring immediate triage
    - Emotional states (panicked, angry, anxious, confused, neutral, happy)
    - Recommends tone adjustments and TTS settings
    """
    try:
        result = analyze_sentiment(
            transcript=body.transcript,
            speech_rate=body.speech_rate,
            pitch_variance=body.pitch_variance,
            volume_level=body.volume_level
        )
        
        logger.info(f"[EMPATHY ENGINE] Detected emotion: {result['detected_emotion']} "
                   f"(confidence: {result['confidence']:.2f}) "
                   f"Emergency: {result['is_emergency']}")
        
        return JSONResponse(result)
    except Exception as exc:
        logger.exception("Sentiment analysis failed")
        raise HTTPException(status_code=500, detail=f"Sentiment analysis failed: {exc}") from exc


@app.post("/adaptive-tts")
async def adaptive_text_to_speech(body: AdaptiveTTSRequest) -> StreamingResponse:
    """
    Generate speech with emotion-adaptive voice settings.
    
    Automatically adjusts:
    - Voice selection (deeper voice for calming angry users, warmer for distressed)
    - Speech speed (slower for panicked users, normal for neutral)
    """
    client = get_openai_client()
    
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    # Get adaptive settings for the detected emotion
    emotion = body.emotion or "neutral"
    tts_settings = ADAPTIVE_TTS_SETTINGS.get(emotion, ADAPTIVE_TTS_SETTINGS["neutral"])
    
    # Allow overrides
    voice = body.voice or tts_settings["voice"]
    speed = body.speed or tts_settings["speed"]
    response_format = body.audio_format or "mp3"
    
    logger.info(f"[ADAPTIVE TTS] Emotion: {emotion}, Voice: {voice}, Speed: {speed}")
    
    # Build TTS instruction for emotion-appropriate delivery
    emotion_instructions = {
        "neutral": "",
        "happy": "Speak in a warm, friendly, and upbeat manner.",
        "confused": "Speak slowly and clearly, with patience in your tone.",
        "anxious": "Speak in a calm, reassuring, and gentle manner. Be soothing.",
        "angry": "Speak in a calm, measured, and understanding tone. Do not be defensive.",
        "panicked": "Speak VERY slowly and calmly. Use a grounding, steady voice. Pause between sentences. Be the calm in the storm.",
        "distressed": "Speak with warmth and compassion. Be gentle and supportive."
    }
    
    instruction = emotion_instructions.get(emotion, "")
    
    try:
        # Note: The standard TTS API doesn't support instructions parameter.
        # Emotional delivery is achieved through:
        # 1. Voice selection (onyx = deeper/calmer, nova = warmer)
        # 2. Speed adjustment (slower for calming)
        # 3. The text content itself (written to convey the right tone)
        stream = client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice=voice,
            input=body.text,
            response_format=response_format,
            speed=speed,
        )
    except Exception as exc:
        logger.exception("Adaptive TTS failed")
        raise HTTPException(status_code=502, detail=f"Adaptive TTS failed: {exc}") from exc
    
    def iter_audio():
        with stream as response:
            for chunk in response.iter_bytes():
                yield chunk
    
    media_type = "audio/mpeg" if response_format == "mp3" else f"audio/{response_format}"
    headers = {
        "Content-Disposition": f"inline; filename=empathy-tts.{response_format}",
        "X-Emotion-Detected": emotion,
        "X-Voice-Used": voice,
        "X-Speed-Used": str(speed)
    }
    return StreamingResponse(iter_audio(), media_type=media_type, headers=headers)


@app.post("/empathy-rag-query")
async def empathy_rag_query(body: EmpathyRAGRequest) -> JSONResponse:
    """
    Full Empathy Engine pipeline:
    1. Analyze sentiment from query + acoustic features
    2. Detect if emergency triage is needed
    3. Retrieve relevant policy information (if appropriate)
    4. Generate emotion-appropriate response
    
    Returns response with sentiment analysis, adaptive TTS settings, and citations.
    """
    try:
        if not body.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Step 1: Analyze sentiment
        sentiment_result = analyze_sentiment(
            transcript=body.query,
            speech_rate=body.speech_rate,
            pitch_variance=body.pitch_variance,
            volume_level=body.volume_level
        )
        
        detected_emotion = sentiment_result["detected_emotion"]
        is_emergency = sentiment_result["is_emergency"]
        emergency_type = sentiment_result["emergency_type"]
        tts_settings = sentiment_result["tts_settings"]
        
        logger.info(f"[EMPATHY RAG] Query: '{body.query[:50]}...' | "
                   f"Emotion: {detected_emotion} | Emergency: {is_emergency}")
        
        # Step 2: Get vector store and retrieve
        vector_db = get_vector_store()
        
        # For emergencies, retrieve less (focus on immediate help)
        k = 1 if is_emergency and detected_emotion == "panicked" else body.k
        results = retrieve(body.query, vector_db, k=k)
        
        # Step 3: Generate tone-adjusted response
        response_text = adjust_tone_with_llm(
            results, 
            body.query, 
            tone=detected_emotion,
            emergency_type=emergency_type
        )
        
        # Step 4: Build citations
        citations = []
        for idx, (doc, score) in enumerate(results, start=1):
            policy_name = doc.metadata.get("policy_name", "Unknown Document")
            page_number = doc.metadata.get("page_number", doc.metadata.get("page", "N/A"))
            source_path = doc.metadata.get("source", "")
            source_file = Path(source_path).name if source_path else policy_name
            
            excerpt = doc.page_content.strip()[:300]
            if len(doc.page_content.strip()) > 300:
                excerpt += "..."
            
            citations.append({
                "id": idx,
                "source": source_file,
                "policy_name": policy_name,
                "page": page_number + 1 if isinstance(page_number, int) else page_number,
                "excerpt": excerpt,
                "relevance_rank": idx
            })
        
        logger.info(f"[EMPATHY RAG] Response generated with {len(citations)} citations")
        
        return JSONResponse({
            "response": response_text,
            "query": body.query,
            "citations": citations,
            "sources_used": len(citations),
            # Empathy Engine specific fields
            "empathy_analysis": {
                "detected_emotion": detected_emotion,
                "confidence": sentiment_result["confidence"],
                "is_emergency": is_emergency,
                "emergency_type": emergency_type,
                "mode": "emergency_triage" if is_emergency and detected_emotion == "panicked" else "standard",
                "signals": sentiment_result["signals"]
            },
            "tts_settings": tts_settings
        })
    except Exception as exc:
        logger.exception("Empathy RAG query failed")
        raise HTTPException(status_code=502, detail=f"Empathy RAG query failed: {exc}") from exc


@app.get("/")
async def root():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)

    return {
        "message": "Speech/Text service ready",
        "routes": ["GET /health", "POST /speech-to-text", "POST /text-to-speech"],
    }


@app.post("/rag-query")
async def rag_query(body: RAGQueryRequest) -> JSONResponse:
    """Query the RAG pipeline and return a tone-adjusted response with citations."""
    try:
        if not body.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        logger.info(f"[RAG QUERY INPUT] Query: '{body.query}' | Tone: '{body.tone}' | K: {body.k}")
        
        # Get or build the vector store
        vector_db = get_vector_store()
        
        # Retrieve relevant chunks
        results = retrieve(body.query, vector_db, k=body.k)
        
        # Generate tone-adjusted response
        response_text = adjust_tone_with_llm(results, body.query, body.tone)
        
        # Build citations for explainability
        citations = []
        for idx, (doc, score) in enumerate(results, start=1):
            policy_name = doc.metadata.get("policy_name", "Unknown Document")
            page_number = doc.metadata.get("page_number", doc.metadata.get("page", "N/A"))
            # Get source file name
            source_path = doc.metadata.get("source", "")
            source_file = Path(source_path).name if source_path else policy_name
            
            # Create a clean excerpt (first 300 chars)
            excerpt = doc.page_content.strip()[:300]
            if len(doc.page_content.strip()) > 300:
                excerpt += "..."
            
            citations.append({
                "id": idx,
                "source": source_file,
                "policy_name": policy_name,
                "page": page_number + 1 if isinstance(page_number, int) else page_number,
                "excerpt": excerpt,
                "relevance_rank": idx
            })
        
        logger.info(f"[RAG QUERY OUTPUT] Response: '{response_text}' | Citations: {len(citations)}")
        
        return JSONResponse({
            "response": response_text,
            "tone": body.tone,
            "query": body.query,
            "citations": citations,
            "sources_used": len(citations)
        })
    except Exception as exc:
        logger.exception("RAG query failed")
        raise HTTPException(status_code=502, detail=f"RAG query failed: {exc}") from exc


@app.post("/rag-audio-query")
async def rag_audio_query(
    audio_file: UploadFile = File(...),
    tone: Optional[str] = Form("neutral"),
    k: Optional[int] = Form(2),
    voice: Optional[str] = Form("alloy"),
    language: Optional[str] = Form(None),
) -> StreamingResponse:
    """
    Complete audio-to-audio RAG pipeline:
    1. Speech-to-text: Convert audio input to text
    2. RAG: Query the knowledge base
    3. Text-to-speech: Convert response back to audio
    """
    client = get_openai_client()
    
    # Step 1: Speech-to-Text
    audio_bytes = await audio_file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio payload")
    
    try:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=(audio_file.filename or "audio.wav", audio_bytes, audio_file.content_type or "audio/wav"),
            language=language,
        )
        user_query = transcript.text
        logger.info(f"[RAG-AUDIO] Transcribed query: '{user_query}'")
    except Exception as exc:
        logger.exception("Transcription failed in RAG audio query")
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}") from exc
    
    # Step 2: RAG Query
    try:
        if not user_query.strip():
            raise HTTPException(status_code=400, detail="Transcribed query is empty")
        
        vector_db = get_vector_store()
        results = retrieve(user_query, vector_db, k=k)
        response_text = adjust_tone_with_llm(results, user_query, tone)
        
        logger.info(f"[RAG-AUDIO] Generated response: '{response_text}'")
    except Exception as exc:
        logger.exception("RAG query failed in audio pipeline")
        raise HTTPException(status_code=502, detail=f"RAG query failed: {exc}") from exc
    
    # Step 3: Text-to-Speech
    try:
        stream = client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice=voice or "alloy",
            input=response_text,
            response_format="mp3",
        )
    except Exception as exc:
        logger.exception("TTS failed in RAG audio query")
        raise HTTPException(status_code=502, detail=f"TTS failed: {exc}") from exc
    
    def iter_audio():
        with stream as response:
            for chunk in response.iter_bytes():
                yield chunk
    
    headers = {
        "Content-Disposition": "inline; filename=rag-response.mp3",
        "X-Transcribed-Query": user_query,
        "X-Response-Text": response_text[:200]  # Truncated for header size limits
    }
    return StreamingResponse(iter_audio(), media_type="audio/mpeg", headers=headers)


@app.post("/rag-audio-query-chunk")
async def rag_audio_query_chunk(
    audio_chunk: UploadFile = File(...),
    tone: Optional[str] = Form("neutral"),
    k: Optional[int] = Form(2),
    voice: Optional[str] = Form("alloy"),
    language: Optional[str] = Form(None),
    mime_type: Optional[str] = Form(None),
) -> StreamingResponse:
    """
    Audio chunk-based RAG pipeline (for streaming/real-time scenarios):
    1. Speech-to-text: Convert audio chunk to text
    2. RAG: Query the knowledge base
    3. Text-to-speech: Convert response back to audio
    """
    client = get_openai_client()
    
    # Step 1: Speech-to-Text (Chunk)
    chunk_bytes = await audio_chunk.read()
    if not chunk_bytes:
        raise HTTPException(status_code=400, detail="Empty audio payload")
    
    supported = {
        "audio/webm": "webm",
        "audio/ogg": "ogg",
        "audio/mp3": "mp3",
        "audio/mpeg": "mp3",
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/mp4": "mp4",
        "audio/m4a": "m4a",
        "video/webm": "webm",
    }
    
    def pick_mime() -> str:
        for candidate in [mime_type, audio_chunk.content_type, "audio/webm"]:
            if not candidate:
                continue
            base = candidate.split(";")[0].strip().lower()
            if base in supported:
                return base
        return "audio/webm"
    
    mime = pick_mime()
    ext = supported[mime]
    filename = audio_chunk.filename or f"chunk.{ext}"
    content_type = mime
    
    logger.info(f"[RAG-AUDIO-CHUNK] Processing: filename={filename}, size={len(chunk_bytes)}")
    
    try:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, chunk_bytes, content_type),
            language=language,
        )
        user_query = transcript.text
        logger.info(f"[RAG-AUDIO-CHUNK] Transcribed query: '{user_query}'")
    except Exception as exc:
        logger.exception("Transcription failed in RAG audio chunk query")
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}") from exc
    
    # Step 2: RAG Query
    try:
        if not user_query.strip():
            raise HTTPException(status_code=400, detail="Transcribed query is empty")
        
        vector_db = get_vector_store()
        results = retrieve(user_query, vector_db, k=k)
        response_text = adjust_tone_with_llm(results, user_query, tone)
        
        logger.info(f"[RAG-AUDIO-CHUNK] Generated response: '{response_text}'")
    except Exception as exc:
        logger.exception("RAG query failed in audio chunk pipeline")
        raise HTTPException(status_code=502, detail=f"RAG query failed: {exc}") from exc
    
    # Step 3: Text-to-Speech
    try:
        stream = client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice=voice or "alloy",
            input=response_text,
            response_format="mp3",
        )
    except Exception as exc:
        logger.exception("TTS failed in RAG audio chunk query")
        raise HTTPException(status_code=502, detail=f"TTS failed: {exc}") from exc
    
    def iter_audio():
        with stream as response:
            for chunk in response.iter_bytes():
                yield chunk
    
    headers = {
        "Content-Disposition": "inline; filename=rag-response.mp3",
        "X-Transcribed-Query": user_query,
        "X-Response-Text": response_text[:200]  # Truncated for header size limits
    }
    return StreamingResponse(iter_audio(), media_type="audio/mpeg", headers=headers)

# cd 'c:\Users\praja\Desktop\neir-classification'; python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000