#!/usr/bin/env python3
"""
Whisper Voice Transcription Handler.

Per agents.md Phase 4:
"Implement a class WhisperTranscriber that:
1. Loads the Whisper model (use 'base' or 'small' model for speed) on initialization
2. Records audio from the microphone while the 'Record' button is held
3. Transcribes the audio locally using model.transcribe()
4. Returns the text string

CONSTRAINT: Do NOT use cloud APIs. Run locally."

Reference: https://github.com/filyp/whisper-simple-dictation.git

CRITICAL THREADING RULE (per agents.md):
"Whisper transcribe() is blocking. It MUST run in a separate thread daemon
so the Tkinter overlay (Main Thread) does not freeze."
"""

import os
import sys
import time
import wave
import tempfile
import threading
from typing import Optional, Callable
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

# Audio libraries
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("WARNING: pyaudio not installed. Run: pip install pyaudio")

# Whisper
try:
    import whisper
    import numpy as np
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("WARNING: whisper not installed. Run: pip install openai-whisper")

# Logging
try:
    from src.utils import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG)


class WhisperModel(Enum):
    """Available Whisper model sizes."""
    TINY = "tiny"       # ~39M params, fastest, lowest accuracy
    BASE = "base"       # ~74M params, good balance
    SMALL = "small"     # ~244M params, better accuracy
    MEDIUM = "medium"   # ~769M params, high accuracy
    LARGE = "large"     # ~1550M params, highest accuracy


@dataclass
class AudioConfig:
    """Audio recording configuration."""
    format: int = pyaudio.paInt16 if PYAUDIO_AVAILABLE else 8
    channels: int = 1
    sample_rate: int = 16000  # Whisper expects 16kHz
    chunk_size: int = 1024
    silence_threshold: int = 500
    silence_duration: float = 1.0  # seconds of silence to stop


class WhisperTranscriber:
    """
    Local Whisper-based voice transcription.

    Per agents.md:
    - Loads Whisper model locally
    - Records audio from microphone
    - Transcribes using model.transcribe()
    - Returns text string
    - All processing is LOCAL (no cloud APIs)

    Threading:
    - Recording runs in calling thread (but is non-blocking due to PyAudio)
    - Transcription should be called from a background thread

    Usage:
        transcriber = WhisperTranscriber()
        transcriber.load_model()  # Do this once, takes time

        transcriber.start_recording()
        # ... user speaks ...
        text = transcriber.stop_and_transcribe()  # Blocking call
    """

    def __init__(
        self,
        model_name: WhisperModel = WhisperModel.BASE,
        audio_config: Optional[AudioConfig] = None,
        language: str = "en"
    ):
        """
        Initialize transcriber.

        Args:
            model_name: Whisper model to use (default: BASE for speed/accuracy balance)
            audio_config: Audio recording settings
            language: Target language (default: English)
        """
        self.model_name = model_name
        self.audio_config = audio_config or AudioConfig()
        self.language = language

        # State
        self._model = None
        self._model_loaded = False
        self._is_recording = False
        self._audio_frames = []

        # PyAudio
        self._pyaudio = None
        self._stream = None

        # Threading
        self._recording_thread = None
        self._lock = threading.Lock()

        logger.info(f"WhisperTranscriber initialized (model={model_name.value})")

    def load_model(self, on_progress: Optional[Callable[[str], None]] = None):
        """
        Load the Whisper model.

        This is a blocking operation and should be called from a background thread
        or during initialization before the UI starts.

        Args:
            on_progress: Optional callback for progress updates
        """
        if self._model_loaded:
            logger.debug("Model already loaded")
            return

        logger.info(f"Loading Whisper model: {self.model_name.value}")

        if on_progress:
            on_progress(f"Loading Whisper {self.model_name.value} model...")

        if not WHISPER_AVAILABLE:
            raise RuntimeError(
                "Whisper not installed. Run: pip install openai-whisper\n"
                "Also ensure ffmpeg is installed on your system."
            )

        try:
            # Load model (downloads if not cached)
            self._model = whisper.load_model(self.model_name.value)
            self._model_loaded = True

            logger.info(f"Whisper model loaded: {self.model_name.value}")

            if on_progress:
                on_progress("Whisper model ready!")

        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise RuntimeError(f"Failed to load Whisper: {e}")

    def is_model_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model_loaded

    def start_recording(self):
        """
        Start recording audio from microphone.

        This is non-blocking - audio is captured in the background.
        Call stop_and_transcribe() to stop and get transcription.
        """
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError("PyAudio not installed")

        if self._is_recording:
            logger.warning("Already recording")
            return

        with self._lock:
            self._audio_frames = []
            self._is_recording = True

        # Initialize PyAudio
        if self._pyaudio is None:
            self._pyaudio = pyaudio.PyAudio()

        # Open stream
        try:
            self._stream = self._pyaudio.open(
                format=self.audio_config.format,
                channels=self.audio_config.channels,
                rate=self.audio_config.sample_rate,
                input=True,
                frames_per_buffer=self.audio_config.chunk_size,
                stream_callback=self._audio_callback
            )
            self._stream.start_stream()

            logger.debug("Recording started")

        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self._is_recording = False
            raise

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for non-blocking recording."""
        # FIX TS-001: Access _is_recording under lock to prevent race condition
        with self._lock:
            if self._is_recording:
                self._audio_frames.append(in_data)
        return (None, pyaudio.paContinue)

    def stop_recording(self) -> bytes:
        """
        Stop recording and return audio data.

        Returns:
            Raw audio bytes
        """
        # FIX TS-001: Set _is_recording under lock to prevent race condition
        with self._lock:
            self._is_recording = False

        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

        with self._lock:
            audio_data = b''.join(self._audio_frames)
            self._audio_frames = []

        logger.debug(f"Recording stopped: {len(audio_data)} bytes")
        return audio_data

    def stop_and_transcribe(self) -> str:
        """
        Stop recording and transcribe the audio.

        IMPORTANT: This is a BLOCKING call. Per agents.md, this MUST be
        called from a background thread to avoid freezing the UI.

        Returns:
            Transcribed text string
        """
        # Stop recording
        audio_data = self.stop_recording()

        if not audio_data:
            logger.warning("No audio data recorded")
            return ""

        # Transcribe
        return self.transcribe_audio(audio_data)

    def transcribe_audio(self, audio_data: bytes) -> str:
        """
        Transcribe audio data using Whisper.

        IMPORTANT: This is BLOCKING and CPU-intensive.
        Call from a background thread.

        Args:
            audio_data: Raw audio bytes (16-bit PCM, 16kHz, mono)

        Returns:
            Transcribed text
        """
        if not self._model_loaded:
            raise RuntimeError("Whisper model not loaded. Call load_model() first.")

        if not audio_data:
            return ""

        logger.debug("Starting transcription...")
        start_time = time.time()

        try:
            # Save to temp file (Whisper requires file input)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name

            # Write WAV file
            self._save_wav(audio_data, temp_path)

            # Transcribe
            result = self._model.transcribe(
                temp_path,
                language=self.language,
                fp16=False  # Use FP32 for CPU compatibility
            )

            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass

            text = result["text"].strip()
            elapsed = time.time() - start_time

            logger.info(f"Transcription complete ({elapsed:.2f}s): {text[:50]}...")
            return text

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    def _save_wav(self, audio_data: bytes, filepath: str):
        """Save audio data to WAV file."""
        with wave.open(filepath, 'wb') as wf:
            wf.setnchannels(self.audio_config.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.audio_config.sample_rate)
            wf.writeframes(audio_data)

    def transcribe_file(self, filepath: str) -> str:
        """
        Transcribe an audio file.

        Args:
            filepath: Path to audio file (WAV, MP3, etc.)

        Returns:
            Transcribed text
        """
        if not self._model_loaded:
            raise RuntimeError("Whisper model not loaded")

        logger.debug(f"Transcribing file: {filepath}")

        result = self._model.transcribe(
            filepath,
            language=self.language,
            fp16=False
        )

        return result["text"].strip()

    def cleanup(self):
        """Clean up resources."""
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()

        if self._pyaudio:
            self._pyaudio.terminate()

        logger.debug("WhisperTranscriber cleaned up")


# =============================================================================
# Threaded Wrapper for UI Integration
# =============================================================================

class AsyncWhisperTranscriber:
    """
    Thread-safe wrapper for WhisperTranscriber.

    Ensures all blocking operations run in background threads,
    keeping the UI responsive per agents.md requirements.
    """

    def __init__(
        self,
        model_name: WhisperModel = WhisperModel.BASE,
        on_model_loaded: Optional[Callable[[], None]] = None,
        on_transcription: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize async transcriber.

        Args:
            model_name: Whisper model to use
            on_model_loaded: Callback when model finishes loading
            on_transcription: Callback with transcribed text
            on_error: Callback on error
        """
        self._transcriber = WhisperTranscriber(model_name=model_name)

        self._on_model_loaded = on_model_loaded
        self._on_transcription = on_transcription
        self._on_error = on_error

        self._loading_thread = None
        self._transcription_thread = None

    def load_model_async(self):
        """Load model in background thread."""
        def load():
            try:
                self._transcriber.load_model()
                if self._on_model_loaded:
                    self._on_model_loaded()
            except Exception as e:
                if self._on_error:
                    self._on_error(str(e))

        self._loading_thread = threading.Thread(target=load, daemon=True)
        self._loading_thread.start()

    def start_recording(self):
        """Start recording (non-blocking)."""
        self._transcriber.start_recording()

    def stop_and_transcribe_async(self):
        """Stop and transcribe in background thread."""
        def transcribe():
            try:
                text = self._transcriber.stop_and_transcribe()
                if self._on_transcription:
                    self._on_transcription(text)
            except Exception as e:
                if self._on_error:
                    self._on_error(str(e))

        self._transcription_thread = threading.Thread(target=transcribe, daemon=True)
        self._transcription_thread.start()

    def is_model_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._transcriber.is_model_loaded()

    def cleanup(self):
        """Clean up resources."""
        self._transcriber.cleanup()


# =============================================================================
# Test Script
# =============================================================================

def test_whisper():
    """
    Test Whisper transcription.

    Per agents.md Verification:
    "Holding 'Record' captures voice and uses Whisper to transcribe accurately."
    """
    print("=" * 60)
    print("Whisper Transcriber Test")
    print("=" * 60)

    if not PYAUDIO_AVAILABLE:
        print("ERROR: pyaudio not installed")
        print("Run: pip install pyaudio")
        return

    if not WHISPER_AVAILABLE:
        print("ERROR: whisper not installed")
        print("Run: pip install openai-whisper")
        print("Also install ffmpeg on your system")
        return

    print("\nLoading Whisper model (this may take a minute)...")
    transcriber = WhisperTranscriber(model_name=WhisperModel.BASE)

    try:
        transcriber.load_model()
        print("Model loaded!")
    except Exception as e:
        print(f"Failed to load model: {e}")
        return

    print("\nRecording for 5 seconds...")
    print("Speak now!")

    transcriber.start_recording()
    time.sleep(5)

    print("\nTranscribing...")
    text = transcriber.stop_and_transcribe()

    print(f"\nTranscription: {text}")

    transcriber.cleanup()
    print("\nTest complete!")


if __name__ == "__main__":
    test_whisper()
