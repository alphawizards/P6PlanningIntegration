#!/usr/bin/env python3
"""
P6 Navigation Module.

Provides navigation automation for P6 Professional:
- Menu navigation
- Toolbar interaction
- Status bar reading
- View switching
"""

import time
import re
from typing import Optional, Dict, List, Tuple
from datetime import datetime

try:
    from pywinauto import Application, Desktop
    from pywinauto.findwindows import ElementNotFoundError
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

from src.utils import logger
from .exceptions import (
    P6WindowNotFoundError,
    P6TimeoutError
)
from .utils import (
    retry,
    wait_for_condition
)


class P6Navigator:
    """
    Handles P6 window navigation, menus, toolbars, and status bar.
    
    This class should be used with an existing P6 connection.
    It operates on the main P6 window.
    
    Warning:
        This class is NOT thread-safe.
    """
    
    # Menu paths for common operations
    MENU_PATHS = {
        # File menu
        'new_project': 'File->New->Project...',
        'open': 'File->Open',
        'close': 'File->Close',
        'close_all': 'File->Close All',
        'print': 'File->Print...',
        'print_preview': 'File->Print Preview',
        'exit': 'File->Exit',
        
        # Edit menu
        'undo': 'Edit->Undo',
        'redo': 'Edit->Redo',
        'cut': 'Edit->Cut',
        'copy': 'Edit->Copy',
        'paste': 'Edit->Paste',
        'select_all': 'Edit->Select All',
        'find': 'Edit->Find...',
        
        # View menu
        'layout_open': 'View->Layout->Open...',
        'layout_save': 'View->Layout->Save',
        'layout_save_as': 'View->Layout->Save As...',
        'group_sort': 'View->Group and Sort...',
        'filter': 'View->Filter...',
        'columns': 'View->Columns...',
        'refresh': 'View->Refresh',
        
        # Project menu
        'schedule': 'Project->Schedule...',
        'level_resources': 'Project->Level Resources...',
        'assign_baselines': 'Project->Assign Baselines...',
        'maintain_baselines': 'Project->Maintain Baselines...',
        'store_period': 'Project->Store Period Performance...',
        
        # Tools menu
        'global_change': 'Tools->Global Change...',
        'check_schedule': 'Tools->Check Schedule...',
        'import': 'Tools->Import...',
        'export': 'Tools->Export...',
        
        # Help menu
        'about': 'Help->About Primavera P6...'
    }
    
    # Keyboard shortcuts for common operations
    SHORTCUTS = {
        'save': '^S',           # Ctrl+S
        'undo': '^Z',           # Ctrl+Z
        'redo': '^Y',           # Ctrl+Y
        'print': '^P',          # Ctrl+P
        'find': '^F',           # Ctrl+F
        'refresh': '{F5}',      # F5
        'schedule': '{F9}',     # F9 (Schedule)
        'help': '{F1}',         # F1
        'close': '^{F4}',       # Ctrl+F4
        'exit': '%{F4}',        # Alt+F4
    }
    
    # Timing
    MENU_DELAY = 0.3
    ACTION_DELAY = 0.5
    
    def __init__(self, main_window):
        """
        Initialize navigator with P6 main window.
        
        Args:
            main_window: pywinauto window wrapper for P6 main window
        """
        self._window = main_window
        logger.debug("P6Navigator initialized")
    
    @property
    def window(self):
        """Get the P6 main window."""
        return self._window
    
    # =========================================================================
    # Menu Navigation
    # =========================================================================
    
    def select_menu(self, menu_path: str) -> bool:
        """
        Select a menu item by path.
        
        Args:
            menu_path: Menu path like "File->Print Preview" or shortcut name
            
        Returns:
            True if menu selected successfully
            
        Example:
            navigator.select_menu("File->Print Preview")
            navigator.select_menu("print_preview")  # Using shortcut name
        """
        # Resolve shortcut name to full path
        if menu_path in self.MENU_PATHS:
            menu_path = self.MENU_PATHS[menu_path]
        
        logger.debug(f"Selecting menu: {menu_path}")
        
        try:
            self._window.set_focus()
            time.sleep(self.ACTION_DELAY)
            
            self._window.menu_select(menu_path)
            time.sleep(self.MENU_DELAY)
            
            logger.info(f"✓ Menu selected: {menu_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to select menu '{menu_path}': {e}")
            return False
    
    def select_menu_by_keys(self, *keys: str) -> bool:
        """
        Navigate menus using keyboard shortcuts.
        
        Args:
            keys: Sequence of keys (e.g., "V", "L", "O" for View->Layout->Open)
            
        Returns:
            True if successful
            
        Example:
            navigator.select_menu_by_keys("%V", "L", "O")  # Alt+V, L, O
        """
        logger.debug(f"Navigating menu by keys: {keys}")
        
        try:
            self._window.set_focus()
            time.sleep(self.ACTION_DELAY)
            
            for key in keys:
                self._window.type_keys(key)
                time.sleep(self.MENU_DELAY)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate menu by keys: {e}")
            return False
    
    def send_shortcut(self, shortcut: str) -> bool:
        """
        Send a keyboard shortcut.
        
        Args:
            shortcut: Shortcut name or key combo (e.g., "schedule" or "^P")
            
        Returns:
            True if sent successfully
            
        Example:
            navigator.send_shortcut("schedule")  # F9
            navigator.send_shortcut("^P")        # Ctrl+P
        """
        # Resolve shortcut name
        if shortcut in self.SHORTCUTS:
            shortcut = self.SHORTCUTS[shortcut]
        
        logger.debug(f"Sending shortcut: {shortcut}")
        
        try:
            self._window.set_focus()
            time.sleep(self.ACTION_DELAY)
            
            self._window.type_keys(shortcut)
            time.sleep(self.ACTION_DELAY)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send shortcut '{shortcut}': {e}")
            return False
    
    # =========================================================================
    # Toolbar Interaction
    # =========================================================================
    
    def click_toolbar_button(self, button_name: str) -> bool:
        """
        Click a toolbar button by name.
        
        Args:
            button_name: Text or tooltip of toolbar button
            
        Returns:
            True if clicked successfully
        """
        logger.debug(f"Looking for toolbar button: {button_name}")
        
        try:
            self._window.set_focus()
            
            # Find toolbar
            toolbar = self._window.child_window(
                control_type="ToolBar",
                found_index=0
            )
            
            # Find button
            button = toolbar.child_window(
                title_re=f".*{button_name}.*",
                control_type="Button"
            )
            
            if button.exists():
                button.click_input()
                logger.info(f"✓ Clicked toolbar button: {button_name}")
                time.sleep(self.ACTION_DELAY)
                return True
            else:
                logger.warning(f"Toolbar button not found: {button_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to click toolbar button '{button_name}': {e}")
            return False
    
    def get_toolbar_buttons(self) -> List[str]:
        """
        Get list of available toolbar buttons.
        
        Returns:
            List of button names/tooltips
        """
        buttons = []
        
        try:
            toolbars = self._window.children(control_type="ToolBar")
            
            for toolbar in toolbars:
                for button in toolbar.children(control_type="Button"):
                    name = button.window_text()
                    if name:
                        buttons.append(name)
                        
        except Exception as e:
            logger.debug(f"Error getting toolbar buttons: {e}")
        
        return buttons
    
    # =========================================================================
    # Status Bar Reading
    # =========================================================================
    
    def read_status_bar(self) -> Dict[str, str]:
        """
        Read information from the P6 status bar.
        
        Returns:
            Dict with status bar sections and their text
        """
        status = {}
        
        try:
            status_bar = self._window.child_window(
                control_type="StatusBar"
            )
            
            if status_bar.exists():
                # Get all panes in status bar
                panes = status_bar.children()
                
                for i, pane in enumerate(panes):
                    text = pane.window_text()
                    if text:
                        status[f'pane_{i}'] = text
                        
                        # Try to parse known patterns
                        self._parse_status_text(text, status)
            
        except Exception as e:
            logger.debug(f"Error reading status bar: {e}")
        
        return status
    
    def _parse_status_text(self, text: str, status: Dict):
        """Parse status bar text for known patterns."""
        # Activity count pattern: "Activities: 1,234"
        activities_match = re.search(r'Activities?:?\s*([\d,]+)', text, re.IGNORECASE)
        if activities_match:
            status['activity_count'] = int(activities_match.group(1).replace(',', ''))
        
        # Date pattern
        date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text)
        if date_match:
            status['date'] = date_match.group()
        
        # User pattern
        user_match = re.search(r'User:?\s*(\w+)', text, re.IGNORECASE)
        if user_match:
            status['user'] = user_match.group(1)
    
    def get_activity_count(self) -> Optional[int]:
        """
        Get the activity count from status bar.
        
        Returns:
            Number of activities or None if not found
        """
        status = self.read_status_bar()
        return status.get('activity_count')
    
    # =========================================================================
    # Window Title / Project Info
    # =========================================================================
    
    def get_window_title(self) -> str:
        """Get the current window title."""
        return self._window.window_text()
    
    def get_current_project_name(self) -> Optional[str]:
        """
        Extract current project name from window title.
        
        Returns:
            Project name or None if not found
            
        Note:
            P6 window title format is typically:
            "Primavera P6 Professional - [ProjectName]"
        """
        title = self.get_window_title()
        
        # Try to extract project name from title
        # Pattern: "Primavera P6 ... - [Project Name]"
        match = re.search(r'-\s*\[?([^\[\]]+)\]?\s*$', title)
        if match:
            return match.group(1).strip()
        
        # Alternative: anything after the dash
        if ' - ' in title:
            parts = title.split(' - ')
            if len(parts) > 1:
                return parts[-1].strip()
        
        return None
    
    # =========================================================================
    # View Navigation
    # =========================================================================
    
    def switch_to_view(self, view_name: str) -> bool:
        """
        Switch to a specific P6 view.
        
        Args:
            view_name: View name (Activities, WBS, Resources, etc.)
            
        Returns:
            True if switched successfully
        """
        view_shortcuts = {
            'activities': 'act',
            'wbs': 'wbs',
            'projects': 'proj',
            'resources': 'res',
            'tracking': 'track'
        }
        
        logger.info(f"Switching to view: {view_name}")
        
        # Try clicking view tab
        try:
            self._window.set_focus()
            
            # Find view tabs
            tab_control = self._window.child_window(
                control_type="Tab"
            )
            
            # Try to select tab by name
            tab_control.select(view_name)
            
            logger.info(f"✓ Switched to view: {view_name}")
            return True
            
        except Exception as e:
            logger.debug(f"Tab selection failed: {e}, trying menu")
        
        # Fallback: use menu
        return self.select_menu(f"View->{view_name}")
    
    # =========================================================================
    # Dialog Helpers
    # =========================================================================
    
    def close_dialog(self, dialog_title: str = None) -> bool:
        """
        Close a dialog by pressing Escape or clicking Cancel.
        
        Args:
            dialog_title: Optional title to target specific dialog
            
        Returns:
            True if dialog closed
        """
        try:
            if dialog_title:
                dialog = self._window.child_window(
                    title_re=f".*{dialog_title}.*"
                )
            else:
                # Try to find any dialog
                dialog = Desktop(backend="uia").active_window()
            
            if dialog.exists():
                # Try Cancel button first
                try:
                    cancel = dialog.child_window(
                        title="Cancel",
                        control_type="Button"
                    )
                    if cancel.exists():
                        cancel.click_input()
                        return True
                except Exception:
                    pass
                
                # Try Escape key
                dialog.type_keys("{ESC}")
                return True
                
        except Exception as e:
            logger.debug(f"Error closing dialog: {e}")
        
        return False
    
    def accept_dialog(self, dialog_title: str = None) -> bool:
        """
        Accept a dialog by pressing Enter or clicking OK.
        
        Args:
            dialog_title: Optional title to target specific dialog
            
        Returns:
            True if dialog accepted
        """
        try:
            if dialog_title:
                dialog = self._window.child_window(
                    title_re=f".*{dialog_title}.*"
                )
            else:
                dialog = Desktop(backend="uia").active_window()
            
            if dialog.exists():
                # Try OK button first
                try:
                    ok_button = dialog.child_window(
                        title="OK",
                        control_type="Button"
                    )
                    if ok_button.exists():
                        ok_button.click_input()
                        return True
                except Exception:
                    pass
                
                # Try Enter key
                dialog.type_keys("{ENTER}")
                return True
                
        except Exception as e:
            logger.debug(f"Error accepting dialog: {e}")
        
        return False
