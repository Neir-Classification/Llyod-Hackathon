# Speech/Text Backend

FastAPI service that offers:
- Speech input -> text output (OpenAI Whisper)
- Text input -> speech output (OpenAI TTS)

## Setup
1) Ensure Python 3.10+ is available.
2) Install deps:
   ```bash
   pip install -r requirements.txt
   ```
3) Set your key (one of):
  ```bash
  export OPENAI_API_KEY="sk-..."  # shell env
  # or create .env file next to main.py with: OPENAI_API_KEY=sk-...
  ```

## Run
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Visit the UI at `http://localhost:8000/`.

Live features:
- Live mic -> text via `/speech-to-text-chunk` streaming small blobs
- Auto-play TTS while typing (toggle in UI)

## Endpoints
- `GET /health` -> `{ "status": "ok" }`
- `POST /speech-to-text` (multipart form)
  - field `audio_file`: audio binary (wav/mp3/m4a)
  - optional `language`: ISO code (e.g., `en`)
  - response: `{ "text": "..." }`
- `POST /speech-to-text-chunk` (multipart form)
  - field `audio_chunk`: small audio chunk (e.g., webm)
  - optional `language`: ISO code
  - response: `{ "text": "..." }`
- `POST /text-to-speech` (JSON)
  - body: `{ "text": "Hello", "voice": "alloy", "audio_format": "mp3" }`
  - returns streaming audio with `audio/<format>` content-type

## Examples
Speech -> text:
```bash
curl -X POST \
  -F "audio_file=@/path/to/sample.wav" \
  http://localhost:8000/speech-to-text
```

Text -> speech (save to file):
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello there","voice":"alloy","audio_format":"mp3"}' \
  http://localhost:8000/text-to-speech \
  --output tts.mp3
```

## Frontend
- Served from `http://localhost:8000/`
- Upload or record audio, then transcribe.
- Type text, choose a voice/format, and play synthesized audio.

## Notes
- Uses `whisper-1` for transcription and `gpt-4o-mini-tts` for speech synthesis.
- Responses stream audio to avoid holding large payloads in memory.
