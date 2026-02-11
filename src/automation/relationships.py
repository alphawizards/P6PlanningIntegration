#!/usr/bin/env python3
"""
P6 Relationship Manager Module.

Manages activity predecessor/successor relationships via the P6 Details
Form Relationships tab using the win32 backend with Delphi VCL message
protocol for direct control manipulation.

Capabilities:
- Read existing relationships from the Relationships tab grid
- Add predecessor relationships (with type and lag editing)
- Remove predecessor relationships
- Add successor relationships (convenience wrapper)

Uses the win32 backend exclusively. The UIA backend is unusable on
P6 Professional 20 (15-90s per operation). All control interaction
uses :class:`P6VCLBase` infrastructure: ``children()``,
``friendly_class_name()``, ``_edit_control_value()``, and
``_handle_confirmation_dialog()``.

P6 Professional 20 Relationships tab layout (verified):
  Grid (TCVirtualQueryGrid) showing:
    Predecessor | Activity Name | Relationship Type | Lag | ...
  Buttons below or beside the grid:
    Assign | Remove
"""

from __future__ import annotations

import ctypes
import re
import time

from src.utils import logger
from .exceptions import P6SafeModeError, P6EditError
from .vcl_base import P6VCLBase, WM_KEYDOWN, VK_RETURN


class P6RelationshipManager(P6VCLBase):
    """Manage P6 activity relationships via the Details Form Relationships tab.

    Inherits win32/VCL infrastructure from :class:`P6VCLBase` and adds
    relationship-specific grid discovery, reading, and editing.

    Requires a :class:`P6ActivityManager` instance for activity selection.
    All write operations require ``safe_mode=False``.

    Warning:
        This class is NOT thread-safe.
        P6 must be open with an activity view showing the Details Form.
    """

    # Valid relationship types in P6
    VALID_REL_TYPES: tuple[str, ...] = ("FS", "SS", "FF", "SF")

    # Grid column patterns for parsing relationship text
    _REL_TYPE_PATTERN = re.compile(r'\b(FS|SS|FF|SF)\b')

    def __init__(
        self,
        main_window: object,
        activity_manager: object,
        safe_mode: bool = True,
    ) -> None:
        """Initialize relationship manager.

        Args:
            main_window: P6 main window wrapper (UIA or win32).
            activity_manager: P6ActivityManager instance for select_activity.
            safe_mode: Prevent destructive operations (default True).
        """
        super().__init__(main_window)
        self._activity_manager: object = activity_manager
        self.safe_mode: bool = safe_mode

        logger.debug("P6RelationshipManager initialized (safe_mode=%s)", safe_mode)

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
                f"Set safe_mode=False to enable relationship editing."
            )

    # =========================================================================
    # Tab & Control Discovery
    # =========================================================================

    def _select_relationships_tab(self) -> bool:
        """Select the Relationships tab in the Details Form.

        Delegates to :meth:`P6VCLBase._select_details_tab` with
        ``tab_name="Relationships"``.

        Returns:
            ``True`` if the tab was found and clicked, ``False`` otherwise.
        """
        return self._select_details_tab("Relationships")

    def _find_relationship_grid(self) -> object | None:
        """Find the TCVirtualQueryGrid on the Relationships tab.

        The Relationships tab contains a grid control (Delphi
        ``TCVirtualQueryGrid``) that displays predecessor/successor
        relationships for the selected activity.

        Returns:
            The grid control wrapper, or ``None`` if not found.
        """
        self._ensure_win32()
        children = self._win32_window.children()

        for child in children:
            try:
                class_name: str = child.friendly_class_name()
                if 'Grid' in class_name or 'VirtualQuery' in class_name:
                    logger.debug(
                        "Found relationship grid: %s", class_name
                    )
                    return child
            except Exception:
                pass

        # Fallback: look for the actual Delphi class name
        for child in children:
            try:
                raw_class: str = child.class_name()
                if 'TCVirtualQueryGrid' in raw_class:
                    logger.debug(
                        "Found relationship grid (raw class): %s", raw_class
                    )
                    return child
            except Exception:
                pass

        logger.warning("Relationship grid not found on Relationships tab")
        return None

    def _find_button(self, button_text: str) -> object | None:
        """Find a button control by text in the main window's children.

        Searches for a Button-class child whose ``window_text()``
        contains *button_text* (case-insensitive).

        Args:
            button_text: Text to search for (e.g. ``"Assign"``, ``"Remove"``).

        Returns:
            The button control wrapper, or ``None`` if not found.
        """
        self._ensure_win32()
        children = self._win32_window.children()
        button_lower: str = button_text.lower()

        for child in children:
            try:
                if child.friendly_class_name() == 'Button':
                    text: str = child.window_text()
                    if button_lower in text.lower():
                        return child
            except Exception:
                pass

        return None

    # =========================================================================
    # Read Relationships
    # =========================================================================

    def read_relationships(self, activity_id: str) -> list[dict[str, str]]:
        """Read current relationships for an activity from the Relationships tab.

        Selects the activity, switches to the Relationships tab, and reads
        the grid contents. Each row in the grid represents one relationship.

        Args:
            activity_id: Activity ID to read relationships for.

        Returns:
            List of dicts with keys: ``'activity_id'``, ``'activity_name'``,
            ``'rel_type'``, ``'lag'``, ``'direction'`` (``'predecessor'``
            or ``'successor'``). Returns empty list on failure.
        """
        try:
            if not self._activity_manager.select_activity(activity_id):
                logger.error("Could not select activity: %s", activity_id)
                return []

            self._select_relationships_tab()
            grid = self._find_relationship_grid()
            if grid is None:
                return []

            relationships: list[dict[str, str]] = []

            # Read grid children — each row may be a child control or
            # the grid may expose text via children
            try:
                grid_children = grid.children()
                for child in grid_children:
                    try:
                        text: str = child.window_text().strip()
                        if not text:
                            continue

                        row_data: dict[str, str] = self._parse_grid_row(text)
                        if row_data:
                            relationships.append(row_data)
                    except Exception:
                        pass
            except Exception as e:
                logger.debug("Could not read grid children: %s", e)

            # Fallback: read grid text directly
            if not relationships:
                try:
                    grid_text: str = grid.window_text().strip()
                    if grid_text:
                        for line in grid_text.split('\n'):
                            row_data = self._parse_grid_row(line.strip())
                            if row_data:
                                relationships.append(row_data)
                except Exception as e:
                    logger.debug("Could not read grid text: %s", e)

            logger.info(
                "Activity %s has %d relationships",
                activity_id, len(relationships),
            )
            return relationships

        except Exception as e:
            logger.error(
                "Failed to read relationships for %s: %s", activity_id, e
            )
            return []

    def _parse_grid_row(self, text: str) -> dict[str, str] | None:
        """Parse a grid row text into a relationship dict.

        Attempts to extract activity ID, name, relationship type, and lag
        from a single row of grid text. The exact format depends on P6's
        grid rendering.

        Args:
            text: Raw text from a grid row.

        Returns:
            Dict with relationship data, or ``None`` if not parseable.
        """
        if not text:
            return None

        # Try to find a relationship type in the text
        rel_match = self._REL_TYPE_PATTERN.search(text)

        # Split on common delimiters (tab, multiple spaces)
        parts: list[str] = re.split(r'\t+|\s{2,}', text)
        parts = [p.strip() for p in parts if p.strip()]

        if len(parts) < 2:
            return None

        # Determine direction from text context
        text_lower: str = text.lower()
        if 'successor' in text_lower:
            direction = 'successor'
        else:
            direction = 'predecessor'

        result: dict[str, str] = {
            'activity_id': parts[0],
            'activity_name': parts[1] if len(parts) > 1 else '',
            'rel_type': rel_match.group(1) if rel_match else 'FS',
            'lag': '',
            'direction': direction,
        }

        # Try to extract lag from remaining parts
        for part in parts[2:]:
            if re.match(r'^-?\d+(\.\d+)?d?$', part):
                result['lag'] = part.rstrip('d')
                break

        return result

    # =========================================================================
    # Add Predecessor
    # =========================================================================

    def add_predecessor(
        self,
        activity_id: str,
        predecessor_id: str,
        rel_type: str = "FS",
        lag: int = 0,
    ) -> bool:
        """Add a predecessor relationship to an activity.

        Selects the target activity, switches to the Relationships tab,
        clicks the Assign button, searches for the predecessor in the
        Assign dialog, confirms the assignment, and optionally edits the
        relationship type and lag.

        Args:
            activity_id: Target activity ID (the successor).
            predecessor_id: Predecessor activity ID to add.
            rel_type: Relationship type — FS, SS, FF, or SF (default "FS").
            lag: Lag value in days (default 0).

        Returns:
            ``True`` if relationship added successfully, ``False`` otherwise.

        Raises:
            P6SafeModeError: If safe_mode is True.
            ValueError: If rel_type is not valid.
        """
        self._check_safe_mode("Add Predecessor")

        if rel_type not in self.VALID_REL_TYPES:
            raise ValueError(
                f"Invalid relationship type '{rel_type}'. "
                f"Must be one of: {', '.join(self.VALID_REL_TYPES)}"
            )

        logger.info(
            "Adding predecessor: %s -> %s (%s, lag=%d)",
            predecessor_id, activity_id, rel_type, lag,
        )

        try:
            # Select the target activity
            if not self._activity_manager.select_activity(activity_id):
                logger.error("Could not select activity: %s", activity_id)
                return False

            # Switch to Relationships tab
            self._select_relationships_tab()

            # Find and click the Assign button
            assign_btn = self._find_button("Assign")
            if assign_btn is None:
                raise P6EditError(
                    "Assign button not found on Relationships tab"
                )

            assign_btn.click_input()
            time.sleep(self.COMMIT_DELAY)

            # Handle the Assign dialog
            if not self._handle_assign_dialog(predecessor_id):
                logger.error(
                    "Failed to assign predecessor %s in dialog",
                    predecessor_id,
                )
                self._detach_thread()
                return False

            # Edit relationship type and lag if non-default
            if rel_type != "FS" or lag != 0:
                self._edit_relationship_properties(predecessor_id, rel_type, lag)

            logger.info(
                "Added relationship: %s -> %s (%s, lag=%d)",
                predecessor_id, activity_id, rel_type, lag,
            )
            self._detach_thread()
            return True

        except (P6SafeModeError, ValueError):
            raise
        except Exception as e:
            self._detach_thread()
            logger.error("Failed to add predecessor: %s", e)
            return False

    def _handle_assign_dialog(self, predecessor_id: str) -> bool:
        """Handle the P6 Assign Predecessors dialog.

        Finds the dialog window via ``find_elements``, locates the search
        edit field, types the predecessor ID, clicks Search/Assign, then
        closes the dialog.

        Args:
            predecessor_id: Activity ID to search for and assign.

        Returns:
            ``True`` if the dialog was handled successfully.
        """
        from pywinauto import Application
        from pywinauto.findwindows import find_elements

        pid = ctypes.c_ulong()
        handle: int = self._win32_handle or self._window.handle
        ctypes.windll.user32.GetWindowThreadProcessId(
            handle, ctypes.byref(pid)
        )

        # Wait for the Assign dialog to appear
        end_time: float = time.time() + self.DIALOG_TIMEOUT
        dialog_win = None

        while time.time() < end_time:
            try:
                elements = find_elements(
                    process=pid.value,
                    title_re=".*Assign.*",
                    backend="win32",
                    visible_only=True,
                )
                if elements:
                    dialog_handle: int = elements[0].handle
                    dialog_app = Application(backend="win32").connect(
                        handle=dialog_handle
                    )
                    dialog_win = dialog_app.window(handle=dialog_handle)
                    break
            except Exception:
                pass
            time.sleep(0.2)

        if dialog_win is None:
            logger.error("Assign dialog did not appear within timeout")
            return False

        try:
            dialog_children = dialog_win.children()

            # Find the search Edit control and type the predecessor ID
            search_edit = None
            for child in dialog_children:
                try:
                    if child.friendly_class_name() in ("Edit", "TCDBEdit"):
                        search_edit = child
                        break
                except Exception:
                    pass

            if search_edit is not None:
                search_handle: int = search_edit.handle
                # Attach to dialog thread for focus
                self._attach_thread()

                ctypes.windll.user32.SetFocus(search_handle)
                time.sleep(self.ACTION_DELAY)

                # Select all and type the predecessor ID
                ctypes.windll.user32.SendMessageW(
                    search_handle, 0x00B1, 0, -1  # EM_SETSEL
                )
                time.sleep(0.1)
                for ch in predecessor_id:
                    ctypes.windll.user32.SendMessageW(
                        search_handle, 0x0102, ord(ch), 0  # WM_CHAR
                    )
                    time.sleep(self.CHAR_DELAY)
                time.sleep(self.ACTION_DELAY)

                # Press Enter to search
                ctypes.windll.user32.SendMessageW(
                    search_handle, WM_KEYDOWN, VK_RETURN, 0
                )
                time.sleep(self.COMMIT_DELAY)
            else:
                logger.warning("Search edit not found in Assign dialog")

            # Find and click the Assign/OK button in the dialog
            for child in dialog_children:
                try:
                    if child.friendly_class_name() == "Button":
                        btn_text: str = child.window_text().lower()
                        if "assign" in btn_text or "ok" in btn_text:
                            child.click()
                            time.sleep(self.ACTION_DELAY)
                            break
                except Exception:
                    pass

            # Close the dialog if still open
            time.sleep(self.ACTION_DELAY)
            try:
                if dialog_win.is_visible():
                    for child in dialog_win.children():
                        try:
                            if child.friendly_class_name() == "Button":
                                btn_text = child.window_text().lower()
                                if "close" in btn_text or "cancel" in btn_text:
                                    child.click()
                                    time.sleep(self.ACTION_DELAY)
                                    break
                        except Exception:
                            pass
            except Exception:
                pass

            return True

        except Exception as e:
            logger.error("Error handling Assign dialog: %s", e)
            return False

    def _edit_relationship_properties(
        self,
        predecessor_id: str,
        rel_type: str,
        lag: int,
    ) -> None:
        """Edit relationship type and lag for a newly added relationship.

        After a relationship is assigned, it appears in the Relationships
        tab grid with default values (FS, lag=0). This method finds the
        relevant grid cells and edits them using the VCL protocol.

        Args:
            predecessor_id: Predecessor ID to locate in the grid.
            rel_type: Relationship type to set.
            lag: Lag value to set.
        """
        logger.debug(
            "Editing relationship properties: type=%s, lag=%d", rel_type, lag
        )

        try:
            grid = self._find_relationship_grid()
            if grid is None:
                logger.warning(
                    "Grid not found; type/lag may need manual adjustment"
                )
                return

            # Find edit controls on the Relationships tab that may
            # correspond to the selected grid row's editable cells.
            edits = self._get_edit_children()

            # Look for an edit control containing the default "FS" value
            # to overwrite with the new relationship type
            if rel_type != "FS":
                for idx, ctrl, text in edits:
                    if text.strip() == "FS":
                        self._edit_control_value(ctrl.handle, rel_type)
                        logger.debug("Set relationship type to: %s", rel_type)
                        break
                else:
                    logger.warning(
                        "Could not find Type cell to change from FS to %s. "
                        "Manual adjustment may be needed.",
                        rel_type,
                    )

            # Look for an edit control containing "0" for the lag field
            if lag != 0:
                for idx, ctrl, text in edits:
                    if text.strip() in ("0", "0d", "0.0"):
                        self._edit_control_value(ctrl.handle, str(lag))
                        logger.debug("Set relationship lag to: %d", lag)
                        break
                else:
                    logger.warning(
                        "Could not find Lag cell to set to %d. "
                        "Manual adjustment may be needed.",
                        lag,
                    )

        except Exception as e:
            logger.warning(
                "Failed to edit relationship properties: %s. "
                "Relationship was added but type/lag may need manual adjustment.",
                e,
            )

    # =========================================================================
    # Remove Predecessor
    # =========================================================================

    def remove_predecessor(self, activity_id: str, predecessor_id: str) -> bool:
        """Remove a predecessor relationship from an activity.

        Selects the activity, switches to the Relationships tab, finds
        the predecessor row in the grid, selects it, clicks Remove, and
        handles the confirmation dialog.

        Args:
            activity_id: Target activity ID (the successor).
            predecessor_id: Predecessor activity ID to remove.

        Returns:
            ``True`` if relationship removed successfully, ``False`` otherwise.

        Raises:
            P6SafeModeError: If safe_mode is True.
        """
        self._check_safe_mode("Remove Predecessor")

        logger.info(
            "Removing predecessor: %s from %s", predecessor_id, activity_id
        )

        try:
            # Select the target activity
            if not self._activity_manager.select_activity(activity_id):
                logger.error("Could not select activity: %s", activity_id)
                return False

            # Switch to Relationships tab
            self._select_relationships_tab()

            # Find the predecessor row in the grid
            grid = self._find_relationship_grid()
            if grid is None:
                raise P6EditError("Relationship grid not found")

            # Try to find and click the row containing predecessor_id
            row_found: bool = False
            try:
                grid_children = grid.children()
                for child in grid_children:
                    try:
                        text: str = child.window_text()
                        if predecessor_id in text:
                            child.click_input()
                            time.sleep(self.ACTION_DELAY)
                            row_found = True
                            break
                    except Exception:
                        pass
            except Exception:
                pass

            if not row_found:
                logger.error(
                    "Predecessor %s not found in relationships for %s",
                    predecessor_id, activity_id,
                )
                return False

            # Start confirmation dialog handler BEFORE clicking Remove
            dialog_thread, dialog_result = self._handle_confirmation_dialog(
                accept=True
            )

            # Find and click the Remove button
            remove_btn = self._find_button("Remove")
            if remove_btn is not None:
                remove_btn.click_input()
                time.sleep(self.ACTION_DELAY)
            else:
                # Fallback: send Delete key to the grid
                logger.debug("No Remove button found; sending Delete key")
                self._attach_thread()
                grid_handle: int = grid.handle
                ctypes.windll.user32.SendMessageW(
                    grid_handle, WM_KEYDOWN, 0x2E, 0  # VK_DELETE
                )
                time.sleep(self.ACTION_DELAY)

            # Wait for confirmation dialog handler
            dialog_thread.join(timeout=self.DIALOG_TIMEOUT)

            logger.info(
                "Removed predecessor: %s from %s", predecessor_id, activity_id
            )
            self._detach_thread()
            return True

        except P6SafeModeError:
            raise
        except Exception as e:
            self._detach_thread()
            logger.error("Failed to remove predecessor: %s", e)
            return False

    # =========================================================================
    # Add Successor (Convenience)
    # =========================================================================

    def add_successor(
        self,
        activity_id: str,
        successor_id: str,
        rel_type: str = "FS",
        lag: int = 0,
    ) -> bool:
        """Add a successor relationship to an activity.

        Semantically equivalent to adding a predecessor relationship
        with swapped arguments: *activity_id* becomes the predecessor
        of *successor_id*.

        Args:
            activity_id: Activity that will be the predecessor.
            successor_id: Activity that will be the successor.
            rel_type: Relationship type — FS, SS, FF, or SF (default "FS").
            lag: Lag value in days (default 0).

        Returns:
            ``True`` if relationship added successfully, ``False`` otherwise.

        Raises:
            P6SafeModeError: If safe_mode is True.
            ValueError: If rel_type is not valid.
        """
        logger.info(
            "Adding successor: %s -> %s (%s, lag=%d)",
            activity_id, successor_id, rel_type, lag,
        )

        result: bool = self.add_predecessor(
            activity_id=successor_id,
            predecessor_id=activity_id,
            rel_type=rel_type,
            lag=lag,
        )

        if result:
            logger.info(
                "Added successor: %s -> %s (%s, lag=%d)",
                activity_id, successor_id, rel_type, lag,
            )

        return result
