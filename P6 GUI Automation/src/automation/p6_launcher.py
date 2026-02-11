#!/usr/bin/env python3
"""
P6 Launcher - Automates P6 Professional startup and login.

This module handles:
1. Clicking P6 icon in taskbar
2. Waiting for login dialog
3. Entering credentials
4. Handling warning dialogs (Industry not selected)
5. Waiting for main window to load

Usage:
    from src.automation.p6_launcher import P6Launcher

    launcher = P6Launcher()
    main_window = launcher.launch_and_login(password="admin")
"""

import time
import subprocess
from typing import Optional, Tuple
from pathlib import Path

try:
    import pywinauto
    from pywinauto import Application, Desktop
    from pywinauto.keyboard import send_keys
    from pywinauto.findwindows import ElementNotFoundError
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False
    print("WARNING: pywinauto not installed")

# Logging
try:
    from src.utils import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG)


class P6LaunchError(Exception):
    """Error during P6 launch/login process."""
    pass


class P6Launcher:
    """
    Automates P6 Professional startup and login sequence.

    Handles the complete startup flow:
    1. Launch P6 from taskbar or Start Menu
    2. Wait for login dialog
    3. Enter username/password
    4. Click Connect
    5. Handle warning dialogs (Industry preference, etc.)
    6. Wait for main Activities window
    """

    # Timing constants
    CLICK_DELAY = 0.5
    DIALOG_TIMEOUT = 30  # seconds
    MAIN_WINDOW_TIMEOUT = 60  # seconds (P6 can be slow to load)

    # P6 window title patterns
    LOGIN_TITLE = "P6 Professional"
    MAIN_TITLE_PATTERN = "Primavera P6 Professional"
    WARNING_TITLE = "Primavera P6 Professional"

    # Default P6 installation paths
    P6_PATHS = [
        r"C:\Program Files\Oracle\Primavera P6\P6 Professional\20.12.0\PM.exe",  # P6 20.12
        r"C:\Program Files\Oracle\Primavera P6\P6 Professional\PM.exe",
        r"C:\Program Files (x86)\Oracle\Primavera P6\P6 Professional\PM.exe",
        r"C:\Oracle\P6Professional\PM.exe",
    ]

    def __init__(self, username: str = "ADMIN"):
        """
        Initialize P6 Launcher.

        Args:
            username: P6 login username (default: ADMIN)
        """
        if not PYWINAUTO_AVAILABLE:
            raise RuntimeError("pywinauto is required for P6 automation")

        self.username = username
        self._desktop = Desktop(backend="uia")
        self._app = None
        self._main_window = None

        logger.info(f"P6Launcher initialized (username={username})")

    def is_p6_running(self) -> bool:
        """Check if P6 is already running."""
        try:
            windows = self._desktop.windows()
            for win in windows:
                try:
                    title = win.window_text()
                    if self.MAIN_TITLE_PATTERN in title or self.LOGIN_TITLE in title:
                        return True
                except Exception:
                    continue
            return False
        except Exception as e:
            logger.warning(f"Error checking if P6 is running: {e}")
            return False

    def find_p6_executable(self) -> Optional[str]:
        """Find P6 executable path."""
        for path in self.P6_PATHS:
            if Path(path).exists():
                logger.info(f"Found P6 at: {path}")
                return path
        return None

    def launch_from_executable(self, exe_path: Optional[str] = None) -> bool:
        """
        Launch P6 from executable path.

        Args:
            exe_path: Path to PM.exe (auto-detect if None)

        Returns:
            True if launched successfully
        """
        if exe_path is None:
            exe_path = self.find_p6_executable()

        if exe_path is None:
            logger.error("Could not find P6 executable")
            return False

        try:
            logger.info(f"Launching P6 from: {exe_path}")
            subprocess.Popen([exe_path])
            time.sleep(5.0)  # Wait longer for P6 to start (it can be slow)
            return True
        except Exception as e:
            logger.error(f"Failed to launch P6: {e}")
            return False

    def launch_from_taskbar(self) -> bool:
        """
        Launch P6 by clicking taskbar icon.

        Note: This requires the P6 icon to be pinned to taskbar.
        Uses keyboard shortcut Win+T to navigate taskbar.

        Returns:
            True if click was sent (doesn't guarantee P6 launched)
        """
        try:
            logger.info("Attempting to launch P6 from taskbar...")

            # Method 1: Use pywinauto to find taskbar and P6 button
            taskbar = self._desktop.window(class_name="Shell_TrayWnd")

            # Find the P6 button in taskbar
            # Look for button with P6 in name or tooltip
            try:
                # Navigate through taskbar structure
                task_list = taskbar.child_window(class_name="MSTaskListWClass")

                # Try to find P6 button by automation_id or name
                buttons = task_list.children()
                for btn in buttons:
                    try:
                        name = btn.window_text().lower()
                        if "p6" in name or "primavera" in name:
                            logger.info(f"Found P6 taskbar button: {btn.window_text()}")
                            btn.click_input()
                            time.sleep(1.0)
                            return True
                    except Exception:
                        continue

                logger.warning("P6 button not found in taskbar")

            except Exception as e:
                logger.warning(f"Could not access taskbar buttons: {e}")

            # Method 2: Fallback - use Start Menu search
            logger.info("Trying Start Menu search as fallback...")
            send_keys("{VK_LWIN}")  # Press Windows key
            time.sleep(0.5)
            send_keys("P6 Professional")  # Type search
            time.sleep(1.0)
            send_keys("{ENTER}")  # Launch first result
            time.sleep(2.0)

            return True

        except Exception as e:
            logger.error(f"Failed to launch from taskbar: {e}")
            return False

    def wait_for_login_dialog(self, timeout: int = None) -> Optional[object]:
        """
        Wait for P6 login dialog to appear.

        Args:
            timeout: Max seconds to wait

        Returns:
            Login dialog window or None
        """
        timeout = timeout or self.DIALOG_TIMEOUT
        logger.info(f"Waiting for P6 login dialog (timeout={timeout}s)...")

        # Title patterns to try (P6 versions use different titles)
        title_patterns = [
            "P6 Professional 20",      # Exact title from screenshot
            "P6 Professional",         # Generic
            ".*P6 Professional.*",     # Regex
            ".*P6.*Professional.*",    # Flexible regex
        ]

        start_time = time.time()
        attempt = 0
        while time.time() - start_time < timeout:
            attempt += 1

            # Debug: List all visible windows every 5 seconds
            if attempt % 10 == 1:
                logger.debug("Scanning for windows...")
                try:
                    for win in self._desktop.windows():
                        try:
                            title = win.window_text()
                            if title and ("P6" in title or "Primavera" in title or "Oracle" in title):
                                logger.info(f"  Found window: '{title}'")
                        except Exception:
                            pass
                except Exception:
                    pass

            # Try each title pattern
            for pattern in title_patterns:
                try:
                    if pattern.startswith(".*"):
                        # Regex pattern
                        login_win = self._desktop.window(
                            title_re=pattern,
                            visible_only=True
                        )
                    else:
                        # Exact match
                        login_win = self._desktop.window(
                            title=pattern,
                            visible_only=True
                        )

                    if login_win.exists():
                        title = login_win.window_text()
                        logger.info(f"Found potential login window: '{title}'")

                        # Verify it's the login dialog (has Password field or Connect button)
                        try:
                            # Try to find Password label or Connect button
                            try:
                                login_win.child_window(title="Password", control_type="Text")
                                logger.info("Login dialog confirmed (found Password label)")
                                return login_win
                            except ElementNotFoundError:
                                pass

                            try:
                                login_win.child_window(title="Connect", control_type="Button")
                                logger.info("Login dialog confirmed (found Connect button)")
                                return login_win
                            except ElementNotFoundError:
                                pass

                            try:
                                login_win.child_window(title="Login Name", control_type="Text")
                                logger.info("Login dialog confirmed (found Login Name label)")
                                return login_win
                            except ElementNotFoundError:
                                pass

                        except Exception as e:
                            logger.debug(f"Error checking login dialog contents: {e}")

                except Exception:
                    pass

            time.sleep(0.5)

        logger.error("Login dialog not found within timeout")
        return None

    def enter_credentials(self, login_dialog, password: str) -> bool:
        """
        Enter username and password in login dialog.

        Args:
            login_dialog: The login dialog window
            password: Password to enter

        Returns:
            True if credentials entered successfully
        """
        try:
            logger.info(f"Entering credentials for user: {self.username}")

            # The username field should already have ADMIN
            # Find the password field and enter password

            # Method 1: Find by control type
            try:
                password_field = login_dialog.child_window(
                    control_type="Edit",
                    found_index=1  # Second edit field (first is username)
                )
                password_field.set_focus()
                time.sleep(0.2)
                password_field.type_keys(password, with_spaces=True)
                logger.info("Password entered via Edit control")
                return True
            except Exception as e:
                logger.debug(f"Method 1 failed: {e}")

            # Method 2: Tab to password field
            try:
                login_dialog.set_focus()
                time.sleep(0.2)
                send_keys("{TAB}")  # Move to password field
                time.sleep(0.2)
                send_keys(password)
                logger.info("Password entered via TAB navigation")
                return True
            except Exception as e:
                logger.debug(f"Method 2 failed: {e}")

            logger.error("Could not enter password")
            return False

        except Exception as e:
            logger.error(f"Failed to enter credentials: {e}")
            return False

    def click_connect(self, login_dialog) -> bool:
        """
        Click the Connect button in login dialog.

        Args:
            login_dialog: The login dialog window

        Returns:
            True if Connect clicked successfully
        """
        try:
            logger.info("Clicking Connect button...")

            # Find Connect button
            connect_btn = login_dialog.child_window(
                title="Connect",
                control_type="Button"
            )

            connect_btn.click_input()
            time.sleep(self.CLICK_DELAY)

            logger.info("Connect button clicked")
            return True

        except ElementNotFoundError:
            # Try pressing Enter as alternative
            try:
                login_dialog.set_focus()
                send_keys("{ENTER}")
                logger.info("Pressed ENTER to submit login")
                return True
            except Exception:
                pass

            logger.error("Connect button not found")
            return False
        except Exception as e:
            logger.error(f"Failed to click Connect: {e}")
            return False

    def handle_warning_dialogs(self, timeout: int = 10) -> bool:
        """
        Handle any warning dialogs that appear after login.

        Specifically handles:
        - "Industry for your organization has not been selected" warning
        - Other P6 startup warnings

        Args:
            timeout: Max seconds to wait for dialogs

        Returns:
            True if handled successfully (or no dialogs appeared)
        """
        logger.info("Checking for warning dialogs...")

        start_time = time.time()
        dialogs_handled = 0

        while time.time() - start_time < timeout:
            try:
                # Look for warning/message dialogs
                warning_dialog = self._desktop.window(
                    title=self.WARNING_TITLE,
                    control_type="Window",
                    visible_only=True
                )

                # Check if it's a warning dialog (has OK button and warning text)
                try:
                    ok_btn = warning_dialog.child_window(
                        title="OK",
                        control_type="Button"
                    )

                    if ok_btn.exists():
                        # Check for the Industry warning text
                        try:
                            warning_text = warning_dialog.window_text()
                            logger.info(f"Found warning dialog: {warning_text[:100]}...")
                        except Exception:
                            logger.info("Found warning dialog")

                        ok_btn.click_input()
                        time.sleep(self.CLICK_DELAY)
                        dialogs_handled += 1
                        logger.info(f"Clicked OK on warning dialog #{dialogs_handled}")
                        continue

                except ElementNotFoundError:
                    pass

            except ElementNotFoundError:
                # No warning dialog found - check if main window appeared
                if self._check_main_window_exists():
                    logger.info(f"Main window detected. Handled {dialogs_handled} warning dialogs.")
                    return True

            except Exception as e:
                logger.debug(f"Error checking for dialogs: {e}")

            time.sleep(0.5)

        logger.info(f"Warning dialog check complete. Handled {dialogs_handled} dialogs.")
        return True

    def _check_main_window_exists(self) -> bool:
        """Check if P6 main window exists."""
        try:
            main_win = self._desktop.window(
                title_re=f".*{self.MAIN_TITLE_PATTERN}.*:.*",  # Pattern: "Primavera P6 Professional 20 : 1282-2 (Project Name)"
                visible_only=True
            )
            return main_win.exists()
        except Exception:
            return False

    def wait_for_main_window(self, timeout: int = None) -> Optional[object]:
        """
        Wait for P6 main window (Activities view) to load.

        Args:
            timeout: Max seconds to wait

        Returns:
            Main window or None
        """
        timeout = timeout or self.MAIN_WINDOW_TIMEOUT
        logger.info(f"Waiting for P6 main window (timeout={timeout}s)...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # P6 main window title format: "Primavera P6 Professional 20 : [ProjectID] ([ProjectName])"
                main_win = self._desktop.window(
                    title_re=f".*{self.MAIN_TITLE_PATTERN}.*",
                    visible_only=True
                )

                # Verify it's the main window (not login dialog)
                title = main_win.window_text()
                if ":" in title and "Professional" in title:
                    # Additional check: look for Activities toolbar or menu
                    try:
                        # Check for File menu (indicates main window)
                        main_win.child_window(title="File", control_type="MenuItem")
                        logger.info(f"Main window ready: {title}")
                        self._main_window = main_win
                        return main_win
                    except ElementNotFoundError:
                        pass

            except ElementNotFoundError:
                pass
            except Exception as e:
                logger.debug(f"Error waiting for main window: {e}")

            time.sleep(1.0)

        logger.error("Main window not found within timeout")
        return None

    def launch_and_login(
        self,
        password: str = "admin",
        use_taskbar: bool = False,
        exe_path: Optional[str] = None
    ) -> Optional[object]:
        """
        Complete P6 launch and login sequence.

        This is the main entry point that handles the full flow:
        1. Check if P6 is already running
        2. Launch P6 (from taskbar or executable)
        3. Wait for login dialog
        4. Enter credentials
        5. Click Connect
        6. Handle warning dialogs
        7. Wait for main window

        Args:
            password: P6 password
            use_taskbar: If True, try clicking taskbar icon first
            exe_path: Path to PM.exe (optional)

        Returns:
            P6 main window handle, or None if failed
        """
        logger.info("=" * 60)
        logger.info("Starting P6 Launch and Login Sequence")
        logger.info("=" * 60)

        # Step 1: Check if already running
        if self.is_p6_running():
            logger.info("P6 is already running")
            # Try to find main window
            main_window = self.wait_for_main_window(timeout=5)
            if main_window:
                return main_window
            # If not main window, might be login dialog
            login_dialog = self.wait_for_login_dialog(timeout=5)
            if login_dialog:
                logger.info("Found existing login dialog")
            else:
                logger.warning("P6 running but no window found - launching anyway")

        # Step 2: Launch P6
        else:
            if use_taskbar:
                if not self.launch_from_taskbar():
                    logger.warning("Taskbar launch failed, trying executable...")
                    if not self.launch_from_executable(exe_path):
                        raise P6LaunchError("Failed to launch P6")
            else:
                if not self.launch_from_executable(exe_path):
                    logger.warning("Executable launch failed, trying taskbar...")
                    if not self.launch_from_taskbar():
                        raise P6LaunchError("Failed to launch P6")

        # Step 3: Wait for login dialog
        login_dialog = self.wait_for_login_dialog()
        if not login_dialog:
            # Maybe P6 was already logged in?
            main_window = self.wait_for_main_window(timeout=10)
            if main_window:
                logger.info("P6 appears to be already logged in")
                return main_window
            raise P6LaunchError("Login dialog not found")

        # Step 4: Enter credentials
        if not self.enter_credentials(login_dialog, password):
            raise P6LaunchError("Failed to enter credentials")

        # Step 5: Click Connect
        if not self.click_connect(login_dialog):
            raise P6LaunchError("Failed to click Connect")

        # Step 6: Handle warning dialogs
        time.sleep(2.0)  # Brief wait for dialogs to appear
        self.handle_warning_dialogs()

        # Step 7: Wait for main window
        main_window = self.wait_for_main_window()
        if not main_window:
            raise P6LaunchError("Main window did not load")

        logger.info("=" * 60)
        logger.info("P6 Launch and Login Complete!")
        logger.info("=" * 60)

        return main_window

    def get_main_window(self):
        """Get the cached main window handle."""
        return self._main_window


# =============================================================================
# Convenience Functions
# =============================================================================

def launch_p6(password: str = "admin", username: str = "ADMIN") -> Optional[object]:
    """
    Convenience function to launch and login to P6.

    Args:
        password: P6 password
        username: P6 username

    Returns:
        P6 main window handle
    """
    launcher = P6Launcher(username=username)
    return launcher.launch_and_login(password=password)


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """
    Command-line interface for P6 launcher.

    Usage:
        python p6_launcher.py [--password PASSWORD] [--username USERNAME]
    """
    import argparse

    parser = argparse.ArgumentParser(description="Launch and login to P6 Professional")
    parser.add_argument("--password", "-p", default="admin", help="P6 password")
    parser.add_argument("--username", "-u", default="ADMIN", help="P6 username")
    parser.add_argument("--taskbar", action="store_true", help="Try taskbar click first")
    parser.add_argument("--exe", help="Path to PM.exe")

    args = parser.parse_args()

    print("=" * 60)
    print("P6 Professional Launcher")
    print("=" * 60)
    print(f"Username: {args.username}")
    print(f"Password: {'*' * len(args.password)}")
    print()

    try:
        launcher = P6Launcher(username=args.username)
        main_window = launcher.launch_and_login(
            password=args.password,
            use_taskbar=args.taskbar,
            exe_path=args.exe
        )

        if main_window:
            print("\nSUCCESS! P6 is ready.")
            print(f"Window: {main_window.window_text()}")
        else:
            print("\nFAILED: Could not launch P6")

    except P6LaunchError as e:
        print(f"\nERROR: {e}")
    except Exception as e:
        print(f"\nUNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
