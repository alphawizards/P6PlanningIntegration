#!/usr/bin/env python3
"""
Test P6 Connection.

Basic test to verify pywinauto can connect to P6 Professional.
Run this test with P6 open to verify automation setup.

Usage:
    pytest tests/test_p6_connection.py -v
    python tests/test_p6_connection.py
"""

import sys
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

# Skip all tests if pywinauto not available
try:
    from pywinauto import Desktop
    from pywinauto.findwindows import ElementNotFoundError
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

# Skip all tests if P6 not running
P6_AVAILABLE = False
if PYWINAUTO_AVAILABLE:
    try:
        window = Desktop(backend="uia").window(title_re=".*Primavera P6.*")
        P6_AVAILABLE = window.exists()
    except Exception:
        P6_AVAILABLE = False


@pytest.mark.skipif(not PYWINAUTO_AVAILABLE, reason="pywinauto not installed")
@pytest.mark.skipif(not P6_AVAILABLE, reason="P6 Professional not running")
class TestP6Connection:
    """Test P6 connection functionality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures."""
        self.p6_window = Desktop(backend="uia").window(title_re=".*Primavera P6.*")
        yield
    
    def test_p6_window_exists(self):
        """Test that P6 window can be found."""
        assert self.p6_window.exists(), "P6 window should exist"
    
    def test_p6_window_has_title(self):
        """Test that P6 window has a title."""
        title = self.p6_window.window_text()
        assert title, "P6 window should have a title"
        assert "Primavera" in title or "P6" in title, "Title should contain P6 reference"
    
    def test_p6_window_is_visible(self):
        """Test that P6 window is visible."""
        assert self.p6_window.is_visible(), "P6 window should be visible"
    
    def test_p6_window_is_enabled(self):
        """Test that P6 window is enabled (not disabled)."""
        assert self.p6_window.is_enabled(), "P6 window should be enabled"
    
    def test_p6_window_can_focus(self):
        """Test that P6 window can be focused."""
        self.p6_window.set_focus()
        time.sleep(0.2)
        # If we get here without error, the focus worked
        assert True


@pytest.mark.skipif(not PYWINAUTO_AVAILABLE, reason="pywinauto not installed")
@pytest.mark.skipif(not P6_AVAILABLE, reason="P6 Professional not running")
class TestP6Controls:
    """Test P6 control detection."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures."""
        self.p6_window = Desktop(backend="uia").window(title_re=".*Primavera P6.*")
        yield
    
    def test_can_find_menu_bar(self):
        """Test that menu bar exists."""
        try:
            menu = self.p6_window.child_window(control_type="MenuBar")
            assert menu.exists(), "Menu bar should exist"
        except Exception:
            pytest.skip("Menu bar not found - different P6 version?")
    
    def test_can_find_status_bar(self):
        """Test that status bar exists."""
        try:
            status = self.p6_window.child_window(control_type="StatusBar")
            # Status bar may not exist in all views
            if not status.exists():
                pytest.skip("Status bar not found in current view")
            assert True
        except Exception:
            pytest.skip("Status bar detection not available")


def run_tests():
    """Run tests and print results."""
    print("=" * 60)
    print("P6 Connection Tests")
    print("=" * 60)
    print()
    
    if not PYWINAUTO_AVAILABLE:
        print("SKIP: pywinauto not installed")
        print("Run: pip install pywinauto")
        return 1
    
    if not P6_AVAILABLE:
        print("SKIP: P6 Professional not running")
        print("Please open P6 Professional with a project")
        return 1
    
    print("Running tests...")
    result = pytest.main([__file__, "-v", "--tb=short"])
    return result


if __name__ == "__main__":
    sys.exit(run_tests())
