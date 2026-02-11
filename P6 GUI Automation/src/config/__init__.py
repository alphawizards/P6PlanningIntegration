#!/usr/bin/env python3
"""
P6 Voice Agent Configuration.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# =============================================================================
# SAFE MODE
# =============================================================================

# When True, prevents write operations to P6
SAFE_MODE = os.getenv('SAFE_MODE', 'true').lower() in ['true', '1', 'yes']

# =============================================================================
# WHISPER CONFIGURATION
# =============================================================================

# Whisper model: tiny, base, small, medium, large
WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'base')

# Language for transcription
WHISPER_LANGUAGE = os.getenv('WHISPER_LANGUAGE', 'en')

# =============================================================================
# LOGGING
# =============================================================================

LOG_DIR = Path(__file__).parent.parent.parent / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / 'voice_agent.log'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# =============================================================================
# P6 CONFIGURATION
# =============================================================================

# P6 window title pattern for detection
P6_WINDOW_PATTERN = os.getenv('P6_WINDOW_PATTERN', '.*Primavera P6.*')

# =============================================================================
# EXPORT CONFIGURATION
# =============================================================================

def print_config():
    """Print configuration summary."""
    print("P6 Voice Agent Configuration")
    print("=" * 40)
    print(f"SAFE_MODE:        {SAFE_MODE}")
    print(f"WHISPER_MODEL:    {WHISPER_MODEL}")
    print(f"WHISPER_LANGUAGE: {WHISPER_LANGUAGE}")
    print(f"LOG_FILE:         {LOG_FILE}")
    print(f"LOG_LEVEL:        {LOG_LEVEL}")
    print("=" * 40)
