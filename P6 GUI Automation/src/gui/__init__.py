#!/usr/bin/env python3
"""
P6 GUI Package - Voice Interface.

Provides the overlay window and voice handling (Layer 3: "The Ears").
"""

from .overlay import P6VoiceOverlay
from .whisper_handler import WhisperTranscriber

__all__ = ['P6VoiceOverlay', 'WhisperTranscriber']
