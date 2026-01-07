"""Utility package for P6 Planning Integration."""

from .logger import logger, setup_logger, sanitize_message, log_exception
from .file_manager import (
    ensure_directory,
    get_export_path,
    get_timestamped_filename,
    cleanup_old_exports,
)

# Converters require JPype - only import if available (Java mode)
try:
    from .converters import (
        java_date_to_python,
        java_value_to_python,
        p6_iterator_to_list,
        p6_objects_to_dict_list,
    )
    _JPYPE_AVAILABLE = True
except ImportError:
    # SQLite mode - JPype not needed
    _JPYPE_AVAILABLE = False
    java_date_to_python = None
    java_value_to_python = None
    p6_iterator_to_list = None
    p6_objects_to_dict_list = None

__all__ = [
    'logger',
    'setup_logger',
    'sanitize_message',
    'log_exception',
    'ensure_directory',
    'get_export_path',
    'get_timestamped_filename',
    'cleanup_old_exports',
]

# Only export converter functions if JPype is available
if _JPYPE_AVAILABLE:
    __all__.extend([
        'java_date_to_python',
        'java_value_to_python',
        'p6_iterator_to_list',
        'p6_objects_to_dict_list',
    ])

