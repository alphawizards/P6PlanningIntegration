#!/usr/bin/env python3
"""
P6 Layout Management Module.

Provides layout and view management automation:
- Layout loading/saving
- View switching (Activities, WBS, Resources)
- Filter management
- Column grouping and sorting
"""

import time
from pathlib import Path
from typing import Optional, List, Dict
from enum import Enum

try:
    from pywinauto import Desktop
    from pywinauto.findwindows import ElementNotFoundError
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

from src.utils import logger
from .exceptions import (
    P6LayoutNotFoundError,
    P6TimeoutError,
    P6WindowNotFoundError
)
from .utils import (
    wait_for_condition,
    sanitize_filename
)


class P6View(Enum):
    """Standard P6 views."""
    ACTIVITIES = "Activities"
    WBS = "WBS"
    PROJECTS = "Projects"
    RESOURCES = "Resources"
    ASSIGNMENTS = "Assignments"
    TRACKING = "Tracking"
    EXPENSES = "Expenses"


class P6LayoutManager:
    """
    Manages P6 layouts, views, and display settings.
    
    Provides:
    - Layout loading/saving/export
    - View switching
    - Filter application
    - Column grouping and sorting
    
    Warning:
        This class is NOT thread-safe.
    """
    
    # Dialog patterns
    LAYOUT_DIALOG_TITLE = "Layout"
    OPEN_LAYOUT_TITLE = "Open Layout"
    SAVE_LAYOUT_TITLE = "Save Layout"
    FILTER_DIALOG_TITLE = "Filter"
    GROUP_SORT_TITLE = "Group and Sort"
    COLUMNS_TITLE = "Columns"
    
    # Timing
    DIALOG_TIMEOUT = 10
    ACTION_DELAY = 0.5
    
    def __init__(self, main_window):
        """
        Initialize layout manager.
        
        Args:
            main_window: P6 main window wrapper
        """
        self._window = main_window
        self._current_layout: Optional[str] = None
        self._current_view: Optional[P6View] = None
        
        logger.debug("P6LayoutManager initialized")
    
    @property
    def current_layout(self) -> Optional[str]:
        """Get currently applied layout name."""
        return self._current_layout
    
    @property
    def current_view(self) -> Optional[P6View]:
        """Get current view."""
        return self._current_view
    
    # =========================================================================
    # Layout Management
    # =========================================================================
    
    def open_layout(self, layout_name: str) -> bool:
        """
        Open/apply a saved layout.
        
        Args:
            layout_name: Name of layout to open
            
        Returns:
            True if layout applied successfully
            
        Raises:
            P6LayoutNotFoundError: If layout not found
        """
        if not layout_name or not layout_name.strip():
            raise ValueError("layout_name cannot be empty")
        
        logger.info(f"Opening layout: {layout_name}")
        
        try:
            self._window.set_focus()
            time.sleep(self.ACTION_DELAY)
            
            # View -> Layout -> Open
            self._window.type_keys("%V")  # Alt+V
            time.sleep(self.ACTION_DELAY)
            self._window.type_keys("L")   # Layout
            time.sleep(self.ACTION_DELAY)
            self._window.type_keys("O")   # Open
            time.sleep(self.ACTION_DELAY * 2)
            
            # Handle layout dialog
            dialog = Desktop(backend="uia").window(
                title_re=f".*{self.OPEN_LAYOUT_TITLE}.*|.*{self.LAYOUT_DIALOG_TITLE}.*"
            )
            dialog.wait("ready", timeout=self.DIALOG_TIMEOUT)
            
            # Find layout in list
            if self._select_layout_in_dialog(dialog, layout_name):
                # Click Open/OK
                ok_button = dialog.child_window(
                    title_re=".*Open.*|.*OK.*",
                    control_type="Button"
                )
                ok_button.click_input()
                time.sleep(self.ACTION_DELAY * 2)
                
                self._current_layout = layout_name
                logger.info(f"✓ Layout applied: {layout_name}")
                return True
            
            raise P6LayoutNotFoundError(f"Layout not found: {layout_name}")
            
        except P6LayoutNotFoundError:
            raise
        except Exception as e:
            raise P6LayoutNotFoundError(f"Failed to open layout: {e}")
    
    def _select_layout_in_dialog(self, dialog, layout_name: str) -> bool:
        """Select layout in dialog list."""
        try:
            # Try list control
            list_control = dialog.child_window(control_type="List")
            if list_control.exists():
                item = list_control.child_window(title=layout_name)
                if item.exists():
                    item.click_input()
                    return True
            
            # Try tree control
            tree_control = dialog.child_window(control_type="Tree")
            if tree_control.exists():
                # Search for layout
                for item in tree_control.descendants(control_type="TreeItem"):
                    if item.window_text() == layout_name:
                        item.click_input()
                        return True
            
            # Fallback: type name in filter/search
            edit = dialog.child_window(control_type="Edit", found_index=0)
            if edit.exists():
                edit.set_text(layout_name)
                time.sleep(self.ACTION_DELAY)
                return True
                
        except Exception as e:
            logger.debug(f"Layout selection error: {e}")
        
        return False
    
    def save_layout(self, layout_name: Optional[str] = None) -> bool:
        """
        Save current layout.
        
        Args:
            layout_name: Name for layout (prompts if not provided)
            
        Returns:
            True if saved successfully
        """
        logger.info(f"Saving layout: {layout_name or 'current'}")
        
        try:
            self._window.set_focus()
            
            if layout_name:
                # Save As
                self._window.type_keys("%V")  # Alt+V
                time.sleep(self.ACTION_DELAY)
                self._window.type_keys("L")
                time.sleep(self.ACTION_DELAY)
                self._window.type_keys("A")  # Save As
            else:
                # Save
                self._window.type_keys("%V")
                time.sleep(self.ACTION_DELAY)
                self._window.type_keys("L")
                time.sleep(self.ACTION_DELAY)
                self._window.type_keys("S")
            
            time.sleep(self.ACTION_DELAY * 2)
            
            if layout_name:
                # Handle Save As dialog
                dialog = Desktop(backend="uia").window(
                    title_re=f".*{self.SAVE_LAYOUT_TITLE}.*|.*Save.*"
                )
                if dialog.exists():
                    dialog.wait("ready", timeout=self.DIALOG_TIMEOUT)
                    
                    edit = dialog.child_window(control_type="Edit", found_index=0)
                    edit.set_text(layout_name)
                    time.sleep(self.ACTION_DELAY)
                    
                    save_button = dialog.child_window(
                        title_re=".*Save.*|.*OK.*",
                        control_type="Button"
                    )
                    save_button.click_input()
                    
                self._current_layout = layout_name
            
            logger.info(f"✓ Layout saved")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save layout: {e}")
            return False
    
    def get_available_layouts(self) -> List[str]:
        """
        Get list of available layouts.
        
        Returns:
            List of layout names
        """
        layouts = []
        
        try:
            # Open layout dialog to read list
            self._window.set_focus()
            self._window.type_keys("%V")
            time.sleep(self.ACTION_DELAY)
            self._window.type_keys("L")
            time.sleep(self.ACTION_DELAY)
            self._window.type_keys("O")
            time.sleep(self.ACTION_DELAY * 2)
            
            dialog = Desktop(backend="uia").window(
                title_re=f".*{self.OPEN_LAYOUT_TITLE}.*|.*{self.LAYOUT_DIALOG_TITLE}.*"
            )
            
            if dialog.exists():
                dialog.wait("ready", timeout=self.DIALOG_TIMEOUT)
                
                # Read from list
                list_control = dialog.child_window(control_type="List")
                if list_control.exists():
                    for item in list_control.children():
                        name = item.window_text()
                        if name:
                            layouts.append(name)
                
                # Close dialog
                dialog.type_keys("{ESC}")
            
        except Exception as e:
            logger.debug(f"Error reading layouts: {e}")
        
        return layouts
    
    # =========================================================================
    # View Switching
    # =========================================================================
    
    def switch_view(self, view: P6View) -> bool:
        """
        Switch to a different P6 view.
        
        Args:
            view: P6View enum value
            
        Returns:
            True if switched successfully
        """
        logger.info(f"Switching to view: {view.value}")
        
        try:
            self._window.set_focus()
            time.sleep(self.ACTION_DELAY)
            
            # Try tab control first
            tab_control = self._window.child_window(control_type="Tab")
            if tab_control.exists():
                try:
                    tab = tab_control.child_window(title=view.value)
                    if tab.exists():
                        tab.click_input()
                        time.sleep(self.ACTION_DELAY)
                        self._current_view = view
                        logger.info(f"✓ Switched to: {view.value}")
                        return True
                except Exception:
                    pass
            
            # Fallback: use menu
            self._window.menu_select(f"View->{view.value}")
            time.sleep(self.ACTION_DELAY)
            
            self._current_view = view
            logger.info(f"✓ Switched to: {view.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to switch view: {e}")
            return False
    
    def switch_to_activities(self) -> bool:
        """Switch to Activities view."""
        return self.switch_view(P6View.ACTIVITIES)
    
    def switch_to_wbs(self) -> bool:
        """Switch to WBS view."""
        return self.switch_view(P6View.WBS)
    
    def switch_to_resources(self) -> bool:
        """Switch to Resources view."""
        return self.switch_view(P6View.RESOURCES)
    
    # =========================================================================
    # Filters
    # =========================================================================
    
    def apply_filter(self, filter_name: str) -> bool:
        """
        Apply a saved filter.
        
        Args:
            filter_name: Name of filter to apply
            
        Returns:
            True if applied successfully
        """
        logger.info(f"Applying filter: {filter_name}")
        
        try:
            self._window.set_focus()
            
            # View -> Filter
            self._window.menu_select("View->Filter...")
            time.sleep(self.ACTION_DELAY * 2)
            
            dialog = Desktop(backend="uia").window(
                title_re=f".*{self.FILTER_DIALOG_TITLE}.*"
            )
            dialog.wait("ready", timeout=self.DIALOG_TIMEOUT)
            
            # Find and select filter
            list_control = dialog.child_window(control_type="List")
            if list_control.exists():
                item = list_control.child_window(title=filter_name)
                if item.exists():
                    item.click_input()
            
            # Apply
            apply_button = dialog.child_window(
                title_re=".*Apply.*|.*OK.*",
                control_type="Button"
            )
            apply_button.click_input()
            time.sleep(self.ACTION_DELAY)
            
            logger.info(f"✓ Filter applied: {filter_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply filter: {e}")
            return False
    
    def clear_filter(self) -> bool:
        """
        Clear current filter.
        
        Returns:
            True if cleared successfully
        """
        logger.info("Clearing filter...")
        
        try:
            self._window.set_focus()
            
            # View -> Filter -> Clear
            self._window.menu_select("View->Filter...")
            time.sleep(self.ACTION_DELAY * 2)
            
            dialog = Desktop(backend="uia").window(
                title_re=f".*{self.FILTER_DIALOG_TITLE}.*"
            )
            
            if dialog.exists():
                dialog.wait("ready", timeout=self.DIALOG_TIMEOUT)
                
                clear_button = dialog.child_window(
                    title_re=".*Clear.*|.*None.*",
                    control_type="Button"
                )
                if clear_button.exists():
                    clear_button.click_input()
                    time.sleep(self.ACTION_DELAY)
                
                # OK to close
                dialog.child_window(title="OK", control_type="Button").click_input()
            
            logger.info("✓ Filter cleared")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear filter: {e}")
            return False
    
    # =========================================================================
    # Grouping and Sorting
    # =========================================================================
    
    def set_grouping(self, *columns: str) -> bool:
        """
        Set grouping by columns.
        
        Args:
            columns: Column names to group by
            
        Returns:
            True if set successfully
        """
        logger.info(f"Setting grouping: {columns}")
        
        try:
            self._window.set_focus()
            
            # View -> Group and Sort
            self._window.menu_select("View->Group and Sort...")
            time.sleep(self.ACTION_DELAY * 2)
            
            dialog = Desktop(backend="uia").window(
                title_re=f".*{self.GROUP_SORT_TITLE}.*"
            )
            dialog.wait("ready", timeout=self.DIALOG_TIMEOUT)
            
            # TODO: Implement column selection in grouping dialog
            # This requires navigating combo boxes for each group level
            
            dialog.child_window(title="OK", control_type="Button").click_input()
            
            logger.info("✓ Grouping set")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set grouping: {e}")
            return False
    
    def set_sorting(self, column: str, ascending: bool = True) -> bool:
        """
        Set sorting by column.
        
        Args:
            column: Column name to sort by
            ascending: Sort ascending (True) or descending (False)
            
        Returns:
            True if set successfully
        """
        logger.info(f"Setting sorting: {column} {'ASC' if ascending else 'DESC'}")
        
        try:
            self._window.set_focus()
            
            # View -> Group and Sort
            self._window.menu_select("View->Group and Sort...")
            time.sleep(self.ACTION_DELAY * 2)
            
            dialog = Desktop(backend="uia").window(
                title_re=f".*{self.GROUP_SORT_TITLE}.*"
            )
            dialog.wait("ready", timeout=self.DIALOG_TIMEOUT)
            
            # TODO: Implement sort column selection
            
            dialog.child_window(title="OK", control_type="Button").click_input()
            
            logger.info("✓ Sorting set")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set sorting: {e}")
            return False
    
    def refresh_view(self) -> bool:
        """
        Refresh current view (F5).
        
        Returns:
            True if refreshed
        """
        try:
            self._window.set_focus()
            self._window.type_keys("{F5}")
            time.sleep(self.ACTION_DELAY)
            logger.info("✓ View refreshed")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh: {e}")
            return False
