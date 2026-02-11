#!/usr/bin/env python3
"""
P6 Scheduling Module.

Provides schedule calculation and resource management automation:
- Schedule project (F9 — CPM calculation) via win32 backend
- Circular logic error detection
- Resource leveling (UIA — Phase 3+ scope)
- Schedule check/diagnostics (UIA — Phase 3+ scope)
- Baseline management (UIA — separate scope)
"""

from __future__ import annotations

import ctypes
import time
from datetime import datetime
from enum import Enum

try:
    from pywinauto import Application, Desktop
    from pywinauto.findwindows import find_elements, ElementNotFoundError
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

# Win32 key constants
VK_F9: int = 0x78
WM_KEYDOWN: int = 0x0100
WM_KEYUP: int = 0x0101


class ScheduleOption(Enum):
    """Schedule calculation options."""
    RETAINED_LOGIC = "Retained Logic"
    PROGRESS_OVERRIDE = "Progress Override"
    ACTUAL_DATES = "Actual Dates"


class P6ScheduleManager:
    """Manage P6 scheduling and CPM operations.

    The ``schedule_project`` and ``schedule_f9`` methods use the **win32**
    backend for fast, reliable dialog interaction.  Other methods
    (``level_resources``, ``check_schedule``, ``run_global_change``) still
    use the UIA backend and are Phase 3+ scope — they are retained as-is
    for forward compatibility.

    Warning:
        This class is NOT thread-safe.
        Scheduling operations can take significant time for large projects.
    """

    # Dialog title patterns
    SCHEDULE_DIALOG_TITLE: str = "Schedule"
    LEVEL_RESOURCES_TITLE: str = "Level Resources"
    CHECK_SCHEDULE_TITLE: str = "Check Schedule"
    PROGRESS_DIALOG_TITLE: str = "Schedule Options"

    # Timing constants (seconds)
    DIALOG_TIMEOUT: float = 15.0
    SCHEDULE_TIMEOUT: float = 300.0  # 5 minutes for large projects
    ACTION_DELAY: float = 0.5

    def __init__(self, main_window: object, safe_mode: bool = True) -> None:
        """Initialize schedule manager.

        Args:
            main_window: P6 main window wrapper (UIA or win32).
                Must expose a ``.handle`` attribute with the HWND value.
            safe_mode: Prevent destructive operations (default True).
        """
        self._window: object = main_window
        self.safe_mode: bool = safe_mode

        # Win32 backend state (lazy-initialized)
        self._win32_handle: int | None = None
        self._p6_pid: int | None = None

        logger.debug("P6ScheduleManager initialized (safe_mode=%s)", safe_mode)

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
                f"Set safe_mode=False to enable scheduling operations."
            )

    # =========================================================================
    # Win32 Infrastructure
    # =========================================================================

    def _ensure_win32(self) -> None:
        """Ensure win32 handle and PID are resolved.

        Resolves the HWND and process ID from the main window on first
        call and caches the results.  Subsequent calls are no-ops.

        Raises:
            P6ScheduleError: If the handle cannot be resolved.
        """
        if self._win32_handle is not None:
            return

        try:
            handle: int = self._window.handle
            self._win32_handle = handle

            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(
                handle, ctypes.byref(pid)
            )
            self._p6_pid = pid.value

            logger.debug(
                "Win32 handle resolved (hwnd=%s, pid=%s)",
                handle, self._p6_pid,
            )
        except Exception as e:
            raise P6ScheduleError(
                f"Cannot resolve win32 handle: {e}"
            ) from e

    def _find_dialog(
        self,
        title: str,
        timeout: float | None = None,
    ) -> object | None:
        """Find a P6 dialog by title using win32 find_elements.

        Polls for a dialog window with a matching title within the P6
        process.

        Args:
            title: Window title to search for (exact match).
            timeout: Seconds to wait (defaults to DIALOG_TIMEOUT).

        Returns:
            Dialog window wrapper, or ``None`` if not found.
        """
        self._ensure_win32()
        timeout = timeout if timeout is not None else self.DIALOG_TIMEOUT
        end_time: float = time.time() + timeout

        while time.time() < end_time:
            try:
                elements = find_elements(
                    process=self._p6_pid,
                    title=title,
                    backend="win32",
                    visible_only=True,
                )
                if elements:
                    dialog_handle: int = elements[0].handle
                    dialog_app = Application(backend="win32").connect(
                        handle=dialog_handle
                    )
                    return dialog_app.window(handle=dialog_handle)
            except Exception:
                pass
            time.sleep(0.2)

        return None

    def _find_dialog_re(
        self,
        title_re: str,
        timeout: float | None = None,
    ) -> object | None:
        """Find a P6 dialog by title regex using win32 find_elements.

        Args:
            title_re: Regex pattern to match against window titles.
            timeout: Seconds to wait (defaults to DIALOG_TIMEOUT).

        Returns:
            Dialog window wrapper, or ``None`` if not found.
        """
        self._ensure_win32()
        timeout = timeout if timeout is not None else self.DIALOG_TIMEOUT
        end_time: float = time.time() + timeout

        while time.time() < end_time:
            try:
                elements = find_elements(
                    process=self._p6_pid,
                    title_re=title_re,
                    backend="win32",
                    visible_only=True,
                )
                if elements:
                    dialog_handle: int = elements[0].handle
                    dialog_app = Application(backend="win32").connect(
                        handle=dialog_handle
                    )
                    return dialog_app.window(handle=dialog_handle)
            except Exception:
                pass
            time.sleep(0.2)

        return None

    # =========================================================================
    # Schedule Project (F9) — Win32 Backend
    # =========================================================================

    def schedule_project(
        self,
        option: ScheduleOption = ScheduleOption.RETAINED_LOGIC,
        wait_for_completion: bool = True,
    ) -> bool:
        """Run schedule calculation (F9) using the win32 backend.

        Sends ``WM_KEYDOWN(VK_F9)`` to open the Schedule dialog, finds
        and clicks the Schedule button via win32 ``children()``, waits
        for the dialog to close, and checks for circular logic errors.

        Args:
            option: Scheduling logic option (applied if the dialog
                exposes a matching radio button).
            wait_for_completion: Wait for schedule to complete before
                returning (default ``True``).

        Returns:
            ``True`` if scheduled successfully.

        Raises:
            P6SafeModeError: If safe mode is enabled.
            P6ScheduleError: If scheduling fails or a circular logic
                error is detected.
        """
        self._check_safe_mode("Schedule Project")
        self._ensure_win32()

        logger.info("Scheduling project with option: %s", option.value)
        start_time: datetime = datetime.now()

        try:
            # Bring P6 to foreground
            ctypes.windll.user32.SetForegroundWindow(self._win32_handle)
            time.sleep(self.ACTION_DELAY)

            # Send F9 key to open Schedule dialog
            ctypes.windll.user32.PostMessageW(
                self._win32_handle, WM_KEYDOWN, VK_F9, 0
            )
            ctypes.windll.user32.PostMessageW(
                self._win32_handle, WM_KEYUP, VK_F9, 0
            )
            time.sleep(self.ACTION_DELAY)

            # Find the Schedule dialog via win32
            dialog = self._find_dialog(self.SCHEDULE_DIALOG_TITLE)
            if dialog is None:
                raise P6ScheduleError(
                    "Schedule dialog did not appear after F9"
                )
            logger.debug("Schedule dialog opened")

            # Find and click the Schedule button in the dialog
            schedule_clicked: bool = False
            for child in dialog.children():
                try:
                    if child.friendly_class_name() == "Button":
                        btn_text: str = child.window_text()
                        if "schedule" in btn_text.lower():
                            child.click()
                            schedule_clicked = True
                            logger.debug("Clicked Schedule button")
                            break
                except Exception:
                    pass

            if not schedule_clicked:
                # Fallback: click the first OK-like button
                for child in dialog.children():
                    try:
                        if child.friendly_class_name() == "Button":
                            btn_text = child.window_text()
                            if "ok" in btn_text.lower():
                                child.click()
                                schedule_clicked = True
                                logger.debug("Clicked OK button (fallback)")
                                break
                    except Exception:
                        pass

            if not schedule_clicked:
                raise P6ScheduleError(
                    "Could not find Schedule/OK button in dialog"
                )

            if wait_for_completion:
                # Wait for the Schedule dialog to close
                self._wait_for_dialog_close(self.SCHEDULE_DIALOG_TITLE)

                # Check for circular logic error
                error_msg: str | None = self._detect_circular_logic_error()
                if error_msg is not None:
                    raise P6ScheduleError(
                        f"Circular logic detected: {error_msg}"
                    )

                elapsed: float = (
                    datetime.now() - start_time
                ).total_seconds()
                logger.info("Schedule complete in %.1fs", elapsed)

            return True

        except P6SafeModeError:
            raise
        except P6ScheduleError:
            raise
        except Exception as e:
            raise P6ScheduleError(f"Failed to schedule project: {e}") from e

    def _wait_for_dialog_close(
        self,
        title: str,
        timeout: float | None = None,
    ) -> bool:
        """Wait for a dialog to close by polling find_elements.

        Args:
            title: Dialog title to watch for.
            timeout: Maximum seconds to wait (defaults to SCHEDULE_TIMEOUT).

        Returns:
            ``True`` if the dialog closed within the timeout.
        """
        self._ensure_win32()
        timeout = timeout if timeout is not None else self.SCHEDULE_TIMEOUT
        end_time: float = time.time() + timeout

        # Brief initial wait for the scheduling to start
        time.sleep(1.0)

        while time.time() < end_time:
            try:
                elements = find_elements(
                    process=self._p6_pid,
                    title=title,
                    backend="win32",
                    visible_only=True,
                )
                if not elements:
                    return True
            except Exception:
                return True
            time.sleep(1.0)

        logger.warning("Dialog '%s' did not close within %.0fs", title, timeout)
        return False

    def _detect_circular_logic_error(self) -> str | None:
        """Check for a circular logic error dialog after scheduling.

        P6 may display an error dialog listing activities with circular
        logic. This method checks for such a dialog immediately after
        scheduling completes.

        Returns:
            The error message text, or ``None`` if no error dialog found.
        """
        self._ensure_win32()

        # Brief check — circular error appears immediately
        dialog = self._find_dialog_re(
            title_re=r".*[Ee]rror.*|.*[Cc]ircular.*",
            timeout=2.0,
        )
        if dialog is None:
            return None

        # Read the error message from the dialog
        error_text: str = ""
        try:
            for child in dialog.children():
                try:
                    class_name: str = child.friendly_class_name()
                    if class_name in ("Static", "Edit"):
                        text: str = child.window_text().strip()
                        if text:
                            error_text = text
                            break
                except Exception:
                    pass
        except Exception:
            error_text = "Circular logic error detected (details unavailable)"

        # Close the error dialog
        try:
            for child in dialog.children():
                try:
                    if child.friendly_class_name() == "Button":
                        btn_text: str = child.window_text().lower()
                        if "ok" in btn_text or "close" in btn_text:
                            child.click()
                            break
                except Exception:
                    pass
        except Exception:
            pass

        logger.error("Circular logic error: %s", error_text)
        return error_text or "Circular logic error detected"

    def schedule_f9(self) -> bool:
        """Quick F9 schedule with default options.

        Convenience wrapper for :meth:`schedule_project` with
        ``ScheduleOption.RETAINED_LOGIC`` and ``wait_for_completion=True``.

        Returns:
            ``True`` if scheduled successfully.

        Raises:
            P6SafeModeError: If safe mode is enabled.
            P6ScheduleError: If scheduling fails.
        """
        return self.schedule_project(wait_for_completion=True)

    # =========================================================================
    # Resource Leveling (UIA — Phase 3+ scope)
    # =========================================================================

    def level_resources(
        self,
        priority_based: bool = True,
        wait_for_completion: bool = True,
    ) -> bool:
        """Run resource leveling.

        Note:
            Uses UIA backend. Phase 3+ scope — retained as-is.

        Args:
            priority_based: Use priority-based leveling.
            wait_for_completion: Wait for leveling to complete.

        Returns:
            ``True`` if leveled successfully.

        Raises:
            P6SafeModeError: If safe mode is enabled.
            P6ScheduleError: If leveling fails.
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
                self._wait_for_schedule_complete_uia()

            logger.info("Resource leveling complete")
            return True

        except P6SafeModeError:
            raise
        except Exception as e:
            raise P6ScheduleError(f"Failed to level resources: {e}") from e

    # =========================================================================
    # Schedule Check (UIA — Phase 3+ scope)
    # =========================================================================

    def check_schedule(self) -> dict[str, object]:
        """Run schedule check (diagnostics).

        Note:
            Uses UIA backend. Phase 3+ scope — retained as-is.

        Returns:
            Dict with check results summary.
        """
        logger.info("Running schedule check...")

        results: dict[str, object] = {
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

            results['ran'] = True

            # Close dialog
            close_button = dialog.child_window(
                title_re=".*Close.*|.*OK.*",
                control_type="Button"
            )
            if close_button.exists():
                close_button.click_input()

            logger.info("Schedule check complete")

        except Exception as e:
            logger.error("Failed to check schedule: %s", e)
            results['errors'].append(str(e))

        return results

    # =========================================================================
    # Global Change (UIA — Phase 3+ scope)
    # =========================================================================

    def run_global_change(self, change_name: str) -> bool:
        """Run a saved global change.

        Note:
            Uses UIA backend. Phase 3+ scope — retained as-is.

        Args:
            change_name: Name of saved global change.

        Returns:
            ``True`` if run successfully.

        Raises:
            P6SafeModeError: If safe mode is enabled.
        """
        self._check_safe_mode("Global Change")

        logger.info("Running global change: %s", change_name)

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

            logger.info("Global change applied: %s", change_name)
            return True

        except P6SafeModeError:
            raise
        except Exception as e:
            logger.error("Failed to run global change: %s", e)
            return False

    # =========================================================================
    # Status
    # =========================================================================

    def get_schedule_status(self) -> dict[str, object]:
        """Get current schedule status.

        Returns:
            Dict with schedule information.
        """
        return {
            'safe_mode': self.safe_mode,
            'can_schedule': not self.safe_mode
        }

    # =========================================================================
    # Legacy helpers (UIA-based, used by Phase 3+ methods)
    # =========================================================================

    def _wait_for_schedule_complete_uia(
        self, timeout: float | None = None,
    ) -> bool:
        """Wait for schedule calculation to complete (UIA-based).

        Polls for the disappearance of a progress dialog.  Used by the
        legacy UIA methods (``level_resources``, etc.).

        Args:
            timeout: Maximum seconds to wait.

        Returns:
            ``True`` if complete, ``False`` if timed out.
        """
        timeout = timeout if timeout is not None else self.SCHEDULE_TIMEOUT

        def is_complete() -> bool:
            try:
                progress = Desktop(backend="uia").window(
                    title_re=".*Progress.*|.*Scheduling.*|.*Please Wait.*"
                )
                return not progress.exists()
            except Exception:
                return True

        time.sleep(2)

        return wait_for_condition(
            condition=is_complete,
            timeout=timeout,
            poll_interval=2.0,
            description="Schedule completion"
        )


class P6BaselineManager:
    """Manages P6 baselines.

    Provides:
    - Create baselines
    - Assign baselines
    - Maintain baselines

    Note:
        Uses UIA backend. Separate scope — not rewritten for win32.

    Warning:
        Baseline operations modify project data.
    """

    # Dialog patterns
    ASSIGN_BASELINE_TITLE: str = "Assign Baselines"
    MAINTAIN_BASELINE_TITLE: str = "Maintain Baselines"

    # Timing
    DIALOG_TIMEOUT: float = 15.0
    ACTION_DELAY: float = 0.5

    def __init__(self, main_window: object, safe_mode: bool = True) -> None:
        """Initialize baseline manager.

        Args:
            main_window: P6 main window wrapper.
            safe_mode: Prevent destructive operations.
        """
        self._window: object = main_window
        self.safe_mode: bool = safe_mode

        logger.debug("P6BaselineManager initialized")

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
                f"Set safe_mode=False to enable baseline operations."
            )

    def create_baseline(self, baseline_name: str) -> bool:
        """Create a new baseline from current schedule.

        Args:
            baseline_name: Name for new baseline.

        Returns:
            ``True`` if created successfully.

        Raises:
            P6SafeModeError: If safe mode is enabled.
            ValueError: If baseline_name is empty.
        """
        self._check_safe_mode("Create Baseline")

        if not baseline_name or not baseline_name.strip():
            raise ValueError("baseline_name cannot be empty")

        logger.info("Creating baseline: %s", baseline_name)

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

            logger.info("Baseline created: %s", baseline_name)
            return True

        except P6SafeModeError:
            raise
        except Exception as e:
            logger.error("Failed to create baseline: %s", e)
            return False

    def assign_baseline(
        self,
        baseline_name: str,
        baseline_type: str = "Project",
    ) -> bool:
        """Assign a baseline to the project.

        Args:
            baseline_name: Name of baseline to assign.
            baseline_type: Type (Project, Primary, Secondary, etc.).

        Returns:
            ``True`` if assigned successfully.

        Raises:
            P6SafeModeError: If safe mode is enabled.
        """
        self._check_safe_mode("Assign Baseline")

        logger.info("Assigning baseline: %s as %s", baseline_name, baseline_type)

        try:
            self._window.set_focus()

            # Project -> Assign Baselines
            self._window.menu_select("Project->Assign Baselines...")
            time.sleep(self.ACTION_DELAY * 2)

            dialog = Desktop(backend="uia").window(
                title_re=f".*{self.ASSIGN_BASELINE_TITLE}.*"
            )
            dialog.wait("ready", timeout=self.DIALOG_TIMEOUT)

            # TODO: Implement baseline selection in dialog

            # OK
            ok_button = dialog.child_window(
                title="OK",
                control_type="Button"
            )
            ok_button.click_input()

            logger.info("Baseline assigned: %s", baseline_name)
            return True

        except P6SafeModeError:
            raise
        except Exception as e:
            logger.error("Failed to assign baseline: %s", e)
            return False

    def open_maintain_baselines(self) -> bool:
        """Open the Maintain Baselines dialog.

        Returns:
            ``True`` if opened successfully.
        """
        try:
            self._window.set_focus()
            self._window.menu_select("Project->Maintain Baselines...")
            time.sleep(self.ACTION_DELAY * 2)
            return True
        except Exception as e:
            logger.error("Failed to open baseline dialog: %s", e)
            return False
