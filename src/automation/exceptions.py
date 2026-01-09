#!/usr/bin/env python3
"""
Custom exceptions for P6 GUI Automation.
"""


class P6AutomationError(Exception):
    """Base exception for P6 automation errors."""
    pass


class P6NotFoundError(P6AutomationError):
    """P6 Professional is not running or cannot be found."""
    pass


class P6ConnectionError(P6AutomationError):
    """Failed to connect to P6 Professional."""
    pass


class P6LoginError(P6AutomationError):
    """Failed to log in to P6."""
    pass


class P6WindowNotFoundError(P6AutomationError):
    """Expected P6 window or dialog not found."""
    pass


class P6TimeoutError(P6AutomationError):
    """Operation timed out waiting for P6 response."""
    pass


class P6ProjectNotFoundError(P6AutomationError):
    """Specified project not found in P6."""
    pass


class P6LayoutNotFoundError(P6AutomationError):
    """Specified layout not found in P6."""
    pass


class P6PrintError(P6AutomationError):
    """Failed to print or export from P6."""
    pass


class P6ExportError(P6AutomationError):
    """Failed to export data from P6."""
    pass


class P6ScheduleError(P6AutomationError):
    """Failed to schedule project in P6."""
    pass


class P6SafeModeError(P6AutomationError):
    """Operation blocked by safe mode."""
    pass
