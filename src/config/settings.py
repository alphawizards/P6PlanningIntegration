#!/usr/bin/env python3
"""
Configuration Management Module
Loads and validates environment variables with fail-fast behavior.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# CRITICAL CONFIGURATION - FAIL FAST
# ============================================================================

def _get_required_env(var_name: str) -> str:
    """
    Get required environment variable with fail-fast validation.
    
    Args:
        var_name: Name of the environment variable
        
    Returns:
        str: Value of the environment variable
        
    Raises:
        ValueError: If the environment variable is not set or is empty
    """
    value = os.getenv(var_name, '').strip()
    if not value:
        raise ValueError(
            f"CRITICAL: Required environment variable '{var_name}' is not set or is empty. "
            f"Please configure it in the .env file."
        )
    return value


# ============================================================================
# CONNECTION MODE CONFIGURATION
# ============================================================================

# Connection mode: 'SQLITE' (local P6 Professional) or 'JAVA' (JPype Integration API)
P6_CONNECTION_MODE = os.getenv('P6_CONNECTION_MODE', 'SQLITE').strip().upper()

if P6_CONNECTION_MODE not in ['SQLITE', 'JAVA']:
    raise ValueError(
        f"CRITICAL: P6_CONNECTION_MODE must be 'SQLITE' or 'JAVA', got: {P6_CONNECTION_MODE}"
    )

# ============================================================================
# SQLITE CONFIGURATION (for P6 Professional Standalone)
# ============================================================================

P6_DB_PATH = os.getenv('P6_DB_PATH', '').strip()

if P6_CONNECTION_MODE == 'SQLITE':
    if not P6_DB_PATH:
        raise ValueError(
            "CRITICAL: P6_DB_PATH is required when P6_CONNECTION_MODE=SQLITE. "
            "Set it to the path of your P6 SQLite database (e.g., S32DB001.db)"
        )
    _db_path = Path(P6_DB_PATH)
    if not _db_path.exists():
        raise ValueError(
            f"CRITICAL: P6 SQLite database does not exist: {P6_DB_PATH}"
        )

# ============================================================================
# P6 LIBRARY CONFIGURATION (for Java Integration API mode)
# ============================================================================

P6_LIB_DIR = os.getenv('P6_LIB_DIR', '').strip()

if P6_CONNECTION_MODE == 'JAVA':
    if not P6_LIB_DIR:
        raise ValueError(
            "CRITICAL: P6_LIB_DIR is required when P6_CONNECTION_MODE=JAVA. "
            "Set it to the path containing P6 Integration API JAR files."
        )
    _lib_path = Path(P6_LIB_DIR)
    if not _lib_path.exists() or not _lib_path.is_dir():
        raise ValueError(
            f"CRITICAL: P6 library directory does not exist or is not a directory: {P6_LIB_DIR}"
        )

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Database type: 'standalone' (SQLite) or 'enterprise' (Oracle)
P6_DB_TYPE = os.getenv('P6_DB_TYPE', 'standalone').strip().lower()

if P6_DB_TYPE not in ['standalone', 'enterprise']:
    raise ValueError(
        f"CRITICAL: P6_DB_TYPE must be 'standalone' or 'enterprise', got: {P6_DB_TYPE}"
    )

# Database credentials (required for enterprise mode)
if P6_DB_TYPE == 'enterprise':
    DB_USER = _get_required_env('DB_USER')
    DB_PASS = _get_required_env('DB_PASS')
    DB_INSTANCE = os.getenv('DB_INSTANCE', '').strip()  # Optional database instance
else:
    # Standalone mode doesn't require database credentials
    DB_USER = None
    DB_PASS = None
    DB_INSTANCE = None

# ============================================================================
# P6 USER CREDENTIALS
# ============================================================================

P6_USER = _get_required_env('P6_USER')
P6_PASS = _get_required_env('P6_PASS')

# ============================================================================
# SAFETY CONFIGURATION
# ============================================================================

# SAFE_MODE: When True, prevents write operations to P6
# Default: True (fail-safe)
SAFE_MODE = os.getenv('SAFE_MODE', 'true').strip().lower() in ['true', '1', 'yes']

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Log directory
LOG_DIR = Path(__file__).parent.parent.parent / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Log file path
LOG_FILE = LOG_DIR / 'app.log'

# Log level
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').strip().upper()

# ============================================================================
# AI/LLM CONFIGURATION
# ============================================================================

# LLM Provider: anthropic, openai, gemini
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'anthropic').strip().lower()

if LLM_PROVIDER not in ['anthropic', 'openai', 'gemini']:
    raise ValueError(
        f"CRITICAL: LLM_PROVIDER must be 'anthropic', 'openai', or 'gemini', got: {LLM_PROVIDER}"
    )

# LLM API Key (optional - AI features disabled if not set)
LLM_API_KEY = os.getenv('LLM_API_KEY', '').strip()

# LLM Model
LLM_MODEL_DEFAULTS = {
    'anthropic': 'claude-3-5-sonnet-20241022',
    'openai': 'gpt-4-turbo-preview',
    'gemini': 'gemini-1.5-pro'
}
LLM_MODEL = os.getenv('LLM_MODEL', LLM_MODEL_DEFAULTS[LLM_PROVIDER]).strip()

# LLM Temperature (0.0 - 1.0)
LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.0'))

# LLM Max Tokens
LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', '4096'))

# AI Features Enabled (True if API key is set)
AI_ENABLED = bool(LLM_API_KEY)

# ============================================================================
# P6 GUI AUTOMATION CONFIGURATION
# ============================================================================

# Path to P6 Professional executable
P6_EXECUTABLE_PATH = os.getenv(
    'P6_EXECUTABLE_PATH',
    r'C:\Program Files\Oracle\Primavera P6\P6 Professional\PM.exe'
).strip()

# Default layout for printing
P6_DEFAULT_LAYOUT = os.getenv('P6_DEFAULT_LAYOUT', 'Standard Layout').strip()

# PDF printer name
PDF_PRINTER_NAME = os.getenv('PDF_PRINTER_NAME', 'Microsoft Print to PDF').strip()

# PDF output directory
PDF_OUTPUT_DIR = os.getenv('PDF_OUTPUT_DIR', 'reports/pdf').strip()

# ============================================================================
# CONFIGURATION SUMMARY
# ============================================================================

def print_config_summary():
    """Print a summary of the current configuration (without sensitive data)."""
    print("=" * 60)
    print("Configuration Summary")
    print("=" * 60)
    print(f"P6_CONNECTION_MODE: {P6_CONNECTION_MODE}")
    if P6_CONNECTION_MODE == 'SQLITE':
        print(f"P6_DB_PATH:    {P6_DB_PATH}")
    else:
        print(f"P6_LIB_DIR:    {P6_LIB_DIR}")
    print(f"P6_DB_TYPE:    {P6_DB_TYPE}")
    print(f"P6_USER:       {P6_USER}")
    print(f"SAFE_MODE:     {SAFE_MODE}")
    print(f"LOG_LEVEL:     {LOG_LEVEL}")
    print(f"LOG_FILE:      {LOG_FILE}")
    if P6_DB_TYPE == 'enterprise':
        print(f"DB_USER:       {DB_USER}")
        if DB_INSTANCE:
            print(f"DB_INSTANCE:   {DB_INSTANCE}")
    print(f"AI_ENABLED:    {AI_ENABLED}")
    if AI_ENABLED:
        print(f"LLM_PROVIDER:  {LLM_PROVIDER}")
        print(f"LLM_MODEL:     {LLM_MODEL}")
        print(f"LLM_TEMP:      {LLM_TEMPERATURE}")
    print("=" * 60)

