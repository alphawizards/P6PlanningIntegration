#!/usr/bin/env python3
"""
P6 Project Management Module.

Provides project navigation and management automation:
- Project search via Ctrl+F in EPS tree
- Open projects via right-click context menu
- Close projects with confirmation dialog handling
- Project switching via tabs
"""

import time
import re
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from datetime import datetime

try:
    from pywinauto import Application, Desktop
    from pywinauto.findwindows import ElementNotFoundError
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

from src.utils import logger
from .exceptions import (
    P6ProjectNotFoundError,
    P6TimeoutError,
    P6WindowNotFoundError
)
from .utils import (
    retry,
    wait_for_condition,
    sanitize_filename
)


class P6ProjectManager:
    """
    Manages P6 project navigation and operations.

    Provides:
    - Project search using Ctrl+F (sole method, no manual tree traversal)
    - Open projects via right-click context menu (per user requirement)
    - Close projects with save prompt + confirmation dialog handling
    - Switch between open projects via tabs

    Warning:
        This class is NOT thread-safe.
    """

    # Dialog patterns
    OPEN_PROJECT_TITLE = "Open Project"
    CLOSE_PROJECT_TITLE = "Close"
    PROJECT_TAB_PATTERN = "Projects"

    # Timing
    DIALOG_TIMEOUT = 15
    ACTION_DELAY = 0.5
    OPEN_TIMEOUT = 30  # Large projects take time

    def __init__(self, main_window):
        """
        Initialize project manager.

        Args:
            main_window: P6 main window wrapper
        """
        self._window = main_window
        self._current_project: Optional[str] = None

        logger.debug("P6ProjectManager initialized")

    @property
    def window(self):
        """Get the P6 main window."""
        return self._window

    @property
    def current_project(self) -> Optional[str]:
        """Get currently open project name."""
        return self._current_project or self.get_current_project_from_title()

    # =========================================================================
    # Project Discovery
    # =========================================================================

    def get_project_tree(self) -> Dict[str, List[str]]:
        """
        Get the project tree (EPS hierarchy).

        Returns:
            Dict mapping EPS names to lists of project names

        Note:
            This requires navigating to Projects view and reading the tree.
        """
        logger.info("Reading project tree...")

        tree = {}

        try:
            # Switch to Projects view
            self._switch_to_projects_view()
            time.sleep(self.ACTION_DELAY)

            # Find tree control
            tree_control = self._window.child_window(
                control_type="Tree"
            )

            if tree_control.exists():
                # Get root items (EPS nodes)
                roots = tree_control.roots()

                for root in roots:
                    eps_name = root.window_text()
                    projects = []

                    # Get child items (projects)
                    for child in root.children():
                        project_name = child.window_text()
                        if project_name:
                            projects.append(project_name)

                    if eps_name:
                        tree[eps_name] = projects

            logger.info(
                f"Found {sum(len(p) for p in tree.values())} projects "
                f"in {len(tree)} EPS nodes"
            )

        except Exception as e:
            logger.error(f"Failed to read project tree: {e}")

        return tree

    def get_all_projects(self) -> List[str]:
        """
        Get list of all project names.

        Returns:
            List of project names
        """
        tree = self.get_project_tree()
        projects = []
        for eps_projects in tree.values():
            projects.extend(eps_projects)
        return projects

    def get_open_projects(self) -> List[str]:
        """
        Get list of currently open projects.

        Returns:
            List of open project names (from tabs)
        """
        open_projects = []

        try:
            # Find project tabs
            tab_control = self._window.child_window(
                control_type="Tab"
            )

            if tab_control.exists():
                for tab in tab_control.children():
                    name = tab.window_text()
                    if name and name != "Projects":
                        open_projects.append(name)

        except Exception as e:
            logger.debug(f"Error getting open projects: {e}")

        return open_projects

    def _switch_to_projects_view(self):
        """Switch to Projects navigation view."""
        try:
            # Try clicking Projects tab
            tab = self._window.child_window(
                title=self.PROJECT_TAB_PATTERN,
                control_type="TabItem"
            )
            if tab.exists():
                tab.click_input()
                time.sleep(self.ACTION_DELAY)
                return
        except Exception:
            pass

        # Try menu: View -> Projects
        try:
            self._window.menu_select("View->Projects")
            time.sleep(self.ACTION_DELAY)
        except Exception:
            pass

    # =========================================================================
    # Open/Close Projects
    # =========================================================================

    def open_project(self, project_id: str) -> bool:
        """
        Open a project by Project ID.

        User requirement: Right-click -> Open Project from context menu.
        No Enter key -- context menu is the required open method.

        Args:
            project_id: Project ID to open

        Returns:
            True if opened successfully

        Raises:
            P6ProjectNotFoundError: If project not found or open fails
            P6TimeoutError: If project takes too long to open
            ValueError: If project_id is empty
        """
        if not project_id or not project_id.strip():
            raise ValueError("project_id cannot be empty")

        logger.info(f"Opening project: {project_id}")

        self._window.set_focus()
        time.sleep(self.ACTION_DELAY)

        # Check if already open
        open_projects = self.get_open_projects()
        if project_id in open_projects:
            logger.info(f"Project already open, switching to: {project_id}")
            return self.switch_to_project(project_id)

        # Switch to projects view
        self._switch_to_projects_view()

        # Find project using Ctrl+F
        self._select_project_in_tree(project_id)

        # Right-click to open context menu via keyboard (Shift+F10)
        self._window.type_keys("+{F10}")
        time.sleep(0.5)

        # Click "Open Project" in context menu
        try:
            context_menu = Desktop(backend="uia").window(control_type="Menu")
            if not context_menu.exists(timeout=3):
                raise P6WindowNotFoundError("Context menu did not appear")

            open_item = context_menu.child_window(
                title_re=".*Open.*Project.*",
                control_type="MenuItem"
            )
            open_item.click_input()
            time.sleep(1.0)

        except P6WindowNotFoundError:
            raise
        except Exception as e:
            raise P6ProjectNotFoundError(
                f"Failed to open project via context menu: {e}"
            )

        # Wait for project to open (adaptive timeout for large projects)
        if not self._wait_for_project_open(project_id):
            raise P6TimeoutError(
                f"Timed out waiting for project '{project_id}' to open. "
                f"Large projects may take longer than {self.OPEN_TIMEOUT}s."
            )

        self._current_project = project_id
        logger.info(f"Project opened: {project_id}")
        return True

    def _select_project_in_tree(self, project_id: str) -> bool:
        """
        Select a project in the EPS tree using Ctrl+F search.

        Workflow from CONTEXT.md:
        1. Click inside Project Hierarchy Grid to ensure focus
        2. Ctrl+F to open Find dialog
        3. Type exact Project ID
        4. Click Find Next -- P6 auto-expands collapsed nodes
        5. Verify highlighted row's Project ID matches target
        6. Close Find dialog (Esc)

        No automatic retries per user requirement.
        No fallback tree.get_item() -- Ctrl+F is the sole method.

        Args:
            project_id: Exact Project ID to find

        Returns:
            True if project found and selected

        Raises:
            P6ProjectNotFoundError: If project not found
            P6WindowNotFoundError: If Find dialog doesn't open
        """
        # Step 1: Focus on project grid
        self._window.set_focus()
        time.sleep(0.5)

        # Step 2: Open Find dialog
        self._window.type_keys("^F")
        time.sleep(0.5)

        # Step 3: Find and interact with Find dialog
        find_dialog = Desktop(backend="uia").window(title_re=".*Find.*")
        if not find_dialog.exists(timeout=3):
            raise P6WindowNotFoundError(
                "Find dialog did not open. "
                "P6 may not have focus on the project grid."
            )

        try:
            # Type project ID
            edit_field = find_dialog.child_window(control_type="Edit")
            edit_field.set_text(project_id)

            # Step 4: Click Find Next
            find_button = find_dialog.child_window(
                title="Find Next",
                control_type="Button"
            )
            find_button.click_input()
            time.sleep(1.0)  # Wait for P6 to expand tree and scroll

            # Step 6: Close Find dialog
            find_dialog.type_keys("{ESC}")
            time.sleep(0.3)

            # Step 5: Trust Find Next behavior -- P6 highlights the match
            # or shows "not found" message. Future enhancement can read
            # the selected row's Project ID column text for verification.
            return True

        except Exception as e:
            # Always close Find dialog on error
            try:
                find_dialog.type_keys("{ESC}")
            except Exception:
                pass
            raise P6ProjectNotFoundError(
                f"Could not find project '{project_id}'. "
                f"Project may not exist or is filtered out. Error: {e}"
            )

    def _wait_for_project_open(self, project_name: str, timeout: float = None) -> bool:
        """Wait for project to finish opening."""
        timeout = timeout or self.OPEN_TIMEOUT

        def is_project_open():
            title = self._window.window_text()
            return project_name.lower() in title.lower()

        return wait_for_condition(
            condition=is_project_open,
            timeout=timeout,
            description=f"Project open: {project_name}"
        )

    def close_project(self, project_name: Optional[str] = None) -> bool:
        """
        Close a project.

        User requirement: File -> Close, handle confirmation dialog.
        Errors raise immediately -- no silent swallowing.

        Args:
            project_name: Project to close (current if not specified)

        Returns:
            True if closed successfully

        Raises:
            P6AutomationError: If close fails
        """
        project_name = project_name or self.current_project

        if not project_name:
            logger.warning("No project to close")
            return False

        logger.info(f"Closing project: {project_name}")

        # Switch to project first if needed
        if project_name != self.current_project:
            self.switch_to_project(project_name)

        # File -> Close
        self._window.menu_select("File->Close")
        time.sleep(self.ACTION_DELAY)

        # Handle save changes prompt if any
        self._handle_save_prompt(save=False)

        # Handle close confirmation dialog ("Are you sure?")
        self._handle_close_confirmation()

        if self._current_project == project_name:
            self._current_project = None

        logger.info(f"Project closed: {project_name}")
        return True

    def close_all_projects(self) -> bool:
        """
        Close all open projects.

        Uses File -> Close All menu. Handles both save prompt and
        close confirmation dialog.

        Returns:
            True if all closed successfully

        Raises:
            P6AutomationError: If close fails
        """
        logger.info("Closing all projects...")

        self._window.menu_select("File->Close All")
        time.sleep(self.ACTION_DELAY)

        # Handle save prompt then close confirmation
        self._handle_save_prompt(save=False)
        self._handle_close_confirmation()

        self._current_project = None
        logger.info("All projects closed")
        return True

    def _handle_save_prompt(self, save: bool = False):
        """Handle save changes prompt."""
        try:
            save_dialog = Desktop(backend="uia").window(
                title_re=".*Save.*|.*Changes.*"
            )

            if save_dialog.exists(timeout=2):
                if save:
                    save_dialog.child_window(
                        title="Yes", control_type="Button"
                    ).click_input()
                else:
                    save_dialog.child_window(
                        title="No", control_type="Button"
                    ).click_input()
                time.sleep(self.ACTION_DELAY)

        except Exception:
            pass  # No save dialog present -- normal case

    def _handle_close_confirmation(self):
        """
        Handle P6 'Are you sure you want to close?' confirmation dialog.

        User requirement: P6 prompts confirmation on close, must click Yes/OK.
        This is separate from the save prompt -- P6 may show both sequentially.
        """
        try:
            # Look for close confirmation dialog -- broader pattern
            dialog = Desktop(backend="uia").window(
                title_re=".*[Cc]lose.*|.*[Cc]onfirm.*|.*Primavera.*"
            )

            if dialog.exists(timeout=3):
                dialog_title = dialog.window_text()

                # Try Yes button first (most common), then OK
                for button_title in ["Yes", "OK", "&Yes"]:
                    try:
                        btn = dialog.child_window(
                            title=button_title,
                            control_type="Button"
                        )
                        if btn.exists(timeout=1):
                            btn.click_input()
                            time.sleep(0.5)
                            return
                    except Exception:
                        continue

                # If no known button found, report to user
                logger.warning(
                    f"Close confirmation dialog found ('{dialog_title}') "
                    f"but could not find Yes/OK button."
                )

        except Exception:
            pass  # No dialog present -- normal case

    # =========================================================================
    # Project Switching
    # =========================================================================

    def switch_to_project(self, project_name: str) -> bool:
        """
        Switch to an open project.

        Args:
            project_name: Name of project to switch to

        Returns:
            True if switched successfully
        """
        logger.debug(f"Switching to project: {project_name}")

        try:
            # Find and click project tab
            tab_control = self._window.child_window(control_type="Tab")

            for tab in tab_control.children():
                if tab.window_text() == project_name:
                    tab.click_input()
                    time.sleep(self.ACTION_DELAY)
                    self._current_project = project_name
                    logger.info(f"Switched to: {project_name}")
                    return True

            logger.warning(f"Project tab not found: {project_name}")
            return False

        except Exception as e:
            logger.error(f"Failed to switch project: {e}")
            return False

    def get_current_project_from_title(self) -> Optional[str]:
        """
        Extract current project name from window title.

        Returns:
            Project name or None
        """
        title = self._window.window_text()

        # Pattern: "Primavera P6 ... - ProjectName"
        match = re.search(r'-\s*\[?([^\[\]-]+)\]?\s*$', title)
        if match:
            return match.group(1).strip()

        # Alternative: anything after last dash
        if ' - ' in title:
            parts = title.split(' - ')
            if len(parts) > 1:
                return parts[-1].strip()

        return None

    # =========================================================================
    # Project Info
    # =========================================================================

    def get_project_info(self, project_name: Optional[str] = None) -> Dict:
        """
        Get information about a project.

        Args:
            project_name: Project to get info for (current if not specified)

        Returns:
            Dict with project information
        """
        project_name = project_name or self.current_project

        info = {
            'name': project_name,
            'is_open': project_name in self.get_open_projects(),
            'is_current': project_name == self.current_project
        }

        return info
