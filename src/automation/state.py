#!/usr/bin/env python3
"""
P6 Application State Tracker.

Tracks the current state of P6 Professional:
- Which project is open
- Which view is active (Activities, Projects, WBS, etc.)
- Which layout is applied

Design: Read from P6 window when accuracy matters, cache for performance.
Per user discretion: "Implementation of P6 state tracking internals."
"""

import re
import time
from typing import Optional, Dict
from datetime import datetime

try:
    from pywinauto import Desktop
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

from src.utils import logger


class P6StateTracker:
    """
    Track P6 Professional application state.

    Reads state from the P6 window (title, tabs, controls) and
    provides cached access for performance. State is refreshed
    on demand or when staleness is suspected.

    Warning:
        This class is NOT thread-safe.
    """

    # Cache staleness threshold (seconds)
    CACHE_TTL = 5.0

    def __init__(self, main_window, navigator=None):
        """
        Initialize state tracker.

        Args:
            main_window: pywinauto window wrapper for P6 main window
            navigator: Optional P6Navigator instance for view detection
        """
        self._window = main_window
        self._navigator = navigator

        # Cached state
        self._cached_project: Optional[str] = None
        self._cached_view: Optional[str] = None
        self._cached_layout: Optional[str] = None
        self._last_refresh: Optional[datetime] = None

        logger.debug("P6StateTracker initialized")

    # =========================================================================
    # Current Project
    # =========================================================================

    def get_current_project(self, force_refresh: bool = False) -> Optional[str]:
        """
        Get the currently open project name.

        Args:
            force_refresh: If True, always read from window (ignore cache)

        Returns:
            Project name or None if no project is open
        """
        if not force_refresh and self._is_cache_fresh():
            return self._cached_project

        return self._read_project_from_window()

    def _read_project_from_window(self) -> Optional[str]:
        """
        Read current project from P6 window title.

        P6 window title patterns:
        - No project: "Primavera P6 Professional"
        - Project open: "Primavera P6 Professional - [ProjectName]"
        - Varies by version, use flexible regex
        """
        try:
            title = self._window.window_text()

            # Pattern 1: "Primavera P6 Professional 20 : ProjectID (Description)"
            match = re.search(r':\s*(\S+)\s*\(', title)
            if match:
                project = match.group(1).strip()
                self._cached_project = project
                self._last_refresh = datetime.now()
                return project

            # Pattern 2: "Primavera P6 ... - [ProjectName]"
            match = re.search(r'-\s*\[?([^\[\]-]+)\]?\s*$', title)
            if match:
                project = match.group(1).strip()
                self._cached_project = project
                self._last_refresh = datetime.now()
                return project

            # Pattern 3: anything after colon or dash separator
            for sep in [' : ', ' - ']:
                if sep in title:
                    remainder = title.split(sep, 1)[1].strip()
                    if remainder and "Primavera" not in remainder and "P6" not in remainder:
                        self._cached_project = remainder
                        self._last_refresh = datetime.now()
                        return remainder

            # No project detected
            self._cached_project = None
            self._last_refresh = datetime.now()
            return None

        except Exception as e:
            logger.debug(f"Could not read project from window title: {e}")
            return self._cached_project  # Return stale cache on error

    # =========================================================================
    # Current View
    # =========================================================================

    def get_current_view(self, force_refresh: bool = False) -> str:
        """
        Get the currently active view.

        Args:
            force_refresh: If True, always read from window

        Returns:
            View name: "Activities", "Projects", "WBS", "Resources", or "Unknown"
        """
        if not force_refresh and self._is_cache_fresh() and self._cached_view:
            return self._cached_view

        return self._read_view_from_window()

    def _read_view_from_window(self) -> str:
        """Read current view from P6 window."""
        # Prefer navigator if available
        if self._navigator:
            view = self._navigator.get_current_view()
            self._cached_view = view
            self._last_refresh = datetime.now()
            return view

        # Fallback: check tab control directly
        try:
            tab_control = self._window.child_window(control_type="Tab")
            if tab_control.exists():
                for tab in tab_control.children():
                    try:
                        if hasattr(tab, 'is_selected') and tab.is_selected():
                            name = tab.window_text()
                            if name:
                                self._cached_view = name
                                self._last_refresh = datetime.now()
                                return name
                    except Exception:
                        continue
        except Exception as e:
            logger.debug(f"Could not detect view from tabs: {e}")

        # Fallback: parse window title
        try:
            title = self._window.window_text()
            for view in ["Activities", "Projects", "WBS", "Resources", "Tracking"]:
                if view in title:
                    self._cached_view = view
                    self._last_refresh = datetime.now()
                    return view
        except Exception:
            pass

        self._cached_view = "Unknown"
        return "Unknown"

    def is_in_projects_view(self) -> bool:
        """Check if currently in Projects (EPS tree) view."""
        return self.get_current_view() == "Projects"

    def is_in_activities_view(self) -> bool:
        """Check if currently in Activities view."""
        return self.get_current_view() == "Activities"

    # =========================================================================
    # Current Layout
    # =========================================================================

    def get_current_layout(self) -> Optional[str]:
        """
        Get the currently applied layout name.

        Note: Layout detection is limited in P6. The layout name may appear
        in the window title or status bar, but this is version-dependent.
        Returns None if layout cannot be determined.

        Returns:
            Layout name or None if not detectable
        """
        # Strategy 1: Check window title for layout indicator
        try:
            title = self._window.window_text()
            # Some P6 versions show: "... - [Project] - LayoutName"
            parts = title.split(' - ')
            if len(parts) >= 3:
                potential_layout = parts[-1].strip()
                if potential_layout and "Primavera" not in potential_layout:
                    self._cached_layout = potential_layout
                    return potential_layout
        except Exception:
            pass

        # Strategy 2: Read from status bar (if navigator available)
        if self._navigator:
            try:
                status = self._navigator.read_status_bar()
                for key, value in status.items():
                    if 'layout' in key.lower() or 'layout' in str(value).lower():
                        self._cached_layout = value
                        return value
            except Exception:
                pass

        return self._cached_layout

    # =========================================================================
    # Combined State
    # =========================================================================

    def get_state(self, force_refresh: bool = False) -> Dict:
        """
        Get complete P6 application state.

        Args:
            force_refresh: If True, read all state from window

        Returns:
            Dict with current_project, current_view, current_layout, window_title
        """
        return {
            'current_project': self.get_current_project(force_refresh),
            'current_view': self.get_current_view(force_refresh),
            'current_layout': self.get_current_layout(),
            'window_title': self._get_window_title(),
            'timestamp': datetime.now().isoformat()
        }

    def set_project(self, project_name: Optional[str]):
        """
        Explicitly set the current project (after open/close operations).

        Called by P6ProjectManager after successful open/close to keep
        cache in sync without requiring a window read.

        Args:
            project_name: Project name or None if no project open
        """
        self._cached_project = project_name
        self._last_refresh = datetime.now()

    def set_view(self, view_name: str):
        """
        Explicitly set the current view.

        Args:
            view_name: View name
        """
        self._cached_view = view_name
        self._last_refresh = datetime.now()

    # =========================================================================
    # Internal
    # =========================================================================

    def _is_cache_fresh(self) -> bool:
        """Check if cached state is still fresh."""
        if not self._last_refresh:
            return False
        elapsed = (datetime.now() - self._last_refresh).total_seconds()
        return elapsed < self.CACHE_TTL

    def _get_window_title(self) -> str:
        """Get current window title safely."""
        try:
            return self._window.window_text()
        except Exception:
            return ""

    def __repr__(self) -> str:
        return (
            f"P6StateTracker("
            f"project={self._cached_project!r}, "
            f"view={self._cached_view!r}, "
            f"layout={self._cached_layout!r})"
        )
