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

TONE_PROMPTS = {
    "angry": "You are a calm, empathetic customer service agent. Acknowledge the user's frustration briefly and provide clear information. Avoid defensive or technical language. Keep it short and reassuring.",
    "confused": "You are a patient and reassuring assistant. Explain the policy information simply and clearly. Avoid jargon. Use everyday language.",
    "neutral": "You are a professional insurance assistant. Provide clear, factual information about the policy. Be direct and concise.",
    "happy": "You are a warm and friendly insurance assistant. Provide the policy information in a positive, helpful manner. Keep it professional but personable.",
    "anxious": "You are a reassuring and supportive assistant. Provide clear information and emphasize what's covered and next steps. Be comforting and specific."
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


def adjust_tone_with_llm(retrieved_chunks, user_question: str, tone: str = "neutral") -> str:
    """Use LLM to generate a tone-appropriate response from retrieved chunks."""
    if tone not in TONE_PROMPTS:
        tone = "neutral"
    
    # Combine retrieved chunks into context
    context = "\n\n".join([doc.page_content for doc, _ in retrieved_chunks])
    
    system_prompt = f"""{TONE_PROMPTS[tone]}

Based on the policy information below, answer the user's question in 3-4 short sentences suitable for voice (20-30 seconds of speech).

Policy Context:
{context}"""

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


class RAGQueryRequest(BaseModel):
    query: str
    tone: Optional[str] = "neutral"
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
    """Query the RAG pipeline and return a tone-adjusted response."""
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
        
        logger.info(f"[RAG QUERY OUTPUT] Response: '{response_text}'")
        
        return JSONResponse({
            "response": response_text,
            "tone": body.tone,
            "query": body.query
        })
    except Exception as exc:
        logger.exception("RAG query failed")
        raise HTTPException(status_code=502, detail=f"RAG query failed: {exc}") from exc

# cd 'c:\Users\praja\Desktop\neir-classification'; python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000