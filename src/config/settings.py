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
# P6 LIBRARY CONFIGURATION
# ============================================================================

P6_LIB_DIR = _get_required_env('P6_LIB_DIR')

# Validate that the library directory exists
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
# CONFIGURATION SUMMARY
# ============================================================================

def print_config_summary():
    """Print a summary of the current configuration (without sensitive data)."""
    print("=" * 60)
    print("Configuration Summary")
    print("=" * 60)
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
    print("=" * 60)
