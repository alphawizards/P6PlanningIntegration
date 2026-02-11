"""
P6 VCL Base Class — Shared Win32/Delphi VCL Infrastructure.

Provides reusable low-level primitives for manipulating Primavera P6
Professional 20's Delphi VCL controls via the win32 backend:

- Thread attachment (cross-process SetFocus)
- Delphi TCDBEdit edit protocol (select-all, type, notify, commit)
- Edit control discovery
- Confirmation dialog handling (background thread)
- Details Form tab selection

Subclasses (P6ActivityEditor, P6RelationshipManager, etc.) inherit
this infrastructure and add domain-specific field discovery and
editing methods.
"""

from __future__ import annotations

import ctypes
import threading
import time
from typing import Optional

from src.utils import logger
from .exceptions import P6EditError

try:
    from pywinauto import Application
    from pywinauto.findwindows import find_elements
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False


# ── Win32 message constants ──────────────────────────────────────────────
EM_SETSEL = 0x00B1
WM_CHAR = 0x0102
WM_COMMAND = 0x0111
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_RETURN = 0x0D
EN_CHANGE = 0x0300
CN_COMMAND = 0xBD11  # Delphi VCL: CN_BASE + WM_COMMAND


class P6VCLBase:
    """Base class providing win32/Delphi VCL infrastructure for P6 automation.

    Encapsulates the low-level mechanics required to drive Primavera P6
    Professional 20 (a Delphi/DevExpress desktop application) from Python:

    * Cross-process thread attachment via ``AttachThreadInput``
    * The Delphi TCDBEdit edit protocol (EM_SETSEL, WM_CHAR, CN_COMMAND, …)
    * Edit-control discovery through ``pywinauto`` win32 children
    * Background-thread handling of P6 Confirmation dialogs
    * Details Form tab selection via ``TcsTabSheet`` controls

    Warning:
        This class is **not** thread-safe.  All callers must ensure
        single-threaded access to P6's window hierarchy.
    """

    # ── Timing constants (seconds) ───────────────────────────────────────
    DIALOG_TIMEOUT: float = 5.0
    ACTION_DELAY: float = 0.2
    VERIFY_DELAY: float = 0.5
    COMMIT_DELAY: float = 1.0
    CHAR_DELAY: float = 0.02

    # ── Initialisation ───────────────────────────────────────────────────

    def __init__(self, main_window: object) -> None:
        """Initialise VCL base with a P6 main window reference.

        Args:
            main_window: P6 main window wrapper (UIA or win32).  Must
                expose a ``.handle`` attribute with the HWND value.
        """
        self._window: object = main_window

        # Win32 backend state
        self._win32_window: object | None = None
        self._win32_handle: int | None = None
        self._p6_thread_id: int | None = None
        self._attached: bool = False

    # ── Win32 connection & thread attachment ──────────────────────────────

    def _ensure_win32(self) -> None:
        """Ensure a win32 backend connection to the P6 main window.

        Connects lazily on first call and caches the result.  Subsequent
        calls are no-ops.

        Raises:
            P6EditError: If the win32 connection cannot be established.
        """
        if self._win32_window is not None:
            return

        try:
            handle: int = self._window.handle
            app = Application(backend="win32").connect(handle=handle)
            self._win32_window = app.window(handle=handle)
            self._win32_handle = handle
            self._p6_thread_id = ctypes.windll.user32.GetWindowThreadProcessId(
                handle, None
            )
            logger.debug("Win32 connection established (handle=%s)", handle)
        except Exception as e:
            logger.error("Failed to establish win32 connection: %s", e)
            raise P6EditError(f"Cannot connect win32 backend: {e}") from e

    def _attach_thread(self) -> None:
        """Attach this thread's input queue to P6's thread.

        Required for cross-process ``SetFocus`` calls.  Idempotent —
        subsequent calls while already attached are no-ops.
        """
        if self._attached:
            return
        self._ensure_win32()
        tid_self: int = ctypes.windll.kernel32.GetCurrentThreadId()
        result: int = ctypes.windll.user32.AttachThreadInput(
            tid_self, self._p6_thread_id, True
        )
        if result:
            self._attached = True
            ctypes.windll.user32.SetForegroundWindow(self._win32_handle)
            time.sleep(self.ACTION_DELAY)
        else:
            logger.warning("AttachThreadInput failed")

    def _detach_thread(self) -> None:
        """Detach this thread's input queue from P6's thread.

        Safe to call even when not attached.
        """
        if not self._attached:
            return
        tid_self: int = ctypes.windll.kernel32.GetCurrentThreadId()
        ctypes.windll.user32.AttachThreadInput(
            tid_self, self._p6_thread_id, False
        )
        self._attached = False

    # ── Delphi VCL edit protocol ─────────────────────────────────────────

    def _edit_control_value(
        self,
        handle: int,
        new_value: str,
        commit_handle: int | None = None,
    ) -> None:
        """Edit a Delphi TCDBEdit control using the VCL message protocol.

        Performs the full edit sequence:

        1. ``SetFocus`` on the target control
        2. ``EM_SETSEL(0, -1)`` — select all existing text
        3. ``WM_CHAR`` for each character of *new_value*
        4. ``CN_COMMAND`` / ``WM_COMMAND`` change notifications
        5. ``WM_KEYDOWN(VK_RETURN)`` to trigger commit
        6. ``SetFocus`` to *commit_handle* to complete the focus change

        Args:
            handle: HWND of the TCDBEdit control to edit.
            new_value: Text to type into the control.
            commit_handle: HWND of another control to receive focus after
                the edit (triggers VCL focus-change commit).  Falls back
                to the main window handle when *None*.
        """
        self._attach_thread()

        if commit_handle is None:
            commit_handle = self._win32_handle

        # 1. SetFocus on target control
        ctypes.windll.user32.SetFocus(handle)
        time.sleep(self.ACTION_DELAY)

        # 2. Select all text
        ctypes.windll.user32.SendMessageW(handle, EM_SETSEL, 0, -1)
        time.sleep(0.1)

        # 3. Type new value character by character
        for ch in new_value:
            ctypes.windll.user32.SendMessageW(handle, WM_CHAR, ord(ch), 0)
            time.sleep(self.CHAR_DELAY)
        time.sleep(self.ACTION_DELAY)

        # 4. Send Delphi VCL change notifications
        ctrl_id: int = ctypes.windll.user32.GetDlgCtrlID(handle)
        parent_handle: int = ctypes.windll.user32.GetParent(handle)
        wparam: int = (EN_CHANGE << 16) | ctrl_id

        ctypes.windll.user32.SendMessageW(
            handle, CN_COMMAND, wparam, handle
        )
        ctypes.windll.user32.SendMessageW(
            parent_handle, WM_COMMAND, wparam, handle
        )

        # 5. Send Enter key to trigger commit
        ctypes.windll.user32.SendMessageW(handle, WM_KEYDOWN, VK_RETURN, 0)
        ctypes.windll.user32.SendMessageW(handle, WM_KEYUP, VK_RETURN, 0)
        time.sleep(self.ACTION_DELAY)

        # 6. Move focus to commit
        ctypes.windll.user32.SetFocus(commit_handle)
        time.sleep(self.COMMIT_DELAY)

    # ── Control discovery ────────────────────────────────────────────────

    def _get_edit_children(self) -> list[tuple[int, object, str]]:
        """Discover all Edit / TCDBEdit child controls in the main window.

        Returns:
            List of ``(child_index, control_wrapper, current_text)``
            tuples for every Edit-class child control.
        """
        self._ensure_win32()
        children = self._win32_window.children()
        edits: list[tuple[int, object, str]] = []
        for i, child in enumerate(children):
            try:
                if child.friendly_class_name() in ("Edit", "TCDBEdit"):
                    text: str = child.window_text()
                    edits.append((i, child, text))
            except Exception:
                pass
        return edits

    # ── Confirmation dialog handling ─────────────────────────────────────

    def _handle_confirmation_dialog(
        self,
        accept: bool = True,
        timeout: float = 5.0,
    ) -> tuple[threading.Thread, dict[str, str | None]]:
        """Start a background watcher for a P6 Confirmation dialog.

        P6 raises modal Confirmation dialogs (e.g. constraint prompts)
        that block the calling thread's ``SendMessage`` calls.  This
        method spawns a daemon thread that polls for the dialog and
        clicks **Yes** or **No**.

        Args:
            accept: ``True`` to click *Yes*, ``False`` to click *No*.
            timeout: Seconds to poll before giving up.

        Returns:
            A ``(thread, result_dict)`` tuple.  *result_dict* has a
            ``'message'`` key set to the dialog text once handled, or
            ``None`` if no dialog appeared.  Join *thread* after the
            edit operation to synchronise.
        """
        pid = ctypes.c_ulong()
        handle: int = self._win32_handle or self._window.handle
        ctypes.windll.user32.GetWindowThreadProcessId(
            handle, ctypes.byref(pid)
        )

        result: dict[str, str | None] = {"message": None}

        def _watcher() -> None:
            end_time: float = time.time() + timeout
            while time.time() < end_time:
                try:
                    elements = find_elements(
                        process=pid.value,
                        title="Confirmation",
                        backend="win32",
                        visible_only=True,
                    )
                    if elements:
                        dialog_handle: int = elements[0].handle
                        dialog_app = Application(backend="win32").connect(
                            handle=dialog_handle
                        )
                        dialog_win = dialog_app.window(handle=dialog_handle)

                        # Read dialog message
                        for child in dialog_win.children():
                            if child.friendly_class_name() in ("Edit", "Static"):
                                msg: str = child.window_text()
                                if msg:
                                    result["message"] = msg
                                    break

                        # Click the appropriate button
                        btn_text: str = "&Yes" if accept else "&No"
                        for child in dialog_win.children():
                            if (
                                child.friendly_class_name() == "Button"
                                and child.window_text() == btn_text
                            ):
                                child.click()
                                logger.info(
                                    "Handled confirmation dialog: %s",
                                    "Yes" if accept else "No",
                                )
                                return
                except Exception:
                    pass
                time.sleep(0.2)

        thread = threading.Thread(target=_watcher, daemon=True)
        thread.start()
        return thread, result

    # ── Tab selection ────────────────────────────────────────────────────

    def _select_details_tab(self, tab_name: str) -> bool:
        """Select a tab in the P6 Details Form by name.

        Searches the main window's children for a ``TcsTabSheet`` whose
        ``window_text()`` matches *tab_name* and clicks just above it
        (the tab header area).

        Args:
            tab_name: Display name of the tab (e.g. ``"Status"``,
                ``"General"``, ``"Relationships"``).

        Returns:
            ``True`` if the tab was found and clicked, ``False`` otherwise.
        """
        self._ensure_win32()
        children = self._win32_window.children()

        for child in children:
            try:
                if (
                    child.friendly_class_name() == "TcsTabSheet"
                    and child.window_text() == tab_name
                ):
                    r = child.rectangle()
                    if PYAUTOGUI_AVAILABLE:
                        pyautogui.click(r.left + 20, r.top - 5)
                    else:
                        child.click_input()
                    time.sleep(self.ACTION_DELAY)
                    logger.debug("Selected %s tab", tab_name)
                    return True
            except Exception:
                pass

        logger.error("Could not find %s tab", tab_name)
        return False
