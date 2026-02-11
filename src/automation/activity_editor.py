#!/usr/bin/env python3
"""
P6 Activity Editor Module.

Provides activity field editing via the P6 Details Form (bottom pane):
- Start/Finish date editing via the Status tab
- Duration editing via the Status tab
- Edit verification (verify_edit helper)
- Activity status reading

Uses win32 backend with Delphi VCL message protocol for direct control
manipulation. P6 Professional 20 is a Delphi application (TDevxMainForm)
using TCDBEdit data-bound Edit controls.

Editing approach (verified against P6 Professional 20):
  1. AttachThreadInput to P6's thread (required for cross-process SetFocus)
  2. SetFocus on the target TCDBEdit control
  3. EM_SETSEL(0, -1) to select all text
  4. WM_CHAR for each character of the new value
  5. CN_COMMAND(EN_CHANGE) to notify the Delphi VCL of the change
  6. WM_COMMAND(EN_CHANGE) to notify the parent control
  7. WM_KEYDOWN(VK_RETURN) to trigger Enter-key commit
  8. SetFocus to a different control to complete the focus change
  9. Handle any Confirmation dialog (e.g., date constraint prompts)

P6 Professional 20 Details Form tabs:
  General | Status | Resources | Codes | Notebook | Risks | Relationships

Status tab layout (verified):
  Left column:  Original Duration, Actual Duration, Remaining Duration,
                At Complete Duration, Total Float, Free Float
  Right column: Start date, Finish date, Expected Finish, Constraints
  Checkboxes:   Started, Finished
"""

from __future__ import annotations

import re
import time
from typing import Optional

from src.utils import logger
from .exceptions import P6SafeModeError, P6EditError
from .vcl_base import P6VCLBase


class P6ActivityEditor(P6VCLBase):
    """Edit P6 activity fields via the Details Form bottom pane.

    Inherits win32/VCL infrastructure from :class:`P6VCLBase` and adds
    activity-specific field discovery, editing, and verification.

    Requires a :class:`P6ActivityManager` instance for activity selection.
    All edit operations use the Details Form Status tab.

    Warning:
        This class is NOT thread-safe.
        Edit operations require ``safe_mode=False``.
        P6 must be open with an activity view showing the Details Form.
    """

    # Date pattern: DD-MMM-YY (e.g., "16-May-25")
    DATE_PATTERN = re.compile(r'^\d{2}-[A-Z][a-z]{2}-\d{2}$')
    # Numeric pattern for durations/floats
    NUMERIC_PATTERN = re.compile(r'^\d+(\.\d+)?$')

    def __init__(
        self,
        main_window: object,
        activity_manager: object,
        safe_mode: bool = True,
    ) -> None:
        """Initialize activity editor.

        Args:
            main_window: P6 main window wrapper (UIA or win32).
            activity_manager: P6ActivityManager instance for select_activity.
            safe_mode: Prevent destructive operations (default True).
        """
        super().__init__(main_window)
        self._activity_manager: object = activity_manager
        self.safe_mode: bool = safe_mode

        logger.debug("P6ActivityEditor initialized (safe_mode=%s)", safe_mode)

    def _check_safe_mode(self, operation: str) -> None:
        """Check if operation is blocked by safe mode.

        Args:
            operation: Human-readable name of the blocked operation.

        Raises:
            P6SafeModeError: If safe mode is enabled.
        """
        if self.safe_mode:
            raise P6SafeModeError(
                f"'{operation}' blocked by SAFE_MODE. "
                f"Set safe_mode=False to enable activity editing."
            )

    # =========================================================================
    # Field Discovery
    # =========================================================================

    def _find_status_duration_fields(self) -> dict[str, tuple[object, str]]:
        """Find duration fields on the Status tab by position analysis.

        Returns:
            Dict with keys ``'original'``, ``'actual'``, ``'remaining'``,
            ``'at_complete'``, ``'total_float'``, ``'free_float'``.
            Values are ``(control, current_text)`` tuples.
        """
        edits = self._get_edit_children()
        children = self._win32_window.children()

        # Find the Status tab sheet for coordinate reference
        status_tab = None
        for child in children:
            try:
                if (child.friendly_class_name() == 'TcsTabSheet'
                        and child.window_text() == 'Status'):
                    status_tab = child
                    break
            except Exception:
                pass

        if not status_tab:
            raise P6EditError("Status tab not found in Details Form")

        tab_rect = status_tab.rectangle()
        tab_midx = (tab_rect.left + tab_rect.right) // 2

        # Find numeric Edit controls in the left column
        left_numerics: list[tuple[int, int, object, str]] = []
        for idx, ctrl, text in edits:
            if not self.NUMERIC_PATTERN.match(text):
                continue
            r = ctrl.rectangle()
            if r.left < tab_midx and r.top >= tab_rect.top - 10:
                left_numerics.append((r.top, idx, ctrl, text))

        left_numerics.sort(key=lambda x: x[0])

        field_names = [
            'original', 'actual', 'remaining', 'at_complete',
            'total_float', 'free_float'
        ]
        fields: dict[str, tuple[object, str]] = {}
        for i, name in enumerate(field_names):
            if i < len(left_numerics):
                _, idx, ctrl, text = left_numerics[i]
                fields[name] = (ctrl, text)

        return fields

    def _find_status_date_fields(self) -> dict[str, tuple[object, str]]:
        """Find date fields on the Status tab.

        Returns:
            Dict with keys ``'start'``, ``'finish'``.
            Values are ``(inner_control, current_text)`` tuples.

            Date fields have outer/inner Edit pairs. The inner control
            (smaller bounding rect) is used for editing.
        """
        edits = self._get_edit_children()

        date_fields: list[tuple[int, int, int, object, str]] = []
        for idx, ctrl, text in edits:
            if not self.DATE_PATTERN.match(text):
                continue
            r = ctrl.rectangle()
            date_fields.append((r.top, r.width(), idx, ctrl, text))

        date_fields.sort(key=lambda x: (x[0], x[1]))

        # Group by approximate Y position (outer/inner pairs within 5px)
        groups: list[list[tuple[int, int, int, object, str]]] = []
        for item in date_fields:
            y = item[0]
            placed = False
            for group in groups:
                if abs(group[0][0] - y) < 5:
                    group.append(item)
                    placed = True
                    break
            if not placed:
                groups.append([item])

        # Pick the narrower control (inner) from each group
        result: dict[str, tuple[object, str]] = {}
        field_names = ['start', 'finish']
        for i, group in enumerate(groups):
            if i >= len(field_names):
                break
            group.sort(key=lambda x: x[1])
            _, _, idx, ctrl, text = group[0]
            result[field_names[i]] = (ctrl, text)

        return result

    # =========================================================================
    # Tab Selection
    # =========================================================================

    def _select_status_tab(self) -> bool:
        """Select the Status tab in the Details Form.

        Delegates to :meth:`P6VCLBase._select_details_tab` with
        ``tab_name="Status"``.

        Returns:
            ``True`` if the tab was found and clicked, ``False`` otherwise.
        """
        return self._select_details_tab("Status")

    # =========================================================================
    # Verification
    # =========================================================================

    def verify_edit(self, control: object, expected_value: str) -> bool:
        """Verify that an edit was accepted by P6.

        P6 may reformat values (e.g., ``"50"`` -> ``"50.00"`` for
        durations).

        Args:
            control: pywinauto control wrapper to read value from.
            expected_value: The value that should now be in the control.

        Returns:
            ``True`` if value matches expected (with P6 reformatting),
            ``False`` if mismatch.
        """
        time.sleep(self.VERIFY_DELAY)

        actual_value: str = control.window_text().strip()
        expected_stripped: str = expected_value.strip()

        if expected_stripped == actual_value:
            logger.info("Edit verified: value is '%s'", actual_value)
            return True

        # P6 reformats numbers: "50" -> "50.00"
        try:
            if float(expected_stripped) == float(actual_value):
                logger.info(
                    "Edit verified (reformatted): '%s' -> '%s'",
                    expected_stripped, actual_value,
                )
                return True
        except (ValueError, TypeError):
            pass

        logger.error(
            "Edit verification FAILED: expected='%s', actual='%s'",
            expected_stripped, actual_value,
        )
        return False

    # =========================================================================
    # Duration Editing
    # =========================================================================

    def edit_duration(self, activity_id: str, new_duration: int) -> bool:
        """Edit the remaining duration of an activity via the Status tab.

        For "Not Started" activities, changing Remaining Duration
        auto-updates Original Duration. This is expected P6 behavior.

        Args:
            activity_id: Activity ID to edit.
            new_duration: New duration value (integer days).

        Returns:
            ``True`` if edit verified, ``False`` if rejected or failed.
        """
        self._check_safe_mode("Edit Duration")
        logger.info("Editing duration for %s -> %s", activity_id, new_duration)

        try:
            if not self._activity_manager.select_activity(activity_id):
                logger.error("Could not select activity: %s", activity_id)
                return False

            self._select_status_tab()

            duration_fields = self._find_status_duration_fields()
            if 'remaining' not in duration_fields:
                raise P6EditError("Remaining Duration field not found")

            dur_ctrl, current_value = duration_fields['remaining']
            logger.debug("Remaining Duration: current='%s'", current_value)

            # Find a different control to commit focus to
            commit_ctrl = None
            if 'original' in duration_fields:
                commit_ctrl = duration_fields['original'][0]

            self._edit_control_value(
                dur_ctrl.handle,
                str(new_duration),
                commit_handle=commit_ctrl.handle if commit_ctrl else None
            )

            result = self.verify_edit(dur_ctrl, str(new_duration))
            self._detach_thread()
            return result

        except P6SafeModeError:
            raise
        except Exception as e:
            self._detach_thread()
            logger.error("Failed to edit duration for %s: %s", activity_id, e)
            return False

    # =========================================================================
    # Date Editing
    # =========================================================================

    def edit_start_date(
        self,
        activity_id: str,
        new_date: str,
        add_constraint: bool = True,
    ) -> bool:
        """Edit the start date of an activity via the Status tab.

        P6 shows a confirmation dialog asking about adding a constraint.
        The *add_constraint* parameter controls whether to accept (Yes) or
        decline (No) the constraint.

        Date format is ``DD-MMM-YY`` (e.g., ``"15-Mar-26"``).

        Args:
            activity_id: Activity ID to edit.
            new_date: New start date string (DD-MMM-YY).
            add_constraint: Accept constraint dialog (True=Yes, False=No).

        Returns:
            ``True`` if edit accepted by P6, ``False`` if rejected or failed.
        """
        self._check_safe_mode("Edit Start Date")
        logger.info("Editing start date for %s -> %s", activity_id, new_date)

        try:
            if not self._activity_manager.select_activity(activity_id):
                logger.error("Could not select activity: %s", activity_id)
                return False

            self._select_status_tab()

            date_fields = self._find_status_date_fields()
            if 'start' not in date_fields:
                raise P6EditError("Start date field not found")

            start_ctrl, current_value = date_fields['start']
            logger.debug("Start date: current='%s'", current_value)

            # Find commit target (finish date field)
            commit_ctrl = date_fields.get('finish', (None, None))[0]

            # Start dialog handler BEFORE editing (date changes trigger dialogs)
            dialog_thread, dialog_result = self._handle_confirmation_dialog(
                accept=add_constraint
            )

            self._edit_control_value(
                start_ctrl.handle,
                new_date,
                commit_handle=commit_ctrl.handle if commit_ctrl else None
            )

            # Wait for dialog handler to finish
            dialog_thread.join(timeout=self.DIALOG_TIMEOUT)

            result = self.verify_edit(start_ctrl, new_date)
            self._detach_thread()
            return result

        except P6SafeModeError:
            raise
        except Exception as e:
            self._detach_thread()
            logger.error("Failed to edit start date for %s: %s", activity_id, e)
            return False

    def edit_finish_date(
        self,
        activity_id: str,
        new_date: str,
        add_constraint: bool = True,
    ) -> bool:
        """Edit the finish date of an activity via the Status tab.

        P6 shows a confirmation dialog asking about adding a constraint.

        Date format is ``DD-MMM-YY`` (e.g., ``"15-Mar-26"``).

        Args:
            activity_id: Activity ID to edit.
            new_date: New finish date string (DD-MMM-YY).
            add_constraint: Accept constraint dialog (True=Yes, False=No).

        Returns:
            ``True`` if edit accepted by P6, ``False`` if rejected or failed.
        """
        self._check_safe_mode("Edit Finish Date")
        logger.info("Editing finish date for %s -> %s", activity_id, new_date)

        try:
            if not self._activity_manager.select_activity(activity_id):
                logger.error("Could not select activity: %s", activity_id)
                return False

            self._select_status_tab()

            date_fields = self._find_status_date_fields()
            if 'finish' not in date_fields:
                raise P6EditError("Finish date field not found")

            finish_ctrl, current_value = date_fields['finish']
            logger.debug("Finish date: current='%s'", current_value)

            # Find commit target (start date field)
            commit_ctrl = date_fields.get('start', (None, None))[0]

            # Start dialog handler BEFORE editing
            dialog_thread, dialog_result = self._handle_confirmation_dialog(
                accept=add_constraint
            )

            self._edit_control_value(
                finish_ctrl.handle,
                new_date,
                commit_handle=commit_ctrl.handle if commit_ctrl else None
            )

            # Wait for dialog handler
            dialog_thread.join(timeout=self.DIALOG_TIMEOUT)

            result = self.verify_edit(finish_ctrl, new_date)
            self._detach_thread()
            return result

        except P6SafeModeError:
            raise
        except Exception as e:
            self._detach_thread()
            logger.error("Failed to edit finish date for %s: %s", activity_id, e)
            return False

    # =========================================================================
    # Constraint Reading
    # =========================================================================

    def get_activity_constraints(
        self, activity_id: str,
    ) -> Optional[dict[str, str]]:
        """Read constraint information from the General tab.

        Navigates to the General tab in the Details Form and reads
        constraint type and date fields.

        Args:
            activity_id: Activity ID to read constraints for.

        Returns:
            Dict with ``'constraint_type'`` and ``'constraint_date'``
            keys, or ``None`` on failure.
        """
        try:
            if not self._activity_manager.select_activity(activity_id):
                logger.error("Could not select activity: %s", activity_id)
                return None

            self._select_details_tab("General")

            edits = self._get_edit_children()
            result: dict[str, str] = {}

            # Look for a constraint type field (common values:
            # "As Late As Possible", "Start On", "Finish On",
            # "Start On or Before", etc.)
            constraint_keywords = (
                'as late', 'as soon', 'start on', 'finish on',
                'mandatory', 'not earlier', 'not later',
            )
            for idx, ctrl, text in edits:
                text_lower: str = text.strip().lower()
                for keyword in constraint_keywords:
                    if keyword in text_lower:
                        result['constraint_type'] = text.strip()
                        break

            # Look for a constraint date (DD-MMM-YY pattern)
            for idx, ctrl, text in edits:
                if self.DATE_PATTERN.match(text.strip()):
                    # On the General tab, date fields that aren't
                    # start/finish are likely constraint dates
                    if 'constraint_date' not in result:
                        result['constraint_date'] = text.strip()

            if not result:
                result = {
                    'constraint_type': 'As Late As Possible',
                    'constraint_date': '',
                }

            logger.info(
                "Activity %s constraints: %s", activity_id, result
            )
            return result

        except Exception as e:
            logger.error(
                "Failed to read constraints for %s: %s", activity_id, e
            )
            return None

    # =========================================================================
    # Critical Path Identification
    # =========================================================================

    def is_critical(self, activity_id: str) -> bool:
        """Check if an activity is on the critical path.

        An activity is considered critical if its Total Float is zero
        or negative.

        Args:
            activity_id: Activity ID to check.

        Returns:
            ``True`` if the activity is critical (Total Float <= 0),
            ``False`` otherwise or on failure.
        """
        try:
            if not self._activity_manager.select_activity(activity_id):
                logger.error("Could not select activity: %s", activity_id)
                return False

            self._select_status_tab()

            dur_fields = self._find_status_duration_fields()
            if 'total_float' not in dur_fields:
                logger.debug(
                    "Total Float field not found for %s", activity_id
                )
                return False

            _, float_text = dur_fields['total_float']
            total_float: float = float(float_text)

            is_crit: bool = total_float <= 0
            logger.debug(
                "Activity %s: Total Float=%.2f, critical=%s",
                activity_id, total_float, is_crit,
            )
            return is_crit

        except (ValueError, TypeError) as e:
            logger.debug(
                "Could not parse Total Float for %s: %s", activity_id, e
            )
            return False
        except Exception as e:
            logger.error(
                "Failed to check critical status for %s: %s", activity_id, e
            )
            return False

    def get_critical_activities(
        self, activity_ids: list[str],
    ) -> list[str]:
        """Identify which activities are on the critical path.

        Convenience wrapper that checks Total Float for each activity
        and returns those with zero or negative float.

        Args:
            activity_ids: List of activity IDs to check.

        Returns:
            List of activity IDs that are on the critical path.
        """
        critical: list[str] = []
        for act_id in activity_ids:
            if self.is_critical(act_id):
                critical.append(act_id)

        logger.info(
            "Critical path scan: %d/%d activities are critical",
            len(critical), len(activity_ids),
        )
        return critical

    # =========================================================================
    # Field Reading
    # =========================================================================

    def get_activity_status(self, activity_id: str) -> Optional[dict]:
        """Read current Status tab values for an activity.

        Args:
            activity_id: Activity ID to read.

        Returns:
            Dict with duration and date fields, or ``None`` on failure.
        """
        try:
            if not self._activity_manager.select_activity(activity_id):
                logger.error("Could not select activity: %s", activity_id)
                return None

            self._select_status_tab()

            result: dict[str, str] = {}

            try:
                dur_fields = self._find_status_duration_fields()
                for key in ['original', 'actual', 'remaining',
                            'at_complete', 'total_float', 'free_float']:
                    if key in dur_fields:
                        _, text = dur_fields[key]
                        result_key = (f'{key}_duration' if key in
                                      ['original', 'actual', 'remaining',
                                       'at_complete'] else key)
                        result[result_key] = text
            except Exception as e:
                logger.debug("Could not read duration fields: %s", e)

            try:
                date_fields = self._find_status_date_fields()
                if 'start' in date_fields:
                    result['start_date'] = date_fields['start'][1]
                if 'finish' in date_fields:
                    result['finish_date'] = date_fields['finish'][1]
            except Exception as e:
                logger.debug("Could not read date fields: %s", e)

            logger.info("Activity %s status: %s", activity_id, result)
            return result

        except Exception as e:
            logger.error("Failed to read status for %s: %s", activity_id, e)
            return None
