#!/usr/bin/env python3
"""
Base P6 Automation Class.

Provides core connection, window management, and shared functionality
for all P6 automation operations.
"""

import os
import time
from pathlib import Path
from typing import Optional
from datetime import datetime

try:
    from pywinauto import Application, Desktop
    from pywinauto.findwindows import ElementNotFoundError
    from pywinauto.timings import Timings
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

from src.config import (
    P6_EXECUTABLE_PATH,
    P6_DEFAULT_LAYOUT,
    PDF_PRINTER_NAME,
    PDF_OUTPUT_DIR,
    SAFE_MODE
)
from src.utils import logger
from .exceptions import (
    P6AutomationError,
    P6NotFoundError,
    P6ConnectionError,
    P6TimeoutError,
    P6SafeModeError
)
from .utils import (
    retry,
    wait_for_condition,
    capture_screenshot,
    get_timestamp
)


class P6AutomationBase:
    """
    Base class for P6 Professional GUI automation.
    
    Provides:
    - Connection management
    - Window detection
    - Error handling
    - Screenshot capture
    - Configuration management
    
    Subclasses implement specific automation features.
    
    Warning:
        This class is NOT thread-safe. Do not share instances
        across threads. Create separate instances per thread.
    
    Example:
        with P6AutomationBase() as p6:
            p6.focus_main_window()
            p6.send_keys('^P')  # Ctrl+P
    """
    
    # P6 window patterns
    P6_PROCESS_NAME = "PM.exe"
    P6_TITLE_PATTERN = "Primavera P6"
    
    # Timing defaults (seconds)
    CONNECT_TIMEOUT = 30
    WINDOW_TIMEOUT = 10
    DIALOG_TIMEOUT = 15
    ACTION_DELAY = 0.5
    
    def __init__(
        self,
        p6_path: Optional[str] = None,
        safe_mode: Optional[bool] = None,
        auto_connect: bool = False
    ):
        """
        Initialize P6 Automation base.
        
        Args:
            p6_path: Path to P6 executable (PM.exe)
            safe_mode: Override safe mode setting
            auto_connect: Automatically connect on init
        """
        if not PYWINAUTO_AVAILABLE:
            raise ImportError(
                "pywinauto is required for P6 GUI automation. "
                "Install with: pip install pywinauto"
            )
        
        self.p6_path = Path(p6_path or P6_EXECUTABLE_PATH)
        self.safe_mode = safe_mode if safe_mode is not None else SAFE_MODE
        
        self._app: Optional[Application] = None
        self._main_window = None
        self._connected = False
        self._connection_time: Optional[datetime] = None
        
        # Configure pywinauto timing
        Timings.Fast()
        
        logger.info(f"P6AutomationBase initialized")
        logger.debug(f"  P6 Path: {self.p6_path}")
        logger.debug(f"  Safe Mode: {self.safe_mode}")
        
        if auto_connect:
            self.connect()
    
    # =========================================================================
    # Connection Management
    # =========================================================================
    
    @retry(max_attempts=3, delay=2.0, exceptions=(P6ConnectionError,))
    def connect(self, start_if_not_running: bool = False) -> bool:
        """
        Connect to P6 Professional.
        
        Args:
            start_if_not_running: Start P6 if not already running
            
        Returns:
            True if connected successfully
            
        Raises:
            P6NotFoundError: If P6 is not running
            P6ConnectionError: If connection fails (after retries)
        """
        if self._connected:
            logger.debug("Already connected to P6")
            return True
        
        logger.info("Connecting to P6 Professional...")
        
        try:
            # Try to connect to existing instance
            self._app = Application(backend="uia").connect(
                title_re=f".*{self.P6_TITLE_PATTERN}.*",
                timeout=5
            )
            self._main_window = self._app.window(
                title_re=f".*{self.P6_TITLE_PATTERN}.*"
            )
            self._main_window.wait('ready', timeout=self.WINDOW_TIMEOUT)
            
            self._connected = True
            self._connection_time = datetime.now()
            
            window_title = self._main_window.window_text()
            logger.info(f"✓ Connected to P6: {window_title}")
            return True
            
        except ElementNotFoundError:
            if start_if_not_running:
                return self._start_p6()
            else:
                raise P6NotFoundError(
                    f"P6 Professional is not running. "
                    f"Please start P6 and log in, or set start_if_not_running=True"
                )
        except Exception as e:
            raise P6ConnectionError(f"Failed to connect to P6: {e}")
    
    def _start_p6(self) -> bool:
        """Start P6 Professional application."""
        if not self.p6_path.exists():
            raise P6NotFoundError(f"P6 executable not found: {self.p6_path}")
        
        logger.info(f"Starting P6 from: {self.p6_path}")
        
        try:
            self._app = Application(backend="uia").start(str(self.p6_path))
            
            # Wait for main window
            logger.info("Waiting for P6 to start...")
            time.sleep(5)  # Initial startup delay
            
            self._main_window = self._app.window(
                title_re=f".*{self.P6_TITLE_PATTERN}.*"
            )
            self._main_window.wait('ready', timeout=self.CONNECT_TIMEOUT)
            
            self._connected = True
            self._connection_time = datetime.now()
            
            logger.info(f"✓ P6 started successfully")
            return True
            
        except Exception as e:
            raise P6ConnectionError(f"Failed to start P6: {e}")
    
    def disconnect(self):
        """Disconnect from P6 (does not close P6)."""
        self._app = None
        self._main_window = None
        self._connected = False
        self._connection_time = None
        logger.info("Disconnected from P6")
    
    def is_connected(self) -> bool:
        """Check if currently connected to P6."""
        if not self._connected or not self._app:
            return False
        
        # Verify connection is still valid
        try:
            if self._main_window and self._main_window.exists():
                return True
        except Exception:
            pass
        
        self._connected = False
        return False
    
    def reconnect(self) -> bool:
        """Reconnect to P6 if connection was lost."""
        self.disconnect()
        return self.connect()
    
    # =========================================================================
    # Window Management
    # =========================================================================
    
    @property
    def app(self) -> Application:
        """Get pywinauto Application instance."""
        if not self.is_connected():
            raise P6ConnectionError("Not connected to P6")
        return self._app
    
    @property
    def main_window(self):
        """Get P6 main window wrapper."""
        if not self.is_connected():
            raise P6ConnectionError("Not connected to P6")
        return self._main_window
    
    def focus_main_window(self):
        """Bring P6 main window to foreground."""
        self.main_window.set_focus()
        time.sleep(self.ACTION_DELAY)
    
    def get_window_title(self) -> str:
        """Get current P6 window title."""
        return self.main_window.window_text()
    
    def find_dialog(
        self,
        title: Optional[str] = None,
        title_re: Optional[str] = None,
        timeout: float = None
    ):
        """
        Find a dialog window.
        
        Args:
            title: Exact dialog title
            title_re: Regex pattern for title
            timeout: Wait timeout
            
        Returns:
            Dialog window wrapper
        """
        timeout = timeout or self.DIALOG_TIMEOUT
        
        kwargs = {}
        if title:
            kwargs['title'] = title
        if title_re:
            kwargs['title_re'] = title_re
        
        try:
            dialog = self.app.window(**kwargs)
            dialog.wait('ready', timeout=timeout)
            return dialog
        except Exception as e:
            raise P6TimeoutError(f"Dialog not found: {e}")
    
    # =========================================================================
    # Menu & Keyboard
    # =========================================================================
    
    def select_menu(self, menu_path: str):
        """
        Select a menu item.
        
        Args:
            menu_path: Menu path like "File->Print Preview"
        """
        self.focus_main_window()
        self.main_window.menu_select(menu_path)
        time.sleep(self.ACTION_DELAY)
    
    def send_keys(self, keys: str):
        """
        Send keyboard input.
        
        Args:
            keys: Keys to send (e.g., "^p" for Ctrl+P)
        """
        self.focus_main_window()
        self.main_window.type_keys(keys)
        time.sleep(self.ACTION_DELAY)
    
    # =========================================================================
    # Safety & Error Handling
    # =========================================================================
    
    def check_safe_mode(self, operation: str = "operation"):
        """
        Check if safe mode allows the operation.
        
        Args:
            operation: Description of operation for error message
            
        Raises:
            P6SafeModeError: If safe mode blocks the operation
        """
        if self.safe_mode:
            raise P6SafeModeError(
                f"'{operation}' blocked by SAFE_MODE. "
                f"Set SAFE_MODE=false in .env to enable."
            )
    
    def capture_error_screenshot(self, error_name: str = "error") -> Optional[Path]:
        """
        Capture screenshot on error.
        
        Args:
            error_name: Name for the screenshot file
            
        Returns:
            Path to screenshot or None if failed
        """
        try:
            if self._main_window:
                timestamp = get_timestamp()
                filename = f"p6_error_{error_name}_{timestamp}.png"
                return capture_screenshot(self._main_window, filename)
        except Exception as e:
            logger.warning(f"Failed to capture error screenshot: {e}")
        return None
    
    # =========================================================================
    # Context Manager
    # =========================================================================
    
    def __enter__(self):
        """Context manager entry."""
        if not self._connected:
            self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type:
            # Capture screenshot on error
            self.capture_error_screenshot(exc_type.__name__)
        self.disconnect()
    
    # =========================================================================
    # Status & Info
    # =========================================================================
    
    def get_status(self) -> dict:
        """Get current automation status."""
        return {
            'connected': self.is_connected(),
            'connection_time': self._connection_time.isoformat() if self._connection_time else None,
            'p6_path': str(self.p6_path),
            'safe_mode': self.safe_mode,
            'window_title': self.get_window_title() if self.is_connected() else None
        }
