"""
Audio handler for real-time voice processing.
Manages microphone input, audio playback, and WebRTC streaming.
"""
import asyncio
import base64
import queue
import threading
from typing import Callable, Optional, AsyncGenerator
import numpy as np
import io

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class AudioConfig:
    """Audio configuration settings."""
    SAMPLE_RATE = 16000
    CHANNELS = 1
    CHUNK_DURATION = 0.5  # seconds
    CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)
    DTYPE = np.float32


class MicrophoneHandler:
    """
    Handle microphone input for voice capture.
    """
    
    def __init__(
        self,
        sample_rate: int = AudioConfig.SAMPLE_RATE,
        channels: int = AudioConfig.CHANNELS,
        chunk_size: int = AudioConfig.CHUNK_SIZE
    ):
        if not SOUNDDEVICE_AVAILABLE:
            raise ImportError("sounddevice is required for microphone handling")
        
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        
        self.audio_queue: queue.Queue = queue.Queue()
        self.is_recording = False
        self._stream = None
    
    def _audio_callback(self, indata, frames, time, status):
        """Callback for audio stream."""
        if status:
            logger.warning(f"Audio status: {status}")
        self.audio_queue.put(indata.copy())
    
    def start_recording(self):
        """Start recording from microphone."""
        if self.is_recording:
            return
        
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=AudioConfig.DTYPE,
            blocksize=self.chunk_size,
            callback=self._audio_callback
        )
        self._stream.start()
        self.is_recording = True
        logger.info("Microphone recording started")
    
    def stop_recording(self):
        """Stop recording."""
        if not self.is_recording:
            return
        
        self.is_recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        logger.info("Microphone recording stopped")
    
    def get_audio_chunk(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """Get the next audio chunk from the queue."""
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def clear_queue(self):
        """Clear the audio queue."""
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break


class AudioPlayer:
    """
    Handle audio playback.
    """
    
    def __init__(
        self,
        sample_rate: int = AudioConfig.SAMPLE_RATE,
        channels: int = AudioConfig.CHANNELS
    ):
        if not SOUNDDEVICE_AVAILABLE:
            raise ImportError("sounddevice is required for audio playback")
        
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_playing = False
    
    def play_bytes(self, audio_data: bytes, format: str = "mp3"):
        """
        Play audio from bytes.
        
        Args:
            audio_data: Audio data as bytes
            format: Audio format (mp3, wav)
        """
        if not SOUNDFILE_AVAILABLE:
            logger.warning("soundfile not available for playback")
            return
        
        # Read audio from bytes
        audio_io = io.BytesIO(audio_data)
        data, sample_rate = sf.read(audio_io)
        
        # Play
        self.is_playing = True
        sd.play(data, sample_rate)
        sd.wait()
        self.is_playing = False
    
    def play_array(self, audio_array: np.ndarray, sample_rate: Optional[int] = None):
        """
        Play audio from numpy array.
        
        Args:
            audio_array: Audio samples
            sample_rate: Sample rate (uses default if not specified)
        """
        sr = sample_rate or self.sample_rate
        self.is_playing = True
        sd.play(audio_array, sr)
        sd.wait()
        self.is_playing = False
    
    async def play_stream(self, audio_chunks: AsyncGenerator[bytes, None]):
        """
        Play streaming audio chunks.
        
        Args:
            audio_chunks: Async generator yielding audio chunks
        """
        buffer = io.BytesIO()
        
        async for chunk in audio_chunks:
            buffer.write(chunk)
        
        buffer.seek(0)
        if SOUNDFILE_AVAILABLE:
            data, sample_rate = sf.read(buffer)
            self.is_playing = True
            sd.play(data, sample_rate)
            sd.wait()
            self.is_playing = False
    
    def stop(self):
        """Stop current playback."""
        sd.stop()
        self.is_playing = False


class WebAudioHandler:
    """
    Handle audio for web-based interfaces.
    Converts between web audio formats and numpy arrays.
    """
    
    @staticmethod
    def base64_to_numpy(
        base64_audio: str,
        sample_rate: int = AudioConfig.SAMPLE_RATE
    ) -> np.ndarray:
        """
        Convert base64 audio to numpy array.
        
        Args:
            base64_audio: Base64 encoded audio data
            sample_rate: Expected sample rate
        
        Returns:
            Audio samples as numpy array
        """
        audio_bytes = base64.b64decode(base64_audio)
        audio_io = io.BytesIO(audio_bytes)
        
        if SOUNDFILE_AVAILABLE:
            data, sr = sf.read(audio_io)
            return data.astype(np.float32)
        else:
            # Fallback: assume raw PCM float32
            return np.frombuffer(audio_bytes, dtype=np.float32)
    
    @staticmethod
    def numpy_to_base64(
        audio_array: np.ndarray,
        sample_rate: int = AudioConfig.SAMPLE_RATE,
        format: str = "wav"
    ) -> str:
        """
        Convert numpy array to base64 audio.
        
        Args:
            audio_array: Audio samples
            sample_rate: Sample rate
            format: Output format (wav, mp3)
        
        Returns:
            Base64 encoded audio
        """
        buffer = io.BytesIO()
        
        if SOUNDFILE_AVAILABLE:
            sf.write(buffer, audio_array, sample_rate, format=format)
        else:
            # Fallback: raw PCM
            buffer.write(audio_array.tobytes())
        
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode('utf-8')
    
    @staticmethod
    def mp3_to_base64(audio_bytes: bytes) -> str:
        """Convert MP3 bytes to base64 string."""
        return base64.b64encode(audio_bytes).decode('utf-8')
    
    @staticmethod
    def base64_to_mp3(base64_audio: str) -> bytes:
        """Convert base64 string to MP3 bytes."""
        return base64.b64decode(base64_audio)


class VoicePipeline:
    """
    Complete voice-to-voice pipeline.
    Combines STT -> Agent -> TTS.
    """
    
    def __init__(
        self,
        on_transcription: Optional[Callable[[str], None]] = None,
        on_response: Optional[Callable[[str], None]] = None
    ):
        from src.voice.speech_to_text import StreamingSpeechToText
        from src.voice.text_to_speech import get_tts
        from src.agent.orchestrator import get_agent
        
        self.stt = StreamingSpeechToText()
        self.tts = get_tts()
        self.agent = get_agent()
        
        self.mic = None
        self.player = None
        
        if SOUNDDEVICE_AVAILABLE:
            self.mic = MicrophoneHandler()
            self.player = AudioPlayer()
        
        self.on_transcription = on_transcription
        self.on_response = on_response
        
        self.is_running = False
    
    def process_audio_chunk(self, audio_chunk: np.ndarray) -> Optional[bytes]:
        """
        Process an audio chunk through the full pipeline.
        
        Returns:
            Response audio if transcription completed, None otherwise
        """
        # Try to get transcription
        text = self.stt.process_chunk(audio_chunk)
        
        if text:
            if self.on_transcription:
                self.on_transcription(text)
            
            # Get agent response
            result = self.agent.process_message(text)
            response_text = result["response"]
            
            if self.on_response:
                self.on_response(response_text)
            
            # Synthesize response
            audio = self.tts.synthesize(response_text)
            return audio
        
        return None
    
    def run_interactive(self):
        """Run interactive voice loop."""
        if not self.mic or not self.player:
            raise RuntimeError("Audio devices not available")
        
        print("Voice pipeline started. Speak into your microphone...")
        print("Press Ctrl+C to stop.\n")
        
        self.is_running = True
        self.mic.start_recording()
        
        try:
            while self.is_running:
                # Get audio chunk
                chunk = self.mic.get_audio_chunk(timeout=1.0)
                if chunk is None:
                    continue
                
                # Process through pipeline
                response_audio = self.process_audio_chunk(chunk.flatten())
                
                if response_audio:
                    # Play response
                    self.mic.stop_recording()  # Pause mic during playback
                    self.player.play_bytes(response_audio)
                    self.mic.start_recording()  # Resume mic
        
        except KeyboardInterrupt:
            print("\nStopping voice pipeline...")
        finally:
            self.mic.stop_recording()
            self.is_running = False
    
    def stop(self):
        """Stop the voice pipeline."""
        self.is_running = False
        if self.mic:
            self.mic.stop_recording()


if __name__ == "__main__":
    print("Audio Handler Module")
    print("====================")
    print(f"sounddevice available: {SOUNDDEVICE_AVAILABLE}")
    print(f"soundfile available: {SOUNDFILE_AVAILABLE}")
    print("\nAvailable classes:")
    print("  - MicrophoneHandler: Microphone input")
    print("  - AudioPlayer: Audio playback")
    print("  - WebAudioHandler: Web audio conversion")
    print("  - VoicePipeline: Full voice-to-voice pipeline")
