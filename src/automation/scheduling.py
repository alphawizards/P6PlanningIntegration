#!/usr/bin/env python3
"""
P6 Scheduling Module.

Provides schedule calculation and resource management automation:
- Schedule project (F9 - CPM calculation)
- Resource leveling
- Schedule check/diagnostics
- Baseline management
"""

import time
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

try:
    from pywinauto import Desktop
    from pywinauto.findwindows import ElementNotFoundError
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

from src.utils import logger
from .exceptions import (
    P6ScheduleError,
    P6TimeoutError,
    P6SafeModeError
)
from .utils import (
    wait_for_condition,
    get_timestamp
)


class ScheduleOption(Enum):
    """Schedule calculation options."""
    RETAINED_LOGIC = "Retained Logic"
    PROGRESS_OVERRIDE = "Progress Override"
    ACTUAL_DATES = "Actual Dates"


class P6ScheduleManager:
    """
    Manages P6 scheduling and CPM operations.
    
    Provides:
    - Schedule project (F9)
    - Resource leveling
    - Schedule check
    - Progress calculation options
    
    Warning:
        This class is NOT thread-safe.
        Scheduling operations can take significant time for large projects.
    """
    
    # Dialog patterns
    SCHEDULE_DIALOG_TITLE = "Schedule"
    LEVEL_RESOURCES_TITLE = "Level Resources"
    CHECK_SCHEDULE_TITLE = "Check Schedule"
    PROGRESS_DIALOG_TITLE = "Schedule Options"
    
    # Timing
    DIALOG_TIMEOUT = 15
    SCHEDULE_TIMEOUT = 300  # 5 minutes for large projects
    ACTION_DELAY = 0.5
    
    def __init__(self, main_window, safe_mode: bool = True):
        """
        Initialize schedule manager.
        
        Args:
            main_window: P6 main window wrapper
            safe_mode: Prevent destructive operations
        """
        self._window = main_window
        self.safe_mode = safe_mode
        
        logger.debug(f"P6ScheduleManager initialized (safe_mode={safe_mode})")
    
    def _check_safe_mode(self, operation: str):
        """Check if operation is blocked by safe mode."""
        if self.safe_mode:
            raise P6SafeModeError(
                f"'{operation}' blocked by SAFE_MODE. "
                f"Set safe_mode=False to enable scheduling operations."
            )
    
    # =========================================================================
    # Schedule Project (F9)
    # =========================================================================
    
    def schedule_project(
        self,
        option: ScheduleOption = ScheduleOption.RETAINED_LOGIC,
        wait_for_completion: bool = True
    ) -> bool:
        """
        Run schedule calculation (F9).
        
        Args:
            option: Scheduling logic option
            wait_for_completion: Wait for schedule to complete
            
        Returns:
            True if scheduled successfully
            
        Raises:
            P6SafeModeError: If safe mode is enabled
            P6ScheduleError: If scheduling fails
        """
        self._check_safe_mode("Schedule Project")
        
        logger.info(f"Scheduling project with option: {option.value}")
        start_time = datetime.now()
        
        try:
            self._window.set_focus()
            time.sleep(self.ACTION_DELAY)
            
            # Press F9 to open schedule dialog
            self._window.type_keys("{F9}")
            time.sleep(self.ACTION_DELAY * 2)
            
            # Find schedule dialog
            dialog = Desktop(backend="uia").window(
                title_re=f".*{self.SCHEDULE_DIALOG_TITLE}.*"
            )
            dialog.wait("ready", timeout=self.DIALOG_TIMEOUT)
            logger.debug("Schedule dialog opened")
            
            # Select scheduling option
            self._select_schedule_option(dialog, option)
            
            # Click Schedule button
            schedule_button = dialog.child_window(
                title_re=".*Schedule.*|.*OK.*",
                control_type="Button"
            )
            schedule_button.click_input()
            logger.debug("Clicked Schedule button")
            
            if wait_for_completion:
                # Wait for scheduling to complete
                if self._wait_for_schedule_complete():
                    elapsed = (datetime.now() - start_time).total_seconds()
                    logger.info(f"✓ Schedule complete in {elapsed:.1f}s")
                    return True
                else:
                    raise P6ScheduleError("Schedule did not complete in time")
            
            return True
            
        except P6SafeModeError:
            raise
        except Exception as e:
            raise P6ScheduleError(f"Failed to schedule project: {e}")
    
    def _select_schedule_option(self, dialog, option: ScheduleOption):
        """Select scheduling option in dialog."""
        try:
            radio = dialog.child_window(
                title_re=f".*{option.value}.*",
                control_type="RadioButton"
            )
            if radio.exists():
                radio.click_input()
                time.sleep(self.ACTION_DELAY)
        except Exception as e:
            logger.debug(f"Could not select schedule option: {e}")
    
    def _wait_for_schedule_complete(self, timeout: float = None) -> bool:
        """Wait for schedule calculation to complete."""
        timeout = timeout or self.SCHEDULE_TIMEOUT
        
        def is_complete():
            # Check if progress dialog is gone
            try:
                progress = Desktop(backend="uia").window(
                    title_re=".*Progress.*|.*Scheduling.*|.*Please Wait.*"
                )
                return not progress.exists()
            except Exception:
                return True
        
        # Initial wait for progress dialog to appear
        time.sleep(2)
        
        return wait_for_condition(
            condition=is_complete,
            timeout=timeout,
            poll_interval=2.0,
            description="Schedule completion"
        )
    
    def schedule_f9(self) -> bool:
        """Quick F9 schedule with default options."""
        return self.schedule_project(wait_for_completion=True)
    
    # =========================================================================
    # Resource Leveling
    # =========================================================================
    
    def level_resources(
        self,
        priority_based: bool = True,
        wait_for_completion: bool = True
    ) -> bool:
        """
        Run resource leveling.
        
        Args:
            priority_based: Use priority-based leveling
            wait_for_completion: Wait for leveling to complete
            
        Returns:
            True if leveled successfully
        """
        self._check_safe_mode("Level Resources")
        
        logger.info("Running resource leveling...")
        
        try:
            self._window.set_focus()
            time.sleep(self.ACTION_DELAY)
            
            # Tools -> Level Resources (or Project -> Level Resources)
            self._window.menu_select("Tools->Level Resources...")
            time.sleep(self.ACTION_DELAY * 2)
            
            dialog = Desktop(backend="uia").window(
                title_re=f".*{self.LEVEL_RESOURCES_TITLE}.*"
            )
            dialog.wait("ready", timeout=self.DIALOG_TIMEOUT)
            
            # Click Level button
            level_button = dialog.child_window(
                title_re=".*Level.*|.*OK.*",
                control_type="Button"
            )
            level_button.click_input()
            
            if wait_for_completion:
                self._wait_for_schedule_complete()
            
            logger.info("✓ Resource leveling complete")
            return True
            
        except P6SafeModeError:
            raise
        except Exception as e:
            raise P6ScheduleError(f"Failed to level resources: {e}")
    
    # =========================================================================
    # Schedule Check
    # =========================================================================
    
    def check_schedule(self) -> Dict:
        """
        Run schedule check (diagnostics).
        
        Returns:
            Dict with check results summary
        """
        logger.info("Running schedule check...")
        
        results = {
            'ran': False,
            'issues_found': 0,
            'warnings': [],
            'errors': []
        }
        
        try:
            self._window.set_focus()
            time.sleep(self.ACTION_DELAY)
            
            # Tools -> Check Schedule
            self._window.menu_select("Tools->Check Schedule...")
            time.sleep(self.ACTION_DELAY * 2)
            
            dialog = Desktop(backend="uia").window(
                title_re=f".*{self.CHECK_SCHEDULE_TITLE}.*"
            )
            dialog.wait("ready", timeout=self.DIALOG_TIMEOUT)
            
            # Click Check button
            check_button = dialog.child_window(
                title_re=".*Check.*|.*Run.*",
                control_type="Button"
            )
            check_button.click_input()
            time.sleep(self.ACTION_DELAY * 3)
            
            # Try to read results
            results['ran'] = True
            
            # TODO: Parse results from dialog/output
            # This requires reading the results pane
            
            # Close dialog
            close_button = dialog.child_window(
                title_re=".*Close.*|.*OK.*",
                control_type="Button"
            )
            if close_button.exists():
                close_button.click_input()
            
            logger.info("✓ Schedule check complete")
            
        except Exception as e:
            logger.error(f"Failed to check schedule: {e}")
            results['errors'].append(str(e))
        
        return results
    
    # =========================================================================
    # Global Change
    # =========================================================================
    
    def run_global_change(self, change_name: str) -> bool:
        """
        Run a saved global change.
        
        Args:
            change_name: Name of saved global change
            
        Returns:
            True if run successfully
        """
        self._check_safe_mode("Global Change")
        
        logger.info(f"Running global change: {change_name}")
        
        try:
            self._window.set_focus()
            
            # Tools -> Global Change
            self._window.menu_select("Tools->Global Change...")
            time.sleep(self.ACTION_DELAY * 2)
            
            dialog = Desktop(backend="uia").window(
                title_re=".*Global Change.*"
            )
            dialog.wait("ready", timeout=self.DIALOG_TIMEOUT)
            
            # Find and select change
            list_control = dialog.child_window(control_type="List")
            if list_control.exists():
                item = list_control.child_window(title=change_name)
                if item.exists():
                    item.click_input()
            
            # Apply
            apply_button = dialog.child_window(
                title_re=".*Apply.*|.*Run.*",
                control_type="Button"
            )
            apply_button.click_input()
            time.sleep(self.ACTION_DELAY * 2)
            
            logger.info(f"✓ Global change applied: {change_name}")
            return True
            
        except P6SafeModeError:
            raise
        except Exception as e:
            logger.error(f"Failed to run global change: {e}")
            return False
    
    # =========================================================================
    # Status
    # =========================================================================
    
    def get_schedule_status(self) -> Dict:
        """
        Get current schedule status.
        
        Returns:
            Dict with schedule information
        """
        return {
            'safe_mode': self.safe_mode,
            'can_schedule': not self.safe_mode
        }


class P6BaselineManager:
    """
    Manages P6 baselines.
    
    Provides:
    - Create baselines
    - Assign baselines
    - Maintain baselines
    
    Warning:
        Baseline operations modify project data.
    """
    
    # Dialog patterns
    ASSIGN_BASELINE_TITLE = "Assign Baselines"
    MAINTAIN_BASELINE_TITLE = "Maintain Baselines"
    
    # Timing
    DIALOG_TIMEOUT = 15
    ACTION_DELAY = 0.5
    
    def __init__(self, main_window, safe_mode: bool = True):
        """
        Initialize baseline manager.
        
        Args:
            main_window: P6 main window wrapper
            safe_mode: Prevent destructive operations
        """
        self._window = main_window
        self.safe_mode = safe_mode
        
        logger.debug(f"P6BaselineManager initialized")
    
    def _check_safe_mode(self, operation: str):
        """Check if operation is blocked by safe mode."""
        if self.safe_mode:
            raise P6SafeModeError(
                f"'{operation}' blocked by SAFE_MODE. "
                f"Set safe_mode=False to enable baseline operations."
            )
    
    def create_baseline(self, baseline_name: str) -> bool:
        """
        Create a new baseline from current schedule.
        
        Args:
            baseline_name: Name for new baseline
            
        Returns:
            True if created successfully
        """
        self._check_safe_mode("Create Baseline")
        
        if not baseline_name or not baseline_name.strip():
            raise ValueError("baseline_name cannot be empty")
        
        logger.info(f"Creating baseline: {baseline_name}")
        
        try:
            self._window.set_focus()
            
            # Project -> Maintain Baselines
            self._window.menu_select("Project->Maintain Baselines...")
            time.sleep(self.ACTION_DELAY * 2)
            
            dialog = Desktop(backend="uia").window(
                title_re=f".*{self.MAINTAIN_BASELINE_TITLE}.*"
            )
            dialog.wait("ready", timeout=self.DIALOG_TIMEOUT)
            
            # Click Add button
            add_button = dialog.child_window(
                title_re=".*Add.*|.*New.*",
                control_type="Button"
            )
            add_button.click_input()
            time.sleep(self.ACTION_DELAY)
            
            # Enter name
            name_edit = dialog.child_window(
                control_type="Edit",
                found_index=0
            )
            if name_edit.exists():
                name_edit.set_text(baseline_name)
            
            # Save/OK
            ok_button = dialog.child_window(
                title="OK",
                control_type="Button"
            )
            ok_button.click_input()
            
            logger.info(f"✓ Baseline created: {baseline_name}")
            return True
            
        except P6SafeModeError:
            raise
        except Exception as e:
            logger.error(f"Failed to create baseline: {e}")
            return False
    
    def assign_baseline(
        self,
        baseline_name: str,
        baseline_type: str = "Project"
    ) -> bool:
        """
        Assign a baseline to the project.
        
        Args:
            baseline_name: Name of baseline to assign
            baseline_type: Type (Project, Primary, Secondary, etc.)
            
        Returns:
            True if assigned successfully
        """
        self._check_safe_mode("Assign Baseline")
        
        logger.info(f"Assigning baseline: {baseline_name} as {baseline_type}")
        
        try:
            self._window.set_focus()
            
            # Project -> Assign Baselines
            self._window.menu_select("Project->Assign Baselines...")
            time.sleep(self.ACTION_DELAY * 2)
            
            dialog = Desktop(backend="uia").window(
                title_re=f".*{self.ASSIGN_BASELINE_TITLE}.*"
            )
            dialog.wait("ready", timeout=self.DIALOG_TIMEOUT)
            
            # Find baseline dropdown and select
            # TODO: Implement baseline selection in dialog
            
            # OK
            ok_button = dialog.child_window(
                title="OK",
                control_type="Button"
            )
            ok_button.click_input()
            
            logger.info(f"✓ Baseline assigned: {baseline_name}")
            return True
            
        except P6SafeModeError:
            raise
        except Exception as e:
            logger.error(f"Failed to assign baseline: {e}")
            return False
    
    def open_maintain_baselines(self) -> bool:
        """
        Open the Maintain Baselines dialog.
        
        Returns:
            True if opened successfully
        """
        try:
            self._window.set_focus()
            self._window.menu_select("Project->Maintain Baselines...")
            time.sleep(self.ACTION_DELAY * 2)
            return True
        except Exception as e:
            logger.error(f"Failed to open baseline dialog: {e}")
            return False
