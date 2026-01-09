#!/usr/bin/env python3
"""
P6 Project Management Module.

Provides project navigation and management automation:
- Project tree traversal
- Open/close projects
- Project switching
- Multi-project handling
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
from ..exceptions import (
    P6ProjectNotFoundError,
    P6TimeoutError,
    P6WindowNotFoundError
)
from ..utils import (
    retry,
    wait_for_condition,
    sanitize_filename
)


class P6ProjectManager:
    """
    Manages P6 project navigation and operations.
    
    Provides:
    - Project tree traversal
    - Open/close projects by name
    - Switch between open projects
    - Project enumeration
    
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
            
            logger.info(f"✓ Found {sum(len(p) for p in tree.values())} projects in {len(tree)} EPS nodes")
            
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
    
    def open_project(self, project_name: str) -> bool:
        """
        Open a project by name.
        
        Args:
            project_name: Name of project to open
            
        Returns:
            True if opened successfully
            
        Raises:
            P6ProjectNotFoundError: If project not found
            ValueError: If project_name is empty
        """
        if not project_name or not project_name.strip():
            raise ValueError("project_name cannot be empty")
        
        logger.info(f"Opening project: {project_name}")
        
        try:
            self._window.set_focus()
            time.sleep(self.ACTION_DELAY)
            
            # Check if already open
            open_projects = self.get_open_projects()
            if project_name in open_projects:
                logger.info(f"Project already open, switching to: {project_name}")
                return self.switch_to_project(project_name)
            
            # Switch to projects view
            self._switch_to_projects_view()
            
            # Find project in tree
            if self._select_project_in_tree(project_name):
                # Double-click to open
                self._window.type_keys("{ENTER}")
                time.sleep(self.OPEN_TIMEOUT / 3)
                
                # Wait for project to open
                if self._wait_for_project_open(project_name):
                    self._current_project = project_name
                    logger.info(f"✓ Project opened: {project_name}")
                    return True
            
            raise P6ProjectNotFoundError(f"Project not found: {project_name}")
            
        except P6ProjectNotFoundError:
            raise
        except Exception as e:
            raise P6ProjectNotFoundError(f"Failed to open project: {e}")
    
    def _select_project_in_tree(self, project_name: str) -> bool:
        """Select a project in the tree control."""
        try:
            tree = self._window.child_window(control_type="Tree")
            
            # Use Ctrl+F to find
            self._window.type_keys("^F")
            time.sleep(self.ACTION_DELAY)
            
            # Type project name
            find_dialog = Desktop(backend="uia").window(title_re=".*Find.*")
            if find_dialog.exists():
                find_dialog.child_window(control_type="Edit").set_text(project_name)
                find_dialog.child_window(title="Find Next", control_type="Button").click_input()
                time.sleep(self.ACTION_DELAY)
                find_dialog.type_keys("{ESC}")
                return True
            
            # Fallback: try to select directly
            item = tree.get_item([project_name])
            if item:
                item.click_input()
                return True
                
        except Exception as e:
            logger.debug(f"Tree selection error: {e}")
        
        return False
    
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
        
        Args:
            project_name: Project to close (current if not specified)
            
        Returns:
            True if closed successfully
        """
        project_name = project_name or self.current_project
        
        if not project_name:
            logger.warning("No project to close")
            return False
        
        logger.info(f"Closing project: {project_name}")
        
        try:
            # Switch to project first
            if project_name != self.current_project:
                self.switch_to_project(project_name)
            
            # File -> Close
            self._window.menu_select("File->Close")
            time.sleep(self.ACTION_DELAY)
            
            # Handle save prompt if any
            self._handle_save_prompt(save=False)
            
            if self._current_project == project_name:
                self._current_project = None
            
            logger.info(f"✓ Project closed: {project_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to close project: {e}")
            return False
    
    def close_all_projects(self) -> bool:
        """
        Close all open projects.
        
        Returns:
            True if all closed successfully
        """
        logger.info("Closing all projects...")
        
        try:
            self._window.menu_select("File->Close All")
            time.sleep(self.ACTION_DELAY)
            
            # Handle any save prompts
            self._handle_save_prompt(save=False)
            
            self._current_project = None
            logger.info("✓ All projects closed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to close all projects: {e}")
            return False
    
    def _handle_save_prompt(self, save: bool = False):
        """Handle save changes prompt."""
        try:
            save_dialog = Desktop(backend="uia").window(
                title_re=".*Save.*|.*Changes.*"
            )
            
            if save_dialog.exists():
                if save:
                    save_dialog.child_window(title="Yes", control_type="Button").click_input()
                else:
                    save_dialog.child_window(title="No", control_type="Button").click_input()
                time.sleep(self.ACTION_DELAY)
                
        except Exception:
            pass
    
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
                    logger.info(f"✓ Switched to: {project_name}")
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
        
        # TODO: Read more info from project properties
        
        return info
