#!/usr/bin/env python3
"""
P6 Activity Editor Module.

Provides activity field editing via the P6 Details Form (bottom pane):
- Start/Finish date editing via the Dates tab
- Duration editing via the Status tab
- Edit verification (verify_edit helper)

Uses Details Form navigation rather than grid cell editing for reliability.
Always re-selects the Details tab before each edit -- tab state may not
persist across activity selections in P6 Professional.
"""

import time
import re
from typing import Optional

try:
    from pywinauto import Desktop
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

from src.utils import logger
from .exceptions import P6SafeModeError
from .utils import immediate_click, immediate_type


class P6ActivityEditor:
    """
    Edit P6 activity fields via the Details Form bottom pane.

    Requires a P6ActivityManager instance for activity selection (select_activity).
    All edit operations use the Details Form tabs (Dates, Status) rather than
    direct grid cell editing for reliability.

    Warning:
        This class is NOT thread-safe.
        Edit operations require safe_mode=False.
        P6 must be open with an activity view showing the Details Form.
    """

    # Timing constants
    DIALOG_TIMEOUT = 10
    ACTION_DELAY = 0.3
    VERIFY_DELAY = 0.5

    def __init__(self, main_window, activity_manager, safe_mode: bool = True):
        """
        Initialize activity editor.

        Args:
            main_window: P6 main window wrapper
            activity_manager: P6ActivityManager instance for select_activity
            safe_mode: Prevent destructive operations (default True)
        """
        self._window = main_window
        self._activity_manager = activity_manager
        self.safe_mode = safe_mode

        logger.debug(f"P6ActivityEditor initialized (safe_mode={safe_mode})")

    def _check_safe_mode(self, operation: str):
        """Check if operation is blocked by safe mode."""
        if self.safe_mode:
            raise P6SafeModeError(
                f"'{operation}' blocked by SAFE_MODE. "
                f"Set safe_mode=False to enable activity editing."
            )

    # =========================================================================
    # Details Form Helpers
    # =========================================================================

    def _get_details_pane(self):
        """
        Locate the Details Form bottom pane in P6.

        Best-effort locator -- exact control identification may vary
        in P6 Professional 20 (Java Swing via UIA).

        Returns:
            Pane wrapper for the Details Form area

        Raises:
            Exception if pane cannot be found
        """
        try:
            details_pane = self._window.child_window(
                control_type="Pane", found_index=1
            )
            return details_pane
        except Exception as e:
            logger.warning(f"Could not locate Details Form pane: {e}")
            raise

    def _select_details_tab(self, tab_name: str) -> bool:
        """
        Select a tab in the Details Form bottom pane.

        IMPORTANT: Always call this before EVERY edit operation -- tab state
        may not persist across activity selections.

        Args:
            tab_name: Name of the tab to select (e.g., "Dates", "Status")

        Returns:
            True if tab selected successfully, False on failure
        """
        try:
            details_pane = self._get_details_pane()
            tab_control = details_pane.child_window(control_type="Tab")
            tab_control.select(tab_name)
            time.sleep(self.ACTION_DELAY)
            logger.debug(f"Selected Details tab: {tab_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to select Details tab '{tab_name}': {e}")
            return False

    # =========================================================================
    # Verification
    # =========================================================================

    def verify_edit(self, control, expected_value: str) -> bool:
        """
        Verify that an edit was accepted by P6.

        Reads the value back from the control and compares with expected.
        Does NOT retry -- per user decision, report failure immediately.

        Args:
            control: pywinauto control wrapper to read value from
            expected_value: The value that should now be in the control

        Returns:
            True if value matches expected, False if mismatch
        """
        time.sleep(self.VERIFY_DELAY)

        # Read value back -- try get_value first, fall back to window_text
        try:
            actual_value = control.get_value()
        except (AttributeError, Exception):
            actual_value = control.window_text()

        # Compare with whitespace stripped
        expected_stripped = expected_value.strip()
        actual_stripped = str(actual_value).strip()

        if expected_stripped == actual_stripped:
            logger.info(
                f"Edit verified: value is '{actual_stripped}'"
            )
            return True
        else:
            logger.error(
                f"Edit verification FAILED: "
                f"expected='{expected_stripped}', actual='{actual_stripped}'"
            )
            return False

    # =========================================================================
    # Date Editing
    # =========================================================================

    def edit_start_date(self, activity_id: str, new_date: str) -> bool:
        """
        Edit the start date of an activity via the Details Form Dates tab.

        Date format is DD-MMM-YY (e.g., "15-Mar-26"). The format is passed
        through as-is -- no conversion or validation is performed here.

        Args:
            activity_id: Activity ID to edit
            new_date: New start date string (DD-MMM-YY)

        Returns:
            True if edit verified, False if rejected or failed
        """
        self._check_safe_mode("Edit Start Date")

        logger.info(f"Editing start date for {activity_id} -> {new_date}")

        try:
            # Select the activity
            if not self._activity_manager.select_activity(activity_id):
                logger.error(f"Could not select activity: {activity_id}")
                return False

            # Switch to Dates tab (always re-select)
            if not self._select_details_tab("Dates"):
                logger.error("Could not select Dates tab in Details Form")
                return False

            # Find start date field
            details_pane = self._get_details_pane()
            start_field = details_pane.child_window(
                control_type="Edit", title_re=".*Start.*"
            )

            # Set focus, clear, type new date, confirm
            start_field.set_focus()
            start_field.set_text("")
            start_field.type_keys(new_date, with_spaces=False)
            start_field.type_keys("{ENTER}")

            # Verify the edit
            return self.verify_edit(start_field, new_date)

        except P6SafeModeError:
            raise
        except Exception as e:
            logger.error(f"Failed to edit start date for {activity_id}: {e}")
            return False

    def edit_finish_date(self, activity_id: str, new_date: str) -> bool:
        """
        Edit the finish date of an activity via the Details Form Dates tab.

        Date format is DD-MMM-YY (e.g., "15-Mar-26"). The format is passed
        through as-is -- no conversion or validation is performed here.

        Args:
            activity_id: Activity ID to edit
            new_date: New finish date string (DD-MMM-YY)

        Returns:
            True if edit verified, False if rejected or failed
        """
        self._check_safe_mode("Edit Finish Date")

        logger.info(f"Editing finish date for {activity_id} -> {new_date}")

        try:
            # Select the activity
            if not self._activity_manager.select_activity(activity_id):
                logger.error(f"Could not select activity: {activity_id}")
                return False

            # Switch to Dates tab (always re-select)
            if not self._select_details_tab("Dates"):
                logger.error("Could not select Dates tab in Details Form")
                return False

            # Find finish date field
            details_pane = self._get_details_pane()
            finish_field = details_pane.child_window(
                control_type="Edit", title_re=".*Finish.*"
            )

            # Set focus, clear, type new date, confirm
            finish_field.set_focus()
            finish_field.set_text("")
            finish_field.type_keys(new_date, with_spaces=False)
            finish_field.type_keys("{ENTER}")

            # Verify the edit
            return self.verify_edit(finish_field, new_date)

        except P6SafeModeError:
            raise
        except Exception as e:
            logger.error(f"Failed to edit finish date for {activity_id}: {e}")
            return False

    # =========================================================================
    # Duration Editing
    # =========================================================================

    def edit_duration(
        self,
        activity_id: str,
        new_duration: int,
        use_details_form: bool = True
    ) -> bool:
        """
        Edit the remaining duration of an activity.

        Default mode uses the Details Form Status tab (more reliable).
        Grid mode (use_details_form=False) is available but less reliable.

        Note: For "Not Started" activities, changing Remaining Duration
        auto-updates Original Duration. This is expected P6 behavior --
        do not treat as an error.

        Args:
            activity_id: Activity ID to edit
            new_duration: New duration value (integer)
            use_details_form: Use Details Form (True) or grid editing (False)

        Returns:
            True if edit verified, False if rejected or failed
        """
        self._check_safe_mode("Edit Duration")

        logger.info(
            f"Editing duration for {activity_id} -> {new_duration} "
            f"(mode={'details_form' if use_details_form else 'grid'})"
        )

        try:
            # Select the activity
            if not self._activity_manager.select_activity(activity_id):
                logger.error(f"Could not select activity: {activity_id}")
                return False

            if use_details_form:
                return self._edit_duration_details_form(new_duration)
            else:
                return self._edit_duration_grid(new_duration)

        except P6SafeModeError:
            raise
        except Exception as e:
            logger.error(f"Failed to edit duration for {activity_id}: {e}")
            return False

    def _edit_duration_details_form(self, new_duration: int) -> bool:
        """Edit duration via Details Form Status tab."""
        # Switch to Status tab (always re-select)
        if not self._select_details_tab("Status"):
            logger.error("Could not select Status tab in Details Form")
            return False

        # Find Remaining Duration field
        details_pane = self._get_details_pane()
        duration_field = details_pane.child_window(
            control_type="Edit",
            title_re=".*Remaining.*Duration.*|.*Remaining.*Dur.*"
        )

        # Clear and type new duration, confirm
        duration_field.set_focus()
        duration_field.set_text("")
        duration_field.type_keys(str(new_duration), with_spaces=False)
        duration_field.type_keys("{ENTER}")

        # Verify the edit
        return self.verify_edit(duration_field, str(new_duration))

    def _edit_duration_grid(self, new_duration: int) -> bool:
        """Edit duration via grid cell editing (less reliable)."""
        logger.warning(
            "Grid editing for durations is less reliable than Details Form. "
            "Consider using use_details_form=True."
        )

        # Enter edit mode on current cell
        self._window.type_keys("{F2}")
        time.sleep(self.ACTION_DELAY)

        # Select all text and type new value
        self._window.type_keys("^A")
        time.sleep(self.ACTION_DELAY)
        self._window.type_keys(str(new_duration))
        self._window.type_keys("{ENTER}")

        # Verification is best-effort in grid mode
        logger.info(
            f"Grid edit completed for duration={new_duration}. "
            f"Verification is best-effort in grid mode."
        )
        return True
