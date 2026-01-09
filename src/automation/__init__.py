"""
P6 Automation Module.
Provides GUI automation for Primavera P6 Professional.
"""

from .base import P6AutomationBase
from .p6_print_automation import P6PrintAutomation
from .connection import (
    P6ConnectionManager,
    detect_p6,
    is_p6_running,
    start_and_login
)
from .navigation import P6Navigator
from .printing import (
    P6PrintManager,
    PageOrientation,
    PageSize
)
from .exporting import (
    P6ExportManager,
    ExportFormat
)
from .projects import P6ProjectManager
from .layouts import (
    P6LayoutManager,
    P6View
)
from .scheduling import (
    P6ScheduleManager,
    P6BaselineManager,
    ScheduleOption
)
from .activities import P6ActivityManager
from .batch import (
    P6BatchProcessor,
    BatchStatus,
    BatchResult,
    BatchSummary
)
from .agent import (
    P6AgentInterface,
    ActionType,
    ActionResult
)
from .exceptions import (
    P6AutomationError,
    P6NotFoundError,
    P6ConnectionError,
    P6LoginError,
    P6WindowNotFoundError,
    P6TimeoutError,
    P6ProjectNotFoundError,
    P6LayoutNotFoundError,
    P6PrintError,
    P6ExportError,
    P6ScheduleError,
    P6SafeModeError
)

__all__ = [
    # Core classes
    'P6AutomationBase',
    'P6PrintAutomation',
    'P6ConnectionManager',
    'P6Navigator',
    'P6PrintManager',
    'P6ExportManager',
    'P6ProjectManager',
    'P6LayoutManager',
    'P6ScheduleManager',
    'P6BaselineManager',
    'P6ActivityManager',
    'P6BatchProcessor',
    'P6AgentInterface',
    # Enums & Data Classes
    'PageOrientation',
    'PageSize',
    'ExportFormat',
    'P6View',
    'ScheduleOption',
    'BatchStatus',
    'BatchResult',
    'BatchSummary',
    'ActionType',
    'ActionResult',
    # Convenience functions
    'detect_p6',
    'is_p6_running',
    'start_and_login',
    # Exceptions
    'P6AutomationError',
    'P6NotFoundError',
    'P6ConnectionError',
    'P6LoginError',
    'P6WindowNotFoundError',
    'P6TimeoutError',
    'P6ProjectNotFoundError',
    'P6LayoutNotFoundError',
    'P6PrintError',
    'P6ExportError',
    'P6ScheduleError',
    'P6SafeModeError'
]
