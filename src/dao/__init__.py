"""Data Access Object package for P6 Planning Integration."""

# SQLite DAOs for P6 Professional Standalone (always available)
from .sqlite import (
    SQLiteManager,
    SQLiteProjectDAO,
    SQLiteActivityDAO,
    SQLiteRelationshipDAO,
)

# Java/JPype DAOs - only import if JPype is available
try:
    from .project_dao import ProjectDAO
    from .activity_dao import ActivityDAO
    from .relationship_dao import RelationshipDAO
    _JPYPE_AVAILABLE = True
except ImportError:
    # SQLite mode - JPype not needed
    _JPYPE_AVAILABLE = False
    ProjectDAO = None
    ActivityDAO = None
    RelationshipDAO = None

__all__ = [
    # SQLite DAOs (always available)
    'SQLiteManager',
    'SQLiteProjectDAO',
    'SQLiteActivityDAO',
    'SQLiteRelationshipDAO',
]

# Only export Java DAOs if available
if _JPYPE_AVAILABLE:
    __all__.extend([
        'ProjectDAO',
        'ActivityDAO',
        'RelationshipDAO',
    ])
