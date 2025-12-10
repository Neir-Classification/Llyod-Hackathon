"""
Text-to-Speech module using ElevenLabs.
"""
import io
import wave
from pathlib import Path
from typing import Optional, Union, Generator
import httpx
import numpy as np

from src.utils.config import config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class TextToSpeech:
    """
    Text-to-Speech using ElevenLabs API.
    Optimized for low latency with streaming support.
    """
    
    BASE_URL = "https://api.elevenlabs.io/v1"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
        model_id: str = "eleven_turbo_v2"
    ):
        self.api_key = api_key or config.elevenlabs.api_key
        self.voice_id = voice_id or config.elevenlabs.voice_id
        self.model_id = model_id
        
        self.headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
    
    def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0
    ) -> bytes:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to convert to speech
            voice_id: Override default voice
            stability: Voice stability (0-1)
            similarity_boost: Voice similarity (0-1)
            style: Style strength (0-1)
        
        Returns:
            Audio data as bytes (MP3 format)
        """
        voice = voice_id or self.voice_id
        url = f"{self.BASE_URL}/text-to-speech/{voice}"
        
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": style
            }
        }
        
        logger.info(f"Synthesizing: '{text[:50]}...' with voice {voice}")
        
        response = httpx.post(
            url,
            json=payload,
            headers=self.headers,
            timeout=30.0
        )
        
        if response.status_code != 200:
            raise Exception(f"TTS Error: {response.status_code} - {response.text}")
        
        return response.content
    
    def synthesize_stream(
        self,
        text: str,
        voice_id: Optional[str] = None,
        chunk_size: int = 1024
    ) -> Generator[bytes, None, None]:
        """
        Stream synthesized speech in chunks for lower latency.
        
        Args:
            text: Text to convert to speech
            voice_id: Override default voice
            chunk_size: Size of audio chunks to yield
        
        Yields:
            Audio data chunks (MP3 format)
        """
        voice = voice_id or self.voice_id
        url = f"{self.BASE_URL}/text-to-speech/{voice}/stream"
        
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        with httpx.stream(
            "POST",
            url,
            json=payload,
            headers=self.headers,
            timeout=30.0
        ) as response:
            if response.status_code != 200:
                raise Exception(f"TTS Stream Error: {response.status_code}")
            
            for chunk in response.iter_bytes(chunk_size=chunk_size):
                yield chunk
    
    def save_to_file(
        self,
        text: str,
        output_path: Union[str, Path],
        voice_id: Optional[str] = None
    ) -> Path:
        """
        Synthesize speech and save to file.
        
        Args:
            text: Text to convert
            output_path: Path for output audio file
            voice_id: Override default voice
        
        Returns:
            Path to saved file
        """
        output_path = Path(output_path)
        audio_data = self.synthesize(text, voice_id)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio_data)
        
        logger.info(f"Saved audio to: {output_path}")
        return output_path


class FallbackTTS:
    """
    Fallback TTS using OpenAI's TTS API.
    Used when ElevenLabs is unavailable.
    """
    
    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=config.openai.api_key)
        self.model = "tts-1"
        self.voice = "nova"  # Options: alloy, echo, fable, onyx, nova, shimmer
    
    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None
    ) -> bytes:
        """
        Synthesize speech using OpenAI TTS.
        
        Args:
            text: Text to convert
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
        
        Returns:
            Audio data as bytes (MP3 format)
        """
        response = self.client.audio.speech.create(
            model=self.model,
            voice=voice or self.voice,
            input=text,
            response_format="mp3"
        )
        
        return response.content
    
    def save_to_file(
        self,
        text: str,
        output_path: Union[str, Path]
    ) -> Path:
        """Save synthesized speech to file."""
        output_path = Path(output_path)
        audio_data = self.synthesize(text)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio_data)
        
        return output_path


def get_tts() -> Union[TextToSpeech, FallbackTTS]:
    """
    Get the best available TTS engine.
    Returns ElevenLabs if API key is set, otherwise falls back to OpenAI.
    """
    if config.elevenlabs.api_key:
        return TextToSpeech()
    else:
        logger.warning("ElevenLabs API key not set, using OpenAI TTS fallback")
        return FallbackTTS()


# Convenience function
def speak(text: str) -> bytes:
    """Quick TTS function."""
    tts = get_tts()
    return tts.synthesize(text)


if __name__ == "__main__":
    print("Text-to-Speech Module")
    print("=====================")
    print("Available classes:")
    print("  - TextToSpeech: ElevenLabs TTS (low latency)")
    print("  - FallbackTTS: OpenAI TTS (backup)")
    print("\nUse get_tts() to get the best available engine.")
