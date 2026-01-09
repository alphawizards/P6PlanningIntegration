#!/usr/bin/env python3
"""
P6 Connection Management Module.

Provides advanced connection features:
- Process detection and enumeration
- Login dialog automation
- Session management
- Connection health monitoring
"""

import os
import time
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from datetime import datetime

try:
    from pywinauto import Application, Desktop
    from pywinauto.findwindows import (
        ElementNotFoundError,
        find_windows,
        find_elements
    )
    from pywinauto.timings import Timings
    import psutil
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False
    psutil = None

from src.config import (
    P6_EXECUTABLE_PATH,
    P6_USER,
    P6_PASS,
    SAFE_MODE
)
from src.utils import logger
from ..exceptions import (
    P6NotFoundError,
    P6ConnectionError,
    P6LoginError,
    P6TimeoutError
)
from ..utils import (
    retry,
    wait_for_condition,
    get_timestamp
)


class P6ConnectionManager:
    """
    Manages P6 Professional process detection and connection.
    
    Provides:
    - Find running P6 instances
    - Start P6 if not running
    - Handle login dialogs
    - Monitor connection health
    
    Warning:
        This class is NOT thread-safe. Create separate instances per thread.
    """
    
    # P6 process identifiers
    P6_PROCESS_NAME = "PM.exe"
    P6_WINDOW_TITLE = "Primavera P6"
    P6_LOGIN_TITLE = "Login"
    P6_DATABASE_TITLE = "Select Database"
    
    # Timing defaults
    STARTUP_TIMEOUT = 60  # P6 can take a while to start
    LOGIN_TIMEOUT = 30
    DIALOG_WAIT = 2.0
    
    def __init__(
        self,
        p6_path: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize connection manager.
        
        Args:
            p6_path: Path to P6 executable (PM.exe)
            username: P6 username (uses config if not provided)
            password: P6 password (uses config if not provided)
        """
        if not PYWINAUTO_AVAILABLE:
            raise ImportError(
                "pywinauto and psutil required. "
                "Install with: pip install pywinauto psutil"
            )
        
        self.p6_path = Path(p6_path or P6_EXECUTABLE_PATH)
        self.username = username or P6_USER
        self.password = password or P6_PASS
        
        self._process: Optional[psutil.Process] = None
        self._app: Optional[Application] = None
        
        logger.debug(f"P6ConnectionManager initialized")
    
    # =========================================================================
    # Process Detection
    # =========================================================================
    
    def find_p6_processes(self) -> List[Dict]:
        """
        Find all running P6 Professional processes.
        
        Returns:
            List of dicts with process info: {pid, name, path, status, create_time}
        """
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'status', 'create_time']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == self.P6_PROCESS_NAME.lower():
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'path': proc.info['exe'],
                        'status': proc.info['status'],
                        'create_time': datetime.fromtimestamp(proc.info['create_time'])
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        logger.debug(f"Found {len(processes)} P6 process(es)")
        return processes
    
    def is_p6_running(self) -> bool:
        """Check if at least one P6 process is running."""
        return len(self.find_p6_processes()) > 0
    
    def get_p6_pid(self) -> Optional[int]:
        """
        Get PID of the first running P6 process.
        
        Returns:
            Process ID or None if not running
        """
        processes = self.find_p6_processes()
        if processes:
            return processes[0]['pid']
        return None
    
    def get_p6_windows(self) -> List[Dict]:
        """
        Find all P6 windows.
        
        Returns:
            List of dicts with window info: {handle, title, class_name, pid}
        """
        windows = []
        
        try:
            # Find all P6 windows
            handles = find_windows(title_re=f".*{self.P6_WINDOW_TITLE}.*")
            
            for handle in handles:
                try:
                    # Get window info
                    from pywinauto.controls.hwndwrapper import HwndWrapper
                    wrapper = HwndWrapper(handle)
                    windows.append({
                        'handle': handle,
                        'title': wrapper.window_text(),
                        'class_name': wrapper.class_name(),
                        'visible': wrapper.is_visible()
                    })
                except Exception:
                    continue
                    
        except Exception as e:
            logger.debug(f"Error finding P6 windows: {e}")
        
        logger.debug(f"Found {len(windows)} P6 window(s)")
        return windows
    
    # =========================================================================
    # Process Management
    # =========================================================================
    
    def start_p6(self, wait_for_main: bool = True) -> bool:
        """
        Start P6 Professional application.
        
        Args:
            wait_for_main: Wait for main window to appear
            
        Returns:
            True if started successfully
            
        Raises:
            P6NotFoundError: If executable not found
            P6ConnectionError: If failed to start
        """
        if not self.p6_path.exists():
            raise P6NotFoundError(f"P6 executable not found: {self.p6_path}")
        
        logger.info(f"Starting P6 from: {self.p6_path}")
        
        try:
            # Start process
            self._app = Application(backend="uia").start(
                str(self.p6_path),
                timeout=self.STARTUP_TIMEOUT
            )
            
            # Store process reference
            self._process = psutil.Process(self._app.process)
            logger.debug(f"P6 started with PID: {self._process.pid}")
            
            if wait_for_main:
                # Wait for either login dialog or main window
                logger.info("Waiting for P6 to initialize...")
                
                if not self._wait_for_p6_ready():
                    raise P6ConnectionError("P6 did not become ready in time")
            
            logger.info("✓ P6 started successfully")
            return True
            
        except Exception as e:
            raise P6ConnectionError(f"Failed to start P6: {e}")
    
    def _wait_for_p6_ready(self, timeout: float = None) -> bool:
        """Wait for P6 to show login or main window."""
        timeout = timeout or self.STARTUP_TIMEOUT
        
        def check_ready():
            # Check for login dialog
            try:
                login_wins = find_windows(title_re=f".*{self.P6_LOGIN_TITLE}.*")
                if login_wins:
                    return True
            except Exception:
                pass
            
            # Check for main window
            try:
                main_wins = find_windows(title_re=f".*{self.P6_WINDOW_TITLE}.*")
                if main_wins:
                    return True
            except Exception:
                pass
            
            return False
        
        return wait_for_condition(
            condition=check_ready,
            timeout=timeout,
            poll_interval=1.0,
            description="P6 ready"
        )
    
    def kill_p6(self, force: bool = False) -> bool:
        """
        Kill P6 process.
        
        Args:
            force: Use SIGKILL instead of SIGTERM
            
        Returns:
            True if killed successfully
        """
        processes = self.find_p6_processes()
        
        for proc_info in processes:
            try:
                proc = psutil.Process(proc_info['pid'])
                if force:
                    proc.kill()
                else:
                    proc.terminate()
                logger.info(f"Killed P6 process: {proc_info['pid']}")
            except psutil.NoSuchProcess:
                continue
            except Exception as e:
                logger.error(f"Failed to kill PID {proc_info['pid']}: {e}")
                return False
        
        return True
    
    # =========================================================================
    # Login Automation
    # =========================================================================
    
    def handle_login(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = None
    ) -> bool:
        """
        Handle P6 login dialog if present.
        
        Args:
            username: Override username
            password: Override password
            timeout: Wait timeout for login dialog
            
        Returns:
            True if login successful or no login needed
            
        Raises:
            P6LoginError: If login fails
        """
        username = username or self.username
        password = password or self.password
        timeout = timeout or self.LOGIN_TIMEOUT
        
        logger.info("Checking for login dialog...")
        
        try:
            # Find login window
            login_window = Desktop(backend="uia").window(
                title_re=f".*{self.P6_LOGIN_TITLE}.*"
            )
            
            if not login_window.exists():
                logger.debug("No login dialog found (may already be logged in)")
                return True
            
            login_window.wait("ready", timeout=5)
            logger.info("Login dialog detected, entering credentials...")
            
            # Find username field
            try:
                username_field = login_window.child_window(
                    control_type="Edit",
                    found_index=0
                )
                username_field.set_text(username)
                logger.debug(f"Entered username: {username}")
                time.sleep(0.5)
            except Exception as e:
                raise P6LoginError(f"Could not find username field: {e}")
            
            # Find password field
            try:
                password_field = login_window.child_window(
                    control_type="Edit",
                    found_index=1
                )
                password_field.set_text(password)
                logger.debug("Entered password")
                time.sleep(0.5)
            except Exception as e:
                raise P6LoginError(f"Could not find password field: {e}")
            
            # Click Login button
            try:
                login_button = login_window.child_window(
                    title_re=".*Log[Ii]n.*|.*OK.*",
                    control_type="Button"
                )
                login_button.click_input()
                logger.debug("Clicked Login button")
            except Exception as e:
                raise P6LoginError(f"Could not find Login button: {e}")
            
            # Wait for login to complete
            time.sleep(self.DIALOG_WAIT)
            
            # Check if login succeeded (dialog should close)
            if login_window.exists():
                # Check for error message
                try:
                    error_text = login_window.child_window(
                        control_type="Text"
                    ).window_text()
                    if "error" in error_text.lower() or "invalid" in error_text.lower():
                        raise P6LoginError(f"Login failed: {error_text}")
                except Exception:
                    pass
                
                raise P6LoginError("Login dialog still visible after login attempt")
            
            logger.info("✓ Login successful")
            return True
            
        except P6LoginError:
            raise
        except ElementNotFoundError:
            logger.debug("No login dialog present")
            return True
        except Exception as e:
            raise P6LoginError(f"Login error: {e}")
    
    def handle_database_selection(self, database_name: Optional[str] = None) -> bool:
        """
        Handle database selection dialog if present.
        
        Args:
            database_name: Database to select (uses first if not specified)
            
        Returns:
            True if handled successfully
        """
        logger.debug("Checking for database selection dialog...")
        
        try:
            db_window = Desktop(backend="uia").window(
                title_re=f".*{self.P6_DATABASE_TITLE}.*"
            )
            
            if not db_window.exists():
                return True
            
            db_window.wait("ready", timeout=5)
            logger.info("Database selection dialog detected")
            
            if database_name:
                # TODO: Select specific database from list
                pass
            
            # Click OK to accept default/selected database
            ok_button = db_window.child_window(
                title="OK",
                control_type="Button"
            )
            ok_button.click_input()
            
            time.sleep(self.DIALOG_WAIT)
            logger.info("✓ Database selected")
            return True
            
        except ElementNotFoundError:
            return True
        except Exception as e:
            logger.warning(f"Database selection error: {e}")
            return False
    
    # =========================================================================
    # Connection Status
    # =========================================================================
    
    def get_connection_status(self) -> Dict:
        """
        Get current P6 connection status.
        
        Returns:
            Dict with status information
        """
        processes = self.find_p6_processes()
        windows = self.get_p6_windows()
        
        return {
            'running': len(processes) > 0,
            'process_count': len(processes),
            'window_count': len(windows),
            'pids': [p['pid'] for p in processes],
            'windows': [w['title'] for w in windows],
            'ready': any(self.P6_WINDOW_TITLE in w.get('title', '') for w in windows)
        }
    
    def wait_for_main_window(self, timeout: float = None) -> bool:
        """
        Wait for P6 main window to appear.
        
        Args:
            timeout: Maximum wait time
            
        Returns:
            True if main window appeared
        """
        timeout = timeout or self.STARTUP_TIMEOUT
        
        def has_main_window():
            windows = self.get_p6_windows()
            # Main window should have project info, not just login
            for w in windows:
                title = w.get('title', '')
                if self.P6_WINDOW_TITLE in title and self.P6_LOGIN_TITLE not in title:
                    return True
            return False
        
        return wait_for_condition(
            condition=has_main_window,
            timeout=timeout,
            description="P6 main window"
        )


# Convenience functions for standalone use
def detect_p6() -> Optional[int]:
    """Find running P6 and return its PID, or None."""
    manager = P6ConnectionManager()
    return manager.get_p6_pid()


def is_p6_running() -> bool:
    """Check if P6 is running."""
    manager = P6ConnectionManager()
    return manager.is_p6_running()


def start_and_login(
    username: Optional[str] = None,
    password: Optional[str] = None
) -> bool:
    """
    Start P6 and log in.
    
    Args:
        username: P6 username
        password: P6 password
        
    Returns:
        True if P6 is running and logged in
    """
    manager = P6ConnectionManager()
    
    if not manager.is_p6_running():
        manager.start_p6()
    
    manager.handle_login(username, password)
    manager.handle_database_selection()
    
    return manager.wait_for_main_window()
