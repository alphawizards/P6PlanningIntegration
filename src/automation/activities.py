#!/usr/bin/env python3
"""
P6 Activities Module.

Provides activity interaction automation:
- Activity selection and navigation
- Activity editing
- Activity data extraction
"""

import time
import re
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    from pywinauto import Desktop
    from pywinauto.findwindows import ElementNotFoundError
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

from src.utils import logger
from .exceptions import (
    P6TimeoutError,
    P6SafeModeError
)
from .utils import wait_for_condition, immediate_click, immediate_type


class P6ActivityManager:
    """
    Manages P6 activity interactions.
    
    Provides:
    - Activity selection by ID or criteria
    - Activity data reading
    - Activity editing (with safe mode)
    - Navigation within activity grid
    
    Warning:
        This class is NOT thread-safe.
        Edit operations require safe_mode=False.
    """
    
    # Timing
    DIALOG_TIMEOUT = 10
    ACTION_DELAY = 0.3
    
    def __init__(self, main_window, safe_mode: bool = True):
        """
        Initialize activity manager.
        
        Args:
            main_window: P6 main window wrapper
            safe_mode: Prevent destructive operations
        """
        self._window = main_window
        self.safe_mode = safe_mode
        self._selected_activities: List[str] = []
        
        logger.debug(f"P6ActivityManager initialized (safe_mode={safe_mode})")
    
    def _check_safe_mode(self, operation: str):
        """Check if operation is blocked by safe mode."""
        if self.safe_mode:
            raise P6SafeModeError(
                f"'{operation}' blocked by SAFE_MODE. "
                f"Set safe_mode=False to enable activity editing."
            )
    
    # =========================================================================
    # Activity Selection
    # =========================================================================
    
    def select_activity(self, activity_id: str) -> bool:
        """
        Select a single activity by ID.
        
        Args:
            activity_id: Activity ID to select
            
        Returns:
            True if activity found and selected
        """
        logger.debug(f"Selecting activity: {activity_id}")
        
        try:
            self._window.set_focus()
            time.sleep(self.ACTION_DELAY)
            
            # Use Ctrl+F to find
            self._window.type_keys("^F")
            time.sleep(self.ACTION_DELAY)
            
            find_dialog = Desktop(backend="uia").window(title_re=".*Find.*")
            if find_dialog.exists():
                find_dialog.wait("ready", timeout=self.DIALOG_TIMEOUT)
                
                # Enter activity ID
                edit = find_dialog.child_window(control_type="Edit", found_index=0)
                edit.set_text(activity_id)
                time.sleep(self.ACTION_DELAY)
                
                # Find Next
                find_button = find_dialog.child_window(
                    title_re=".*Find.*Next.*",
                    control_type="Button"
                )
                find_button.click_input()
                time.sleep(self.ACTION_DELAY)
                
                # Close find dialog
                find_dialog.type_keys("{ESC}")
                
                self._selected_activities = [activity_id]
                logger.info(f"✓ Selected activity: {activity_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to select activity: {e}")
            return False
    
    def select_activities(self, activity_ids: List[str]) -> int:
        """
        Select multiple activities.
        
        Args:
            activity_ids: List of activity IDs to select
            
        Returns:
            Number of activities successfully selected
        """
        logger.info(f"Selecting {len(activity_ids)} activities")
        
        count = 0
        for i, activity_id in enumerate(activity_ids):
            try:
                if i == 0:
                    success = self.select_activity(activity_id)
                else:
                    # Ctrl+Click for multi-select (using Find)
                    success = self._add_to_selection(activity_id)
                
                if success:
                    count += 1
                    
            except Exception as e:
                logger.debug(f"Could not select {activity_id}: {e}")
        
        self._selected_activities = activity_ids[:count]
        logger.info(f"✓ Selected {count}/{len(activity_ids)} activities")
        return count
    
    def _add_to_selection(self, activity_id: str) -> bool:
        """Add activity to current selection."""
        # This is tricky in P6 - typically need to:
        # 1. Find the activity
        # 2. Ctrl+Click to add to selection
        # For now, use Find dialog
        return self.select_activity(activity_id)
    
    def select_all(self) -> bool:
        """
        Select all activities (Ctrl+A).
        
        Returns:
            True if successful
        """
        try:
            self._window.set_focus()
            self._window.type_keys("^A")
            time.sleep(self.ACTION_DELAY)
            logger.info("✓ Selected all activities")
            return True
        except Exception as e:
            logger.error(f"Failed to select all: {e}")
            return False
    
    def clear_selection(self) -> bool:
        """
        Clear activity selection.
        
        Returns:
            True if cleared
        """
        try:
            self._window.set_focus()
            self._window.type_keys("{ESC}")
            self._selected_activities = []
            return True
        except Exception:
            return False
    
    def get_selected_activities(self) -> List[str]:
        """
        Get list of currently selected activity IDs.
        
        Returns:
            List of activity IDs
        """
        return self._selected_activities.copy()
    
    # =========================================================================
    # Activity Navigation  
    # =========================================================================
    
    def go_to_activity(self, activity_id: str) -> bool:
        """
        Navigate to a specific activity.
        
        Args:
            activity_id: Activity ID to navigate to
            
        Returns:
            True if navigated successfully
        """
        # Same as select, but ensures activity is visible
        return self.select_activity(activity_id)
    
    def go_to_first(self) -> bool:
        """Navigate to first activity."""
        try:
            self._window.set_focus()
            self._window.type_keys("^{HOME}")
            return True
        except Exception:
            return False
    
    def go_to_last(self) -> bool:
        """Navigate to last activity."""
        try:
            self._window.set_focus()
            self._window.type_keys("^{END}")
            return True
        except Exception:
            return False
    
    def move_up(self, count: int = 1) -> bool:
        """Move selection up."""
        try:
            self._window.set_focus()
            for _ in range(count):
                self._window.type_keys("{UP}")
            return True
        except Exception:
            return False
    
    def move_down(self, count: int = 1) -> bool:
        """Move selection down."""
        try:
            self._window.set_focus()
            for _ in range(count):
                self._window.type_keys("{DOWN}")
            return True
        except Exception:
            return False
    
    # =========================================================================
    # Activity Data
    # =========================================================================
    
    def get_activity_count(self) -> Optional[int]:
        """
        Get total activity count from status bar.
        
        Returns:
            Activity count or None
        """
        try:
            status_bar = self._window.child_window(control_type="StatusBar")
            if status_bar.exists():
                text = status_bar.window_text()
                # Look for pattern like "Activities: 1,234"
                match = re.search(r'Activities?:?\s*([\d,]+)', text, re.IGNORECASE)
                if match:
                    return int(match.group(1).replace(',', ''))
        except Exception:
            pass
        return None
    
    def get_visible_columns(self) -> List[str]:
        """
        Get list of visible column headers.
        
        Returns:
            List of column names
        """
        columns = []
        
        try:
            # Find header row in grid
            header = self._window.child_window(control_type="Header")
            if header.exists():
                for item in header.children():
                    name = item.window_text()
                    if name:
                        columns.append(name)
        except Exception as e:
            logger.debug(f"Error getting columns: {e}")
        
        return columns
    
    # =========================================================================
    # Details Pane Helpers
    # =========================================================================

    def _get_details_pane(self):
        """
        Locate the Activity Details bottom pane.

        Returns:
            Details pane wrapper, or None if not found.
        """
        try:
            # The details pane is typically a Pane control below the activity grid
            pane = self._window.child_window(
                title_re=".*Detail.*|.*Activity Detail.*",
                control_type="Pane"
            )
            if pane.exists():
                return pane
        except Exception as e:
            logger.debug(f"Details pane not found: {e}")
        # Fallback: return the main window itself for child searches
        return self._window

    def _select_details_tab(self, tab_name: str) -> bool:
        """
        Select a tab in the Activity Details pane.

        Args:
            tab_name: Tab name (e.g. 'General', 'Status', 'Resources')

        Returns:
            True if tab selected
        """
        try:
            details_pane = self._get_details_pane()
            tab_control = details_pane.child_window(control_type="TabControl")
            if tab_control.exists():
                tab_item = tab_control.child_window(title=tab_name)
                tab_item.click_input()
                time.sleep(self.ACTION_DELAY)
                logger.debug(f"Selected details tab: {tab_name}")
                return True
        except Exception as e:
            logger.debug(f"Could not select details tab '{tab_name}': {e}")
        return False

    # =========================================================================
    # Activity Editing
    # =========================================================================

    def edit_activity_field(
        self,
        activity_id: str,
        field_name: str,
        value: Any
    ) -> bool:
        """
        Edit a field value for an activity.
        
        Args:
            activity_id: Activity ID to edit
            field_name: Column/field name
            value: New value
            
        Returns:
            True if edited successfully
        """
        self._check_safe_mode("Edit Activity")
        
        logger.info(f"Editing {activity_id}.{field_name} = {value}")
        
        try:
            # Select the activity
            if not self.select_activity(activity_id):
                return False
            
            # Navigate to field (Tab through columns)
            # This is simplified - would need column position lookup
            
            # Enter edit mode
            self._window.type_keys("{F2}")
            time.sleep(self.ACTION_DELAY)
            
            # Type new value
            self._window.type_keys(str(value))
            time.sleep(self.ACTION_DELAY)
            
            # Confirm
            self._window.type_keys("{ENTER}")
            time.sleep(self.ACTION_DELAY)
            
            logger.info(f"✓ Activity edited: {activity_id}")
            return True
            
        except P6SafeModeError:
            raise
        except Exception as e:
            logger.error(f"Failed to edit activity: {e}")
            return False
    
    def create_activity(
        self,
        activity_name: str,
        duration: int,
        wbs_node: Optional[str] = None,
        activity_type: Optional[str] = None,
        calendar: Optional[str] = None
    ) -> bool:
        """
        Create a new activity with specified properties.

        Args:
            activity_name: Name for the new activity
            duration: Remaining duration in days
            wbs_node: Optional WBS node to create activity under
            activity_type: Optional activity type (e.g. 'Task Dependent')
            calendar: Optional calendar assignment

        Returns:
            True if activity created successfully
        """
        self._check_safe_mode("Create Activity")

        logger.info(f"Creating activity: '{activity_name}' (duration={duration})")

        try:
            self._window.set_focus()
            time.sleep(self.ACTION_DELAY)

            # Navigate to WBS node if specified
            if wbs_node:
                logger.debug(f"Navigating to WBS node: {wbs_node}")
                self._window.type_keys("^F")
                time.sleep(self.ACTION_DELAY)

                find_dialog = Desktop(backend="uia").window(title_re=".*Find.*")
                if find_dialog.exists():
                    find_dialog.wait("ready", timeout=self.DIALOG_TIMEOUT)

                    edit = find_dialog.child_window(control_type="Edit", found_index=0)
                    edit.set_text(wbs_node)
                    time.sleep(self.ACTION_DELAY)

                    find_button = find_dialog.child_window(
                        title_re=".*Find.*Next.*",
                        control_type="Button"
                    )
                    find_button.click_input()
                    time.sleep(self.ACTION_DELAY)

                    find_dialog.type_keys("{ESC}")
                    time.sleep(self.ACTION_DELAY)
                else:
                    logger.error(f"Find dialog not found; cannot navigate to WBS '{wbs_node}'")
                    return False

            # Insert new activity
            self._window.type_keys("{INSERT}")
            time.sleep(self.ACTION_DELAY * 2)

            # Fill Activity Name (newly inserted row should be in edit mode)
            self._window.type_keys(activity_name, with_spaces=True)
            self._window.type_keys("{ENTER}")
            time.sleep(self.ACTION_DELAY)

            # Fill Duration via Details Form Status tab
            if duration and duration > 0:
                self._select_details_tab("Status")

                details_pane = self._get_details_pane()
                if details_pane:
                    try:
                        dur_field = details_pane.child_window(
                            title_re=".*Remaining.*Dur.*",
                            control_type="Edit"
                        )
                        dur_field.set_text("")
                        dur_field.type_keys(str(duration), with_spaces=True)
                        dur_field.type_keys("{ENTER}")
                        time.sleep(self.ACTION_DELAY)
                        logger.debug(f"Set duration: {duration}")
                    except Exception as e:
                        logger.warning(f"Could not set duration: {e}")

            # Fill Activity Type via Details Form General tab
            if activity_type:
                self._select_details_tab("General")

                details_pane = self._get_details_pane()
                if details_pane:
                    try:
                        type_control = details_pane.child_window(
                            title_re=".*Activity Type.*|.*Type.*",
                            control_type="ComboBox"
                        )
                        try:
                            type_control.select(activity_type)
                        except Exception:
                            type_control.type_keys(activity_type, with_spaces=True)
                        time.sleep(self.ACTION_DELAY)
                        logger.debug(f"Set activity type: {activity_type}")
                    except Exception as e:
                        logger.warning(f"Could not set activity type: {e}")

            # Fill Calendar via Details Form General tab
            if calendar:
                if not activity_type:
                    # Only switch tab if we didn't already in the type step
                    self._select_details_tab("General")

                details_pane = self._get_details_pane()
                if details_pane:
                    try:
                        cal_control = details_pane.child_window(
                            title_re=".*Calendar.*",
                            control_type="ComboBox"
                        )
                        try:
                            cal_control.select(calendar)
                        except Exception:
                            cal_control.type_keys(calendar, with_spaces=True)
                        time.sleep(self.ACTION_DELAY)
                        logger.debug(f"Set calendar: {calendar}")
                    except Exception as e:
                        logger.warning(f"Could not set calendar: {e}")

            logger.info(f"Activity created: '{activity_name}'")
            return True

        except P6SafeModeError:
            raise
        except Exception as e:
            logger.error(f"Failed to create activity: {e}")
            return False

    def add_activity(self, wbs_path: Optional[str] = None) -> bool:
        """Deprecated: Use create_activity() instead."""
        logger.warning("add_activity() is deprecated. Use create_activity() instead.")
        return self.create_activity(activity_name="New Activity", duration=0, wbs_node=wbs_path)
    
    def delete_activity(self, activity_id: str) -> bool:
        """
        Delete an activity.
        
        Args:
            activity_id: Activity to delete
            
        Returns:
            True if deleted
        """
        self._check_safe_mode("Delete Activity")
        
        logger.info(f"Deleting activity: {activity_id}")
        
        try:
            # Select activity
            if not self.select_activity(activity_id):
                return False
            
            # Delete key
            self._window.type_keys("{DELETE}")
            time.sleep(self.ACTION_DELAY)
            
            # Confirm deletion dialog if present
            try:
                confirm = Desktop(backend="uia").window(
                    title_re=".*Confirm.*|.*Delete.*"
                )
                if confirm.exists():
                    yes_button = confirm.child_window(title="Yes", control_type="Button")
                    yes_button.click_input()
            except Exception:
                pass
            
            logger.info(f"✓ Activity deleted: {activity_id}")
            return True
            
        except P6SafeModeError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete activity: {e}")
            return False
    
    # =========================================================================
    # Clipboard Operations
    # =========================================================================
    
    def copy_activities(self) -> bool:
        """Copy selected activities to clipboard."""
        try:
            self._window.set_focus()
            self._window.type_keys("^C")
            time.sleep(self.ACTION_DELAY)
            logger.debug("Activities copied")
            return True
        except Exception:
            return False
    
    def paste_activities(self) -> bool:
        """Paste activities from clipboard."""
        self._check_safe_mode("Paste Activities")
        
        try:
            self._window.set_focus()
            self._window.type_keys("^V")
            time.sleep(self.ACTION_DELAY * 2)
            logger.debug("Activities pasted")
            return True
        except P6SafeModeError:
            raise
        except Exception:
            return False
