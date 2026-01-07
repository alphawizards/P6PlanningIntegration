"""Core package for P6 Planning Integration."""

# Schema definitions are always available (no JPype dependency)
from .definitions import (
    PROJECT_FIELDS,
    ACTIVITY_FIELDS,
    RESOURCE_FIELDS,
    RELATIONSHIP_FIELDS,
    validate_fields,
    get_fields,
)

# P6Session requires JPype - only import if available
try:
    from .session import P6Session
    _JPYPE_AVAILABLE = True
except ImportError:
    _JPYPE_AVAILABLE = False
    P6Session = None

__all__ = [
    'PROJECT_FIELDS',
    'ACTIVITY_FIELDS',
    'RESOURCE_FIELDS',
    'RELATIONSHIP_FIELDS',
    'validate_fields',
    'get_fields',
]

if _JPYPE_AVAILABLE:
    __all__.append('P6Session')

