"""
Speech-to-Text module using OpenAI Whisper.
"""
import io
import tempfile
import wave
from pathlib import Path
from typing import Optional, Union, BinaryIO
import numpy as np

from openai import OpenAI

from src.utils.config import config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SpeechToText:
    """
    Speech-to-Text using OpenAI Whisper API.
    Optimized for low latency conversational use.
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=config.openai.api_key)
        self.model = "whisper-1"
        self.language = "en"
    
    def transcribe_file(
        self,
        audio_path: Union[str, Path],
        language: Optional[str] = None
    ) -> str:
        """
        Transcribe an audio file to text.
        
        Args:
            audio_path: Path to audio file (mp3, wav, m4a, etc.)
            language: Language code (optional, auto-detected if not specified)
        
        Returns:
            Transcribed text
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        logger.info(f"Transcribing: {audio_path.name}")
        
        with open(audio_path, "rb") as audio_file:
            response = self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
                language=language or self.language,
                response_format="text"
            )
        
        return response.strip()
    
    def transcribe_bytes(
        self,
        audio_data: bytes,
        filename: str = "audio.wav",
        language: Optional[str] = None
    ) -> str:
        """
        Transcribe audio data from bytes.
        
        Args:
            audio_data: Audio data as bytes
            filename: Filename hint for format detection
            language: Language code (optional)
        
        Returns:
            Transcribed text
        """
        # Create a file-like object
        audio_file = io.BytesIO(audio_data)
        audio_file.name = filename
        
        response = self.client.audio.transcriptions.create(
            model=self.model,
            file=audio_file,
            language=language or self.language,
            response_format="text"
        )
        
        return response.strip()
    
    def transcribe_numpy(
        self,
        audio_array: np.ndarray,
        sample_rate: int = 16000,
        language: Optional[str] = None
    ) -> str:
        """
        Transcribe audio from numpy array.
        
        Args:
            audio_array: Audio samples as numpy array (float32, mono)
            sample_rate: Sample rate in Hz
            language: Language code (optional)
        
        Returns:
            Transcribed text
        """
        # Convert to 16-bit PCM
        if audio_array.dtype == np.float32 or audio_array.dtype == np.float64:
            audio_int16 = (audio_array * 32767).astype(np.int16)
        else:
            audio_int16 = audio_array.astype(np.int16)
        
        # Create WAV in memory
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
        
        buffer.seek(0)
        buffer.name = "audio.wav"
        
        response = self.client.audio.transcriptions.create(
            model=self.model,
            file=buffer,
            language=language or self.language,
            response_format="text"
        )
        
        return response.strip()


class StreamingSpeechToText:
    """
    Streaming Speech-to-Text for real-time transcription.
    Buffers audio and transcribes when speech is detected.
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_duration: float = 0.5,  # seconds
        silence_threshold: float = 0.01,
        silence_duration: float = 1.0  # seconds of silence to trigger transcription
    ):
        self.stt = SpeechToText()
        self.sample_rate = sample_rate
        self.chunk_size = int(sample_rate * chunk_duration)
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.silence_chunks = int(silence_duration / chunk_duration)
        
        # Audio buffer
        self.audio_buffer: list[np.ndarray] = []
        self.silence_count = 0
        self.is_speaking = False
    
    def process_chunk(self, audio_chunk: np.ndarray) -> Optional[str]:
        """
        Process an audio chunk and return transcription if speech ended.
        
        Args:
            audio_chunk: Audio samples (float32)
        
        Returns:
            Transcribed text if speech ended, None otherwise
        """
        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio_chunk ** 2))
        
        if rms > self.silence_threshold:
            # Speech detected
            self.is_speaking = True
            self.silence_count = 0
            self.audio_buffer.append(audio_chunk)
        else:
            # Silence detected
            if self.is_speaking:
                self.audio_buffer.append(audio_chunk)
                self.silence_count += 1
                
                # Check if enough silence to end utterance
                if self.silence_count >= self.silence_chunks:
                    return self._transcribe_buffer()
        
        return None
    
    def _transcribe_buffer(self) -> str:
        """Transcribe the accumulated buffer and reset."""
        if not self.audio_buffer:
            return ""
        
        # Concatenate buffer
        full_audio = np.concatenate(self.audio_buffer)
        
        # Reset state
        self.audio_buffer = []
        self.silence_count = 0
        self.is_speaking = False
        
        # Transcribe
        try:
            return self.stt.transcribe_numpy(full_audio, self.sample_rate)
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""
    
    def force_transcribe(self) -> str:
        """Force transcription of current buffer."""
        return self._transcribe_buffer()
    
    def reset(self):
        """Reset the streaming state."""
        self.audio_buffer = []
        self.silence_count = 0
        self.is_speaking = False


# Convenience function
def transcribe(audio_path: str) -> str:
    """Quick transcription function."""
    stt = SpeechToText()
    return stt.transcribe_file(audio_path)


if __name__ == "__main__":
    # Test with a sample (requires audio file)
    print("Speech-to-Text Module")
    print("=====================")
    print("Available classes:")
    print("  - SpeechToText: File/bytes/numpy transcription")
    print("  - StreamingSpeechToText: Real-time streaming transcription")
