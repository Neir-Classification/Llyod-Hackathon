import logging
import os
import json
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
    knowledge base. For example: "Could you please specify which \[policy type/customer name/etc.] you are referring to?"

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

\* **User Question:** "What is John Smith's life insurance policy number?"

\* **Identify Keywords:** "John Smith", "life insurance", "policy number"

\* **Search Knowledge Base:** Search for entries containing these keywords.

\* **Relevant Entry Found:** (The John Smith entry we discussed earlier)

\* **Extract Answer:** Locate the value for the "policy\_number" field ("LIFE-001").

\* **Formulate Response:** "John Smith's life insurance policy number is LIFE-001."

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

# cd 'c:\Users\praja\Desktop\neir-classification'; python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000