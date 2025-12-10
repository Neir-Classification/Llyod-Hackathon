"""Voice module initialization."""
from .speech_to_text import SpeechToText, StreamingSpeechToText, transcribe
from .text_to_speech import TextToSpeech, FallbackTTS, get_tts, speak
from .audio_handler import (
    AudioConfig,
    MicrophoneHandler,
    AudioPlayer,
    WebAudioHandler,
    VoicePipeline
)

__all__ = [
    # STT
    "SpeechToText",
    "StreamingSpeechToText",
    "transcribe",
    # TTS
    "TextToSpeech",
    "FallbackTTS",
    "get_tts",
    "speak",
    # Audio
    "AudioConfig",
    "MicrophoneHandler",
    "AudioPlayer",
    "WebAudioHandler",
    "VoicePipeline"
]
