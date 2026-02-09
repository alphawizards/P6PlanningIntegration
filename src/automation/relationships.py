#!/usr/bin/env python3
"""
P6 Relationship Manager Module.

Provides relationship (predecessor/successor) management:
- Add predecessor relationships
- Remove predecessor relationships
- Add successor relationships (convenience wrapper)
- Relationship type and lag editing
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


class P6RelationshipManager:
    """
    Manages P6 activity relationships (predecessors/successors).

    Provides:
    - Adding predecessor relationships with type and lag
    - Removing predecessor relationships
    - Adding successor relationships (convenience method)

    Warning:
        This class is NOT thread-safe.
        All operations require safe_mode=False.
    """

    # Timing
    DIALOG_TIMEOUT = 10
    ACTION_DELAY = 0.3

    # Valid relationship types in P6
    VALID_REL_TYPES = ("FS", "SS", "FF", "SF")

    def __init__(self, main_window, activity_manager, safe_mode: bool = True):
        """
        Initialize relationship manager.

        Args:
            main_window: P6 main window wrapper
            activity_manager: P6ActivityManager instance for activity selection
            safe_mode: Prevent destructive operations (default True)
        """
        self._window = main_window
        self._activity_manager = activity_manager
        self.safe_mode = safe_mode

        logger.debug(f"P6RelationshipManager initialized (safe_mode={safe_mode})")

    def _check_safe_mode(self, operation: str):
        """Check if operation is blocked by safe mode."""
        if self.safe_mode:
            raise P6SafeModeError(
                f"'{operation}' blocked by SAFE_MODE. "
                f"Set safe_mode=False to enable relationship editing."
            )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _get_details_pane(self):
        """
        Locate the Details Form pane at the bottom of the P6 window.

        Returns:
            Details pane control wrapper

        Raises:
            Exception if details pane not found
        """
        # The Details Form is typically a pane/panel at the bottom of the
        # main P6 window. Try common identifiers.
        details = self._window.child_window(
            title_re=".*Detail.*",
            control_type="Pane"
        )
        if details.exists(timeout=5):
            return details

        # Fallback: look for a tab control that contains relationship tabs
        tab_control = self._window.child_window(
            control_type="Tab",
            found_index=1  # Second tab control (first is usually the main view tabs)
        )
        if tab_control.exists(timeout=5):
            return tab_control.parent()

        raise Exception("Details pane not found in P6 window")

    def _select_details_tab(self, tab_name: str):
        """
        Select a tab in the Details Form pane.

        Args:
            tab_name: Name of the tab to select (e.g., "Relationships")
        """
        details_pane = self._get_details_pane()

        # Find and click the tab
        tab_item = details_pane.child_window(
            title_re=f".*{tab_name}.*",
            control_type="TabItem"
        )
        if tab_item.exists(timeout=5):
            immediate_click(tab_item)
            time.sleep(self.ACTION_DELAY)
            logger.debug(f"Selected details tab: {tab_name}")
            return

        # Fallback: try clicking text that matches
        tab_text = details_pane.child_window(title_re=f".*{tab_name}.*")
        if tab_text.exists(timeout=5):
            immediate_click(tab_text)
            time.sleep(self.ACTION_DELAY)
            logger.debug(f"Selected details tab (fallback): {tab_name}")
            return

        raise Exception(f"Details tab '{tab_name}' not found")

    # =========================================================================
    # Add Predecessor
    # =========================================================================

    def add_predecessor(
        self,
        activity_id: str,
        predecessor_id: str,
        rel_type: str = "FS",
        lag: int = 0
    ) -> bool:
        """
        Add a predecessor relationship to an activity.

        Args:
            activity_id: Target activity ID (the successor)
            predecessor_id: Predecessor activity ID to add
            rel_type: Relationship type - FS, SS, FF, or SF (default "FS")
            lag: Lag value in days (default 0)

        Returns:
            True if relationship added successfully

        Raises:
            P6SafeModeError: If safe_mode is True
            ValueError: If rel_type is not valid
        """
        self._check_safe_mode("Add Predecessor")

        # Validate relationship type
        if rel_type not in self.VALID_REL_TYPES:
            raise ValueError(
                f"Invalid relationship type '{rel_type}'. "
                f"Must be one of: {', '.join(self.VALID_REL_TYPES)}"
            )

        logger.info(
            f"Adding predecessor: {predecessor_id} -> {activity_id} "
            f"({rel_type}, lag={lag})"
        )

        try:
            # Select the target activity
            if not self._activity_manager.select_activity(activity_id):
                logger.error(f"Could not select activity: {activity_id}")
                return False

            # Switch to Relationships tab in Details Form
            self._select_details_tab("Relationships")

            # Get the details pane for button access
            details_pane = self._get_details_pane()

            # Click "Assign" button to open assignment dialog
            assign_button = details_pane.child_window(
                title="Assign", control_type="Button"
            )
            immediate_click(assign_button)
            time.sleep(self.ACTION_DELAY)

            # Wait for the Assign dialog
            assign_dialog = Desktop(backend="uia").window(
                title_re=".*Assign.*"
            )
            assign_dialog.wait("ready", timeout=self.DIALOG_TIMEOUT)

            # Find search edit field
            search_edit = assign_dialog.child_window(
                control_type="Edit", found_index=0
            )
            immediate_type(search_edit, predecessor_id)
            time.sleep(self.ACTION_DELAY)

            # Click Search/Find button
            search_button = assign_dialog.child_window(
                title_re=".*Search.*|.*Find.*", control_type="Button"
            )
            immediate_click(search_button)
            time.sleep(self.ACTION_DELAY)

            # Select the result (first item in list or the found activity)
            try:
                result_list = assign_dialog.child_window(
                    control_type="List"
                )
                if result_list.exists(timeout=3):
                    first_item = result_list.child_window(
                        control_type="ListItem", found_index=0
                    )
                    immediate_click(first_item)
                    time.sleep(self.ACTION_DELAY)
            except Exception:
                # Result may already be selected or use different control
                logger.debug("Could not click list item; proceeding with assignment")

            # Click Assign/OK button to confirm
            confirm_button = assign_dialog.child_window(
                title_re=".*Assign.*|.*OK.*", control_type="Button"
            )
            immediate_click(confirm_button)
            time.sleep(self.ACTION_DELAY)

            # Close dialog if still open
            try:
                if assign_dialog.exists(timeout=2):
                    close_button = assign_dialog.child_window(
                        title_re=".*Close.*|.*Cancel.*", control_type="Button"
                    )
                    if close_button.exists(timeout=1):
                        immediate_click(close_button)
                    else:
                        assign_dialog.type_keys("{ESC}")
            except Exception:
                pass

            # If non-default relationship type or non-zero lag, edit them
            if rel_type != "FS" or lag != 0:
                self._edit_relationship_properties(
                    details_pane, predecessor_id, rel_type, lag
                )

            logger.info(
                f"Added relationship: {predecessor_id} -> {activity_id} "
                f"({rel_type}, lag={lag})"
            )
            return True

        except P6SafeModeError:
            raise
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to add predecessor: {e}")
            return False

    def _edit_relationship_properties(
        self,
        details_pane,
        predecessor_id: str,
        rel_type: str,
        lag: int
    ):
        """
        Edit relationship type and lag for a newly added relationship.

        The relationship appears in the Relationships tab grid. This method
        finds the row and edits the Type and Lag columns.

        Note: The exact mechanism for editing cells in the Relationships tab
        grid depends on P6's UI controls. This implements the most likely
        pattern (double-click cell, type value, Enter). If it fails, clear
        log messages are produced for debugging during live P6 testing.

        Args:
            details_pane: The Details Form pane control
            predecessor_id: Predecessor ID to locate in the grid
            rel_type: Relationship type to set
            lag: Lag value to set
        """
        logger.debug(
            f"Editing relationship properties: type={rel_type}, lag={lag}"
        )

        try:
            # Find the row containing the predecessor ID
            row = details_pane.child_window(
                title_re=f".*{re.escape(predecessor_id)}.*"
            )
            if not row.exists(timeout=3):
                logger.warning(
                    f"Could not find relationship row for {predecessor_id}. "
                    f"Type/lag may need manual adjustment."
                )
                return

            # Edit relationship type if not default FS
            if rel_type != "FS":
                try:
                    # Try to find and double-click the Type cell
                    # The Type column is typically adjacent to the Activity ID
                    type_cell = details_pane.child_window(
                        title_re=".*FS.*",  # Current default value
                        found_index=0
                    )
                    if type_cell.exists(timeout=2):
                        type_cell.double_click_input()
                        time.sleep(self.ACTION_DELAY)

                        # Type the new relationship type
                        self._window.type_keys(rel_type, with_spaces=True)
                        time.sleep(self.ACTION_DELAY)
                        self._window.type_keys("{ENTER}")
                        time.sleep(self.ACTION_DELAY)

                        logger.debug(f"Set relationship type to: {rel_type}")
                    else:
                        logger.warning(
                            f"Could not find Type cell to change from FS to {rel_type}. "
                            f"Manual adjustment may be needed."
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to edit relationship type: {e}. "
                        f"Manual adjustment may be needed."
                    )

            # Edit lag if non-zero
            if lag != 0:
                try:
                    # Try to find and double-click the Lag cell
                    # The Lag column typically shows "0" or "0d"
                    lag_cell = details_pane.child_window(
                        title_re=".*Lag.*",
                        control_type="DataItem"
                    )
                    if not lag_cell.exists(timeout=2):
                        # Fallback: look for the cell showing "0"
                        lag_cell = details_pane.child_window(
                            title="0",
                            control_type="DataItem",
                            found_index=0
                        )

                    if lag_cell.exists(timeout=2):
                        lag_cell.double_click_input()
                        time.sleep(self.ACTION_DELAY)

                        # Type the lag value
                        self._window.type_keys(str(lag), with_spaces=True)
                        time.sleep(self.ACTION_DELAY)
                        self._window.type_keys("{ENTER}")
                        time.sleep(self.ACTION_DELAY)

                        logger.debug(f"Set relationship lag to: {lag}")
                    else:
                        logger.warning(
                            f"Could not find Lag cell to set to {lag}. "
                            f"Manual adjustment may be needed."
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to edit relationship lag: {e}. "
                        f"Manual adjustment may be needed."
                    )

        except Exception as e:
            logger.warning(
                f"Failed to edit relationship properties: {e}. "
                f"Relationship was added but type/lag may need manual adjustment."
            )

    # =========================================================================
    # Remove Predecessor
    # =========================================================================

    def remove_predecessor(self, activity_id: str, predecessor_id: str) -> bool:
        """
        Remove a predecessor relationship from an activity.

        Args:
            activity_id: Target activity ID (the successor)
            predecessor_id: Predecessor activity ID to remove

        Returns:
            True if relationship removed successfully

        Raises:
            P6SafeModeError: If safe_mode is True
        """
        self._check_safe_mode("Remove Predecessor")

        logger.info(
            f"Removing predecessor: {predecessor_id} from {activity_id}"
        )

        try:
            # Select the target activity
            if not self._activity_manager.select_activity(activity_id):
                logger.error(f"Could not select activity: {activity_id}")
                return False

            # Switch to Relationships tab
            self._select_details_tab("Relationships")

            # Get the details pane
            details_pane = self._get_details_pane()

            # Find the predecessor in the relationships grid
            predecessor_row = details_pane.child_window(
                title_re=f".*{re.escape(predecessor_id)}.*"
            )
            if not predecessor_row.exists(timeout=5):
                logger.error(
                    f"Predecessor {predecessor_id} not found in "
                    f"relationships for {activity_id}"
                )
                return False

            # Click to select the row
            immediate_click(predecessor_row)
            time.sleep(self.ACTION_DELAY)

            # Try "Remove" or "Delete" button first
            try:
                remove_button = details_pane.child_window(
                    title_re=".*Remove.*|.*Delete.*", control_type="Button"
                )
                if remove_button.exists(timeout=2):
                    immediate_click(remove_button)
                    time.sleep(self.ACTION_DELAY)
                else:
                    # Fallback: use Delete key
                    logger.debug("No Remove button found; using Delete key")
                    self._window.type_keys("{DELETE}")
                    time.sleep(self.ACTION_DELAY)
            except Exception:
                # Fallback: use Delete key
                logger.debug("Remove button not accessible; using Delete key")
                self._window.type_keys("{DELETE}")
                time.sleep(self.ACTION_DELAY)

            # Handle confirmation dialog if one appears
            try:
                confirm = Desktop(backend="uia").window(
                    title_re=".*Confirm.*|.*Delete.*|.*Remove.*"
                )
                if confirm.exists(timeout=2):
                    yes_button = confirm.child_window(
                        title_re=".*Yes.*|.*OK.*", control_type="Button"
                    )
                    if yes_button.exists(timeout=2):
                        immediate_click(yes_button)
                        time.sleep(self.ACTION_DELAY)
            except Exception:
                pass

            logger.info(
                f"Removed predecessor: {predecessor_id} from {activity_id}"
            )
            return True

        except P6SafeModeError:
            raise
        except Exception as e:
            logger.error(f"Failed to remove predecessor: {e}")
            return False

    # =========================================================================
    # Add Successor (Convenience)
    # =========================================================================

    def add_successor(
        self,
        activity_id: str,
        successor_id: str,
        rel_type: str = "FS",
        lag: int = 0
    ) -> bool:
        """
        Add a successor relationship to an activity.

        This is semantically equivalent to adding a predecessor relationship
        with swapped arguments: the activity becomes the predecessor of the
        successor.

        Args:
            activity_id: Activity that will be the predecessor
            successor_id: Activity that will be the successor
            rel_type: Relationship type - FS, SS, FF, or SF (default "FS")
            lag: Lag value in days (default 0)

        Returns:
            True if relationship added successfully

        Raises:
            P6SafeModeError: If safe_mode is True
            ValueError: If rel_type is not valid
        """
        logger.info(
            f"Adding successor: {activity_id} -> {successor_id} "
            f"({rel_type}, lag={lag})"
        )

        result = self.add_predecessor(
            activity_id=successor_id,
            predecessor_id=activity_id,
            rel_type=rel_type,
            lag=lag
        )

        if result:
            logger.info(
                f"Added successor: {activity_id} -> {successor_id} "
                f"({rel_type}, lag={lag})"
            )

        return result
