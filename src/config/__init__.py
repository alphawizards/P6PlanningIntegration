"""Configuration package for P6 Planning Integration."""

from .settings import (
    P6_CONNECTION_MODE,
    P6_DB_PATH,
    P6_LIB_DIR,
    P6_DB_TYPE,
    DB_USER,
    DB_PASS,
    DB_INSTANCE,
    P6_USER,
    P6_PASS,
    SAFE_MODE,
    LOG_DIR,
    LOG_FILE,
    LOG_LEVEL,
    print_config_summary,
    # P6 GUI Automation
    P6_EXECUTABLE_PATH,
    P6_DEFAULT_LAYOUT,
    PDF_PRINTER_NAME,
    PDF_OUTPUT_DIR,
)

__all__ = [
    'P6_CONNECTION_MODE',
    'P6_DB_PATH',
    'P6_LIB_DIR',
    'P6_DB_TYPE',
    'DB_USER',
    'DB_PASS',
    'DB_INSTANCE',
    'P6_USER',
    'P6_PASS',
    'SAFE_MODE',
    'LOG_DIR',
    'LOG_FILE',
    'LOG_LEVEL',
    'print_config_summary',
    # P6 GUI Automation
    'P6_EXECUTABLE_PATH',
    'P6_DEFAULT_LAYOUT',
    'PDF_PRINTER_NAME',
    'PDF_OUTPUT_DIR',
]

