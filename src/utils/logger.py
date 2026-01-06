#!/usr/bin/env python3
"""
Logging Infrastructure
Configures structured logging with file and console output.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Import configuration
try:
    from src.config import LOG_FILE, LOG_LEVEL
except ImportError:
    # Fallback if running outside of package context
    LOG_FILE = Path('logs/app.log')
    LOG_LEVEL = 'INFO'

# ============================================================================
# LOGGER CONFIGURATION
# ============================================================================

def setup_logger(
    name: str = 'p6_integration',
    log_file: Optional[Path] = None,
    log_level: str = 'INFO',
    console_output: bool = True
) -> logging.Logger:
    """
    Configure and return a logger instance with file and console handlers.
    
    Args:
        name: Logger name
        log_file: Path to log file (default: from settings)
        log_level: Logging level (default: from settings)
        console_output: Whether to output to console (default: True)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Use settings defaults if not provided
    if log_file is None:
        log_file = LOG_FILE
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Prevent duplicate handlers if logger already configured
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # Capture all levels in file
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not create file handler: {e}", file=sys.stderr)
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger


# ============================================================================
# DEFAULT LOGGER INSTANCE
# ============================================================================

# Create default logger instance
logger = setup_logger(
    name='p6_integration',
    log_file=LOG_FILE,
    log_level=LOG_LEVEL,
    console_output=True
)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def sanitize_message(message: str, sensitive_data: list) -> str:
    """
    Sanitize log message by removing sensitive information.
    
    Args:
        message: The message to sanitize
        sensitive_data: List of sensitive strings to remove
        
    Returns:
        str: Sanitized message with sensitive data replaced by '***'
    """
    sanitized = message
    for data in sensitive_data:
        if data and str(data) in sanitized:
            sanitized = sanitized.replace(str(data), '***')
    return sanitized


def log_exception(logger_instance: logging.Logger, exception: Exception, sensitive_data: list = None):
    """
    Log an exception with sanitized message.
    
    Args:
        logger_instance: Logger instance to use
        exception: Exception to log
        sensitive_data: Optional list of sensitive strings to remove
    """
    if sensitive_data is None:
        sensitive_data = []
    
    error_msg = str(exception)
    sanitized_msg = sanitize_message(error_msg, sensitive_data)
    
    logger_instance.error(
        f"{type(exception).__name__}: {sanitized_msg}",
        exc_info=False  # Don't include full traceback to avoid leaking sensitive data
    )
