import logging
import os
import json
import asyncio
import hashlib
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
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

# Thread pool for running blocking operations
executor = ThreadPoolExecutor(max_workers=4)


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
AUDIO_CACHE_DIR = BASE_DIR / "audio_cache"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

TONE_PROMPTS = {
    "angry": "You are a calm, empathetic customer service agent. Acknowledge the user's frustration briefly and provide clear information. Avoid defensive or technical language. Keep it short and reassuring.",
    "confused": "You are a patient and reassuring assistant. Explain the policy information simply and clearly. Avoid jargon. Use everyday language.",
    "neutral": "You are a professional insurance assistant. Provide clear, factual information about the policy. Be direct and concise.",
    "happy": "You are a warm and friendly insurance assistant. Provide the policy information in a positive, helpful manner. Keep it professional but personable.",
    "anxious": "You are a reassuring and supportive assistant. Provide clear information and emphasize what's covered and next steps. Be comforting and specific."
}

# ============================================================================
# DUAL-PIPELINE: Fast Reaction System
# ============================================================================

# Intent categories for fast classification (ordered by priority - first match with high score wins)
INTENT_CATEGORIES = {
    "greeting": ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"],
    # Emergency/disaster situations - highest priority for empathy
    "emergency": [
        "burned", "burn", "fire", "flood", "flooded", "earthquake", "tornado", "hurricane", 
        "disaster", "destroyed", "destruction", "total loss", "everything gone", "lost everything",
        "died", "death", "passed away", "hospital", "injured", "injury", "hurt"
    ],
    # Theft and break-ins
    "theft": [
        "stolen", "robbed", "robbery", "burglar", "burglary", "break-in", "broke in", 
        "thief", "thieves", "missing", "took my", "stole"
    ],
    # Accidents and damage
    "accident": [
        "accident", "crash", "crashed", "hit", "collision", "collided", "wreck", "wrecked",
        "totaled", "smashed", "rear-ended", "side-swiped", "fender bender"
    ],
    # Property damage (non-emergency)
    "damage": [
        "damage", "damaged", "broken", "cracked", "shattered", "dent", "dented", 
        "scratched", "leak", "leaking", "water damage", "mold"
    ],
    # Claims (general)
    "claim": ["claim", "file a claim", "make a claim", "claims process", "incident", "report"],
    "cancel": ["cancel", "cancellation", "stop my", "end my", "terminate", "quit", "close my"],
    "payment": ["pay", "payment", "premium", "cost", "price", "bill", "due", "amount", "fee", "monthly", "charge"],
    "coverage": ["cover", "covered", "coverage", "include", "included", "protect", "protection", "deductible", "limit", "limits"],
    "distress": ["help", "urgent", "worried", "scared", "confused", "don't understand", "frustrated", "angry", "anxious"],
    "question": ["what", "how", "when", "where", "why", "can", "could", "would"],
}

# Intent priority order (higher priority intents are checked first)
INTENT_PRIORITY = ["greeting", "emergency", "theft", "accident", "damage", "claim", "cancel", "payment", "coverage", "distress", "question"]

# Quick acknowledgment responses (pre-cached for instant playback)
QUICK_RESPONSES = {
    # Emergency responses - deeply empathetic
    "emergency_fire": "Oh no, I'm so sorry to hear about the fire. That must be incredibly difficult. Let me help you right away.",
    "emergency_flood": "I'm so sorry about the flooding. I know this is overwhelming. Let me find what your policy covers immediately.",
    "emergency_general": "I'm so sorry you're going through this. This is exactly what we're here for. Let me help you right now.",
    
    # Theft responses
    "theft_recent": "I'm really sorry this happened to you. That's such a violation. Let me help you start the claims process right away.",
    "theft_general": "I'm sorry to hear about the theft. Let me check your coverage and help you file a claim.",
    
    # Accident responses
    "accident_serious": "I'm so sorry about your accident. I hope everyone is okay. Let me help you with your claim right away.",
    "accident_vehicle": "I'm sorry to hear about the accident. Let me check your coverage and walk you through the next steps.",
    "accident_general": "I'm sorry that happened. Let me look into your coverage for this situation.",
    
    # Damage responses
    "damage_property": "I'm sorry about the damage. Let me check what your policy covers for this.",
    "damage_general": "I understand you have damage to report. Let me find the details on your coverage.",
    
    # Original responses
    "claim_distress": "I'm so sorry to hear that happened. Let me look into your coverage right away.",
    "claim_neutral": "I understand you need help with a claim. Let me check that for you.",
    "coverage_question": "Great question about your coverage. Let me find the exact details for you.",
    "payment_question": "I'll check your payment information for you right now.",
    "cancel_request": "I understand you're asking about cancellation. Let me get those details.",
    "general_question": "Good question! Let me look that up for you.",
    "distress_general": "I hear you, and I want to help. Let me find the information you need.",
    "greeting": "Hello! How can I help you with your insurance today?",
    "default": "I'm on it. Let me find that information for you.",
}

# Tone-specific quick response modifiers
TONE_QUICK_RESPONSES = {
    "angry": {
        "prefix": "I completely understand your frustration. ",
        "suffix": " I'll get you the answers you need.",
    },
    "anxious": {
        "prefix": "Don't worry, I'm here to help. ",
        "suffix": " Everything will be okay.",
    },
    "confused": {
        "prefix": "No problem at all. ",
        "suffix": " I'll explain everything clearly.",
    },
    "happy": {
        "prefix": "Absolutely! ",
        "suffix": "",
    },
    "neutral": {
        "prefix": "",
        "suffix": "",
    },
}

# Cache for pre-generated audio responses
_audio_cache: dict[str, bytes] = {}

# Global vector store (cached)
_vector_store = None


def detect_intent_fast(text: str) -> tuple[str, float]:
    """
    Fast intent detection using keyword matching with priority.
    Returns (intent_key, confidence) in under 10ms.
    
    Priority order ensures specific intents (like "claim", "cancel") are 
    detected before generic ones (like "question").
    """
    text_lower = text.lower()
    words = set(text_lower.split())
    
    scores = {}
    for intent, keywords in INTENT_CATEGORIES.items():
        # Check for phrase matches first (more specific)
        phrase_matches = sum(2 for kw in keywords if ' ' in kw and kw in text_lower)
        # Then check word matches
        word_matches = sum(1 for kw in keywords if ' ' not in kw and (kw in text_lower or kw in words))
        score = phrase_matches + word_matches
        if score > 0:
            scores[intent] = score
    
    if not scores:
        return "default", 0.0
    
    # Use priority order to break ties - earlier in priority list wins
    # This ensures "greeting" beats "question", "claim" beats "coverage", etc.
    best_intent = None
    best_score = 0
    
    for intent in INTENT_PRIORITY:
        if intent in scores:
            score = scores[intent]
            # Give priority bonus to higher-priority intents
            priority_bonus = (len(INTENT_PRIORITY) - INTENT_PRIORITY.index(intent)) * 0.5
            adjusted_score = score + priority_bonus
            
            if adjusted_score > best_score or best_intent is None:
                best_score = adjusted_score
                best_intent = intent
    
    # If no priority match, fall back to max score
    if best_intent is None:
        best_intent = max(scores, key=scores.get)
    
    confidence = min(scores[best_intent] / 3.0, 1.0)  # Normalize to 0-1
    
    return best_intent, confidence


def get_quick_response_key(intent: str, tone: str, text: str) -> str:
    """Determine the appropriate quick response key based on intent and tone."""
    text_lower = text.lower()
    
    # Check for distress signals
    is_distressed = any(kw in text_lower for kw in INTENT_CATEGORIES.get("distress", []))
    
    # Emergency situations - highest priority, always empathetic
    if intent == "emergency":
        if any(word in text_lower for word in ["fire", "burned", "burn", "burning"]):
            return "emergency_fire"
        elif any(word in text_lower for word in ["flood", "flooded", "flooding", "water"]):
            return "emergency_flood"
        else:
            return "emergency_general"
    
    # Theft situations
    elif intent == "theft":
        if any(word in text_lower for word in ["just", "today", "last night", "yesterday", "recently"]):
            return "theft_recent"
        else:
            return "theft_general"
    
    # Accident situations
    elif intent == "accident":
        if any(word in text_lower for word in ["hospital", "injured", "hurt", "serious", "bad"]):
            return "accident_serious"
        elif any(word in text_lower for word in ["car", "vehicle", "truck", "motorcycle", "driving"]):
            return "accident_vehicle"
        else:
            return "accident_general"
    
    # Damage situations
    elif intent == "damage":
        if any(word in text_lower for word in ["house", "home", "property", "roof", "wall", "window"]):
            return "damage_property"
        else:
            return "damage_general"
    
    # Original intent handling
    elif intent == "claim":
        return "claim_distress" if is_distressed or tone in ["angry", "anxious"] else "claim_neutral"
    elif intent == "coverage":
        return "coverage_question"
    elif intent == "payment":
        return "payment_question"
    elif intent == "cancel":
        return "cancel_request"
    elif intent == "greeting":
        return "greeting"
    elif intent == "distress":
        return "distress_general"
    elif intent == "question":
        return "general_question"
    else:
        return "default"


def get_quick_response_text(intent: str, tone: str, text: str) -> str:
    """Get the quick acknowledgment text for the detected intent."""
    response_key = get_quick_response_key(intent, tone, text)
    base_response = QUICK_RESPONSES.get(response_key, QUICK_RESPONSES["default"])
    
    # Apply tone modifiers
    tone_mod = TONE_QUICK_RESPONSES.get(tone, TONE_QUICK_RESPONSES["neutral"])
    
    # Don't add prefix/suffix for greetings
    if response_key == "greeting":
        return base_response
    
    return f"{tone_mod['prefix']}{base_response}{tone_mod['suffix']}"


def get_audio_cache_path(text: str, voice: str) -> Path:
    """Get the cache file path for a given text and voice."""
    cache_key = hashlib.md5(f"{text}:{voice}".encode()).hexdigest()
    return AUDIO_CACHE_DIR / f"{cache_key}.mp3"


async def get_or_generate_quick_audio(text: str, voice: str = "alloy") -> bytes:
    """Get cached audio or generate and cache it."""
    cache_key = f"{text}:{voice}"
    
    # Check memory cache first
    if cache_key in _audio_cache:
        logger.info(f"[QUICK-AUDIO] Memory cache hit for: '{text[:30]}...'")
        return _audio_cache[cache_key]
    
    # Check disk cache
    cache_path = get_audio_cache_path(text, voice)
    if cache_path.exists():
        logger.info(f"[QUICK-AUDIO] Disk cache hit for: '{text[:30]}...'")
        audio_data = cache_path.read_bytes()
        _audio_cache[cache_key] = audio_data
        return audio_data
    
    # Generate new audio
    logger.info(f"[QUICK-AUDIO] Generating audio for: '{text[:30]}...'")
    client = get_openai_client()
    
    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text,
        response_format="mp3",
    )
    
    audio_data = response.content
    
    # Cache to memory and disk
    _audio_cache[cache_key] = audio_data
    cache_path.write_bytes(audio_data)
    
    return audio_data


async def warm_audio_cache(voice: str = "alloy"):
    """Pre-generate and cache all quick response audio files."""
    logger.info("[CACHE-WARM] Starting audio cache warming...")
    
    all_responses = set()
    
    # Generate all possible quick responses
    for tone in TONE_QUICK_RESPONSES.keys():
        for intent in list(INTENT_CATEGORIES.keys()) + ["default"]:
            text = get_quick_response_text(intent, tone, "")
            all_responses.add(text)
    
    # Also add base responses
    for text in QUICK_RESPONSES.values():
        all_responses.add(text)
    
    # Generate audio for each
    for text in all_responses:
        try:
            await get_or_generate_quick_audio(text, voice)
        except Exception as e:
            logger.warning(f"[CACHE-WARM] Failed to generate audio for '{text[:30]}...': {e}")
    
    logger.info(f"[CACHE-WARM] Completed. Cached {len(all_responses)} audio files.")


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


def extract_structured_content_with_chatgpt(page_content: str, page_num: int, policy_name: str) -> str:
    """Use ChatGPT to extract and structure content from a PDF page."""
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
        
        prompt = f"""You are an expert at extracting and structuring insurance policy information.

Analyze the following insurance policy page and extract ALL information into a well-structured, searchable format.

IMPORTANT INSTRUCTIONS:
1. Extract ALL data points including: coverage details, limits, conditions, exclusions, definitions, procedures, contact info, etc.
2. Organize information hierarchically with clear sections and subsections
3. Convert tables into structured text format with clear labels
4. Preserve all numerical values, percentages, and monetary amounts
5. Keep policy-specific terminology intact
6. Create clear relationships between related items
7. Make the output optimized for semantic search and retrieval

Format your response as structured text with:
- Clear section headers (use ### for sections, #### for subsections)
- Bullet points for lists
- Key-value pairs for specific data (e.g., "Maximum Limit: $500,000")
- Complete sentences for explanations and conditions

Policy: {policy_name}
Page: {page_num}

---PAGE CONTENT---
{page_content}
---END PAGE CONTENT---

Structured Output:"""
        
        messages = [{"role": "user", "content": prompt}]
        response = llm.invoke(messages)
        structured_text = response.content
        
        logger.info(f"[ChatGPT] Processed {policy_name} page {page_num}: {len(structured_text)} chars")
        return structured_text
        
    except Exception as e:
        logger.error(f"[ChatGPT] Failed to process page {page_num}: {e}")
        # Fallback to original content if ChatGPT fails
        return page_content


def load_pdfs_with_chatgpt(pdf_paths):
    """Load PDFs and process each page through ChatGPT for structured extraction."""
    docs = []
    for path in pdf_paths:
        if not path.exists():
            logger.warning(f"PDF not found: {path}")
            continue
        
        logger.info(f"[ChatGPT] Processing PDF: {path.name}")
        loader = PyPDFLoader(str(path))
        loaded_docs = loader.load()
        policy_name = path.name
        
        for doc in loaded_docs:
            page_num = doc.metadata.get("page", "unknown")
            
            # Process through ChatGPT for structured extraction
            structured_content = extract_structured_content_with_chatgpt(
                doc.page_content, 
                page_num, 
                policy_name
            )
            
            # Create new document with structured content
            structured_doc = Document(
                page_content=structured_content,
                metadata={
                    "policy_name": policy_name,
                    "page_number": page_num,
                    "source": str(path),
                    "processed_by": "gpt-4o"
                }
            )
            docs.append(structured_doc)
        
        logger.info(f"[ChatGPT] Completed processing {path.name}: {len([d for d in docs if d.metadata['policy_name'] == policy_name])} pages")
    
    return docs


def chunk_docs(docs, chunk_size=2000, chunk_overlap=200):
    """Split ChatGPT-structured documents into semantic chunks."""
    # Use section-aware splitting for ChatGPT-structured content
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n### ", "\n#### ", "\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_documents(docs)
    for chunk in chunks:
        if "policy_name" not in chunk.metadata:
            chunk.metadata["policy_name"] = chunk.metadata.get("source", "unknown")
        if "page_number" not in chunk.metadata and "page" in chunk.metadata:
            chunk.metadata["page_number"] = chunk.metadata["page"]
    return chunks


def build_vector_store():
    """Build a new FAISS vector store from PDFs using ChatGPT processing."""
    global _vector_store
    logger.info("Building FAISS index from PDFs with ChatGPT processing...")
    
    # Use ChatGPT-based processing
    docs = load_pdfs_with_chatgpt(PDF_PATHS)
    if not docs:
        raise RuntimeError("No PDFs found to index")
    
    logger.info(f"Loaded {len(docs)} pages from PDFs")
    
    # Chunk the structured content
    chunks = chunk_docs(docs)
    logger.info(f"Created {len(chunks)} chunks from {len(docs)} pages")
    
    # Create embeddings and build FAISS index
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    _vector_store = FAISS.from_documents(chunks, embeddings)
    FAISS_DIR.mkdir(parents=True, exist_ok=True)
    _vector_store.save_local(str(FAISS_DIR))
    logger.info(f"FAISS index built and saved to {FAISS_DIR}")
    return _vector_store


def retrieve(query: str, vector_db: FAISS, k: int = 3):
    """Retrieve relevant chunks from the vector store (ChatGPT-structured) with scores."""
    # Use similarity search with scores for citations
    results = vector_db.similarity_search_with_score(query, k=k)
    
    # Don't truncate ChatGPT-structured content as aggressively
    for doc, score in results:
        doc.page_content = doc.page_content[:1000]
    
    return results


def adjust_tone_with_llm(retrieved_chunks, user_question: str, tone: str = "neutral", conversation_history: list = None) -> str:
    """Use LLM to generate a tone-appropriate response from retrieved chunks with conversation context."""
    if tone not in TONE_PROMPTS:
        tone = "neutral"
    
    if conversation_history is None:
        conversation_history = []
    
    # Combine retrieved chunks into context
    context = "\n\n".join([doc.page_content for doc, _ in retrieved_chunks])
    
    # Build conversation history context
    history_context = ""
    if conversation_history:
        history_context = "\n\nPrevious Conversation:\n"
        for msg in conversation_history:  # Use complete conversation history
            role = "User" if msg.get("role") == "user" else "Assistant"
            history_context += f"{role}: {msg.get('content', '')}\n"
    
    system_prompt = f"""{TONE_PROMPTS[tone]}

Based on the policy information below, answer the user's question in 3-4 short sentences suitable for voice (20-30 seconds of speech).
**Instructions for Answering Insurance Questions Using the Knowledge Base:**

1.  **Prioritize Knowledge Base Search:** Always attempt to answer the user's question by first searching the provided knowledge base.

2.  **Identify Key Information Needs & Keywords:** Understand what specific information the user is asking for. Extract the most relevant
    keywords and entities from their query (e.g., name, policy number, type of information).

3.  **Execute Knowledge Base Search:** Use the identified keywords to search the knowledge base. Be mindful of potential synonyms or related 
    terms if the initial search is unsuccessful.

4.  **Analyze Search Results:** Carefully review the entries returned by the search. Identify the entry that directly addresses the user's question.

5.  **Extract and Formulate Answer:** Locate the specific data point needed to answer the user's query within the relevant knowledge base entry. 
    Formulate a clear, concise, and grammatically correct answer using this information. Avoid directly copying the entire knowledge base entry.

6.  **Handle "No Match" Scenarios:** If your search yields no relevant results, inform the user politely that the information is not currently 
    available in the knowledge base. For example: "I'm sorry, but I couldn't find that information in our current knowledge base."

7.  **Seek Clarification for Ambiguity:** If the user's question is unclear or ambiguous, ask for specific details before attempting to search the 
    knowledge base. For example: "Could you please specify which [policy type/customer name/etc.] you are referring to?"

8.  **Maintain Professional Tone:** Always maintain a helpful and professional tone while providing information to the user.

9.  **Report Knowledge Base Issues:** If you identify any outdated, incorrect, or missing information in the knowledge base, flag it for review by
     the administrator.

10. **Enhanced Data Analysis:** For questions that require calculations (e.g., total, average, sum), perform the necessary calculations using the 
    data extracted from the knowledge base. Show your work or the formulas used if appropriate for clarity.

11. **Temporal Reasoning:** When a question involves dates, extract all relevant dates from the knowledge base. Perform any necessary date 
    calculations (e.g., differences, comparisons). Be precise with date formats in your answers (e.g., YYYY-MM-DD).

12. **Table Generation:** If the question asks for a table or a summary of multiple items, organize your answer in a table format. Include 
    clear column headers, and align the data appropriately. Sort the table as requested. If no sort order is specified, use a logical order 
    (e.g., alphabetical, numerical).

13. **Multi-Step Reasoning:** Break down complex questions into smaller, manageable steps. Extract the information needed for each step from 
    the knowledge base. Use the results of one step to inform the next. Maintain context throughout the process.

14. **Context Maintenance:** Pay attention to the context of the conversation. If a user refers to a previous query, try to use the information 
    you already provided. Avoid repeating information unless necessary for clarity.

**Example Workflow:**

* **User Question:** "What is John Smith's life insurance policy number?"

* **Identify Keywords:** "John Smith", "life insurance", "policy number"

* **Search Knowledge Base:** Search for entries containing these keywords.

* **Relevant Entry Found:** (The John Smith entry we discussed earlier)

* **Extract Answer:** Locate the value for the "policy_number" field ("LIFE-001").

* **Formulate Response:** "John Smith's life insurance policy number is LIFE-001."

**Remember:** Your goal is to efficiently and accurately retrieve information from the knowledge base to answer user inquiries, 
perform calculations, handle dates, generate tables, and maintain context when necessary.

Policy Context:
{context}{history_context}"""

    user_prompt = f"User question: {user_question}"
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
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


class SpeechRequest(BaseModel):
    text: str
    voice: Optional[str] = "alloy"
    audio_format: Optional[str] = "mp3"


class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str


class RAGQueryRequest(BaseModel):
    query: str
    tone: Optional[str] = "neutral"
    k: Optional[int] = 2
    conversation_history: Optional[list[ChatMessage]] = []


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
    """Query the RAG pipeline and return a tone-adjusted response with conversation history."""
    try:
        if not body.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        logger.info(f"[RAG QUERY INPUT] Query: '{body.query}' | Tone: '{body.tone}' | K: {body.k} | History: {len(body.conversation_history or [])}")
        
        # Get or build the vector store
        vector_db = get_vector_store()
        
        # Retrieve relevant chunks
        results = retrieve(body.query, vector_db, k=body.k)
        
        # Convert conversation history to dict format
        history = [{"role": msg.role, "content": msg.content} for msg in (body.conversation_history or [])]
        
        # Generate tone-adjusted response with conversation context
        response_text = adjust_tone_with_llm(results, body.query, body.tone, history)
        
        # Format citations from retrieved documents
        citations = []
        for doc, score in results:
            citations.append({
                "policy_name": doc.metadata.get("policy_name", "unknown"),
                "page_number": doc.metadata.get("page_number", "N/A"),
                "content": doc.page_content[:300],  # Preview for citation
                "score": float(score)
            })
        
        logger.info(f"[RAG QUERY OUTPUT] Response: '{response_text}' | Citations: {len(citations)}")
        
        return JSONResponse({
            "response": response_text,
            "tone": body.tone,
            "query": body.query,
            "citations": citations
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


# ============================================================================
# DUAL-PIPELINE ENDPOINTS
# ============================================================================

class DualPipelineRequest(BaseModel):
    query: str
    tone: Optional[str] = "neutral"
    k: Optional[int] = 2
    voice: Optional[str] = "alloy"
    conversation_history: Optional[list[ChatMessage]] = []


@app.post("/intent-detect")
async def intent_detect(query: str = Form(...)) -> JSONResponse:
    """
    Fast intent detection endpoint.
    Returns intent and quick response text in <50ms.
    """
    intent, confidence = detect_intent_fast(query)
    quick_text = get_quick_response_text(intent, "neutral", query)
    
    return JSONResponse({
        "intent": intent,
        "confidence": confidence,
        "quick_response": quick_text,
    })


@app.post("/quick-response-audio")
async def quick_response_audio(
    query: str = Form(...),
    tone: Optional[str] = Form("neutral"),
    voice: Optional[str] = Form("alloy"),
) -> StreamingResponse:
    """
    Get pre-cached audio for quick acknowledgment response.
    Returns cached audio in <100ms for instant playback.
    """
    intent, _ = detect_intent_fast(query)
    quick_text = get_quick_response_text(intent, tone, query)
    
    try:
        audio_data = await get_or_generate_quick_audio(quick_text, voice)
        
        return StreamingResponse(
            iter([audio_data]),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=quick-response.mp3",
                "X-Quick-Response-Text": quick_text,
                "X-Intent": intent,
            }
        )
    except Exception as exc:
        logger.exception("Quick response audio generation failed")
        raise HTTPException(status_code=502, detail=f"Audio generation failed: {exc}") from exc


@app.post("/rag-query-dual")
async def rag_query_dual(body: DualPipelineRequest) -> JSONResponse:
    """
    Dual-pipeline RAG query that returns both quick and full responses.
    
    The quick response is returned immediately for instant feedback,
    while the full RAG response provides accurate, contextual information.
    """
    try:
        if not body.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Fast Pipeline: Intent detection and quick response (<50ms)
        intent, confidence = detect_intent_fast(body.query)
        quick_text = get_quick_response_text(intent, body.tone, body.query)
        
        logger.info(f"[DUAL-PIPELINE] Intent: {intent} ({confidence:.2f}) | Quick: '{quick_text[:50]}...'")
        
        # Deep Pipeline: Full RAG query
        vector_db = get_vector_store()
        results = retrieve(body.query, vector_db, k=body.k)
        
        history = [{"role": msg.role, "content": msg.content} for msg in (body.conversation_history or [])]
        full_response = adjust_tone_with_llm(results, body.query, body.tone, history)
        
        # Format citations
        citations = []
        for doc, score in results:
            citations.append({
                "policy_name": doc.metadata.get("policy_name", "unknown"),
                "page_number": doc.metadata.get("page_number", "N/A"),
                "content": doc.page_content[:300],
                "score": float(score)
            })
        
        logger.info(f"[DUAL-PIPELINE] Full response: '{full_response[:50]}...'")
        
        return JSONResponse({
            "quick_response": quick_text,
            "full_response": full_response,
            "intent": intent,
            "intent_confidence": confidence,
            "tone": body.tone,
            "query": body.query,
            "citations": citations
        })
    except Exception as exc:
        logger.exception("Dual-pipeline RAG query failed")
        raise HTTPException(status_code=502, detail=f"RAG query failed: {exc}") from exc


@app.websocket("/ws/dual-pipeline")
async def websocket_dual_pipeline(websocket: WebSocket):
    """
    WebSocket endpoint for real-time dual-pipeline communication.
    
    Protocol:
    1. Client sends: {"type": "query", "query": "...", "tone": "...", "voice": "..."}
    2. Server sends: {"type": "quick", "text": "...", "intent": "...", "audio_base64": "..."}
    3. Server sends: {"type": "full", "text": "...", "citations": [...], "audio_base64": "..."}
    """
    await websocket.accept()
    logger.info("[WS] Client connected to dual-pipeline")
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "query":
                query = data.get("query", "")
                tone = data.get("tone", "neutral")
                voice = data.get("voice", "alloy")
                k = data.get("k", 2)
                history = data.get("conversation_history", [])
                
                if not query.strip():
                    await websocket.send_json({"type": "error", "message": "Empty query"})
                    continue
                
                logger.info(f"[WS] Received query: '{query}'")
                
                # FAST PIPELINE: Send quick response immediately
                intent, confidence = detect_intent_fast(query)
                quick_text = get_quick_response_text(intent, tone, query)
                
                # Get cached audio (should be instant)
                try:
                    quick_audio = await get_or_generate_quick_audio(quick_text, voice)
                    import base64
                    quick_audio_b64 = base64.b64encode(quick_audio).decode('utf-8')
                except Exception as e:
                    logger.warning(f"[WS] Quick audio failed: {e}")
                    quick_audio_b64 = None
                
                # Send quick response immediately
                await websocket.send_json({
                    "type": "quick",
                    "text": quick_text,
                    "intent": intent,
                    "confidence": confidence,
                    "audio_base64": quick_audio_b64,
                })
                logger.info(f"[WS] Sent quick response: '{quick_text[:30]}...'")
                
                # DEEP PIPELINE: Process full RAG in background
                try:
                    vector_db = get_vector_store()
                    results = retrieve(query, vector_db, k=k)
                    full_response = adjust_tone_with_llm(results, query, tone, history)
                    
                    # Generate full response audio
                    client = get_openai_client()
                    full_audio_response = client.audio.speech.create(
                        model="gpt-4o-mini-tts",
                        voice=voice,
                        input=full_response,
                        response_format="mp3",
                    )
                    full_audio_b64 = base64.b64encode(full_audio_response.content).decode('utf-8')
                    
                    # Format citations
                    citations = []
                    for doc, score in results:
                        citations.append({
                            "policy_name": doc.metadata.get("policy_name", "unknown"),
                            "page_number": doc.metadata.get("page_number", "N/A"),
                            "content": doc.page_content[:300],
                            "score": float(score)
                        })
                    
                    # Send full response
                    await websocket.send_json({
                        "type": "full",
                        "text": full_response,
                        "citations": citations,
                        "audio_base64": full_audio_b64,
                    })
                    logger.info(f"[WS] Sent full response: '{full_response[:30]}...'")
                    
                except Exception as e:
                    logger.exception("[WS] Full pipeline failed")
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Full pipeline failed: {str(e)}"
                    })
            
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        logger.info("[WS] Client disconnected")
    except Exception as e:
        logger.exception("[WS] WebSocket error")


@app.post("/rag-audio-dual")
async def rag_audio_dual(
    audio_file: UploadFile = File(...),
    tone: Optional[str] = Form("neutral"),
    k: Optional[int] = Form(2),
    voice: Optional[str] = Form("alloy"),
    language: Optional[str] = Form(None),
) -> JSONResponse:
    """
    Dual-pipeline audio-to-audio RAG endpoint.
    
    Returns both quick response audio (for immediate playback) and 
    full response audio (for accurate information).
    
    Response format:
    {
        "transcribed_query": "...",
        "quick_response": {"text": "...", "audio_base64": "..."},
        "full_response": {"text": "...", "audio_base64": "...", "citations": [...]}
    }
    """
    import base64
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
        logger.info(f"[DUAL-AUDIO] Transcribed query: '{user_query}'")
    except Exception as exc:
        logger.exception("Transcription failed")
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}") from exc
    
    if not user_query.strip():
        raise HTTPException(status_code=400, detail="Transcribed query is empty")
    
    # Step 2a: FAST PIPELINE - Intent detection and quick response
    intent, confidence = detect_intent_fast(user_query)
    quick_text = get_quick_response_text(intent, tone, user_query)
    
    try:
        quick_audio = await get_or_generate_quick_audio(quick_text, voice)
        quick_audio_b64 = base64.b64encode(quick_audio).decode('utf-8')
    except Exception as e:
        logger.warning(f"[DUAL-AUDIO] Quick audio generation failed: {e}")
        quick_audio_b64 = None
    
    logger.info(f"[DUAL-AUDIO] Quick response ready: '{quick_text[:30]}...'")
    
    # Step 2b: DEEP PIPELINE - Full RAG query
    try:
        vector_db = get_vector_store()
        results = retrieve(user_query, vector_db, k=k)
        full_response = adjust_tone_with_llm(results, user_query, tone)
        
        # Generate full response audio
        full_audio_response = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=voice,
            input=full_response,
            response_format="mp3",
        )
        full_audio_b64 = base64.b64encode(full_audio_response.content).decode('utf-8')
        
        # Format citations
        citations = []
        for doc, score in results:
            citations.append({
                "policy_name": doc.metadata.get("policy_name", "unknown"),
                "page_number": doc.metadata.get("page_number", "N/A"),
                "content": doc.page_content[:300],
                "score": float(score)
            })
        
        logger.info(f"[DUAL-AUDIO] Full response ready: '{full_response[:30]}...'")
        
    except Exception as exc:
        logger.exception("Full RAG pipeline failed")
        raise HTTPException(status_code=502, detail=f"RAG query failed: {exc}") from exc
    
    return JSONResponse({
        "transcribed_query": user_query,
        "intent": intent,
        "intent_confidence": confidence,
        "quick_response": {
            "text": quick_text,
            "audio_base64": quick_audio_b64,
        },
        "full_response": {
            "text": full_response,
            "audio_base64": full_audio_b64,
            "citations": citations,
        }
    })


@app.post("/warm-cache")
async def warm_cache(voice: Optional[str] = Form("alloy")) -> JSONResponse:
    """Pre-generate and cache all quick response audio files."""
    try:
        await warm_audio_cache(voice)
        return JSONResponse({"status": "ok", "message": "Audio cache warmed successfully"})
    except Exception as exc:
        logger.exception("Cache warming failed")
        raise HTTPException(status_code=502, detail=f"Cache warming failed: {exc}") from exc


@app.on_event("startup")
async def startup_event():
    """Initialize caches on startup."""
    logger.info("[STARTUP] Initializing dual-pipeline system...")
    
    # Pre-load the vector store
    try:
        get_vector_store()
        logger.info("[STARTUP] Vector store loaded")
    except Exception as e:
        logger.warning(f"[STARTUP] Vector store not available: {e}")
    
    # Warm the audio cache in background (non-blocking)
    # asyncio.create_task(warm_audio_cache())


# cd 'c:\Users\praja\Desktop\neir-classification'; python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000