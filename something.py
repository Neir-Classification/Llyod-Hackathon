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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(title="Speech-Text Bridge", version="0.1.0")
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Load environment variables from a local .env file if present (for local dev convenience).
load_dotenv(BASE_DIR / ".env")


def get_openai_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set the OPENAI_API_KEY environment variable.")
    return OpenAI(api_key=api_key)


class SpeechRequest(BaseModel):
    text: str
    voice: Optional[str] = "alloy"
    audio_format: Optional[str] = "mp3"


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
