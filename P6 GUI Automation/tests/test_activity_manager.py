#!/usr/bin/env python3
"""
Test P6 Activity Manager.

Tests for the P6ActivityManager class including:
- Column detection
- Activity selection
- Navigation

Requires P6 Professional to be running with a project open.

Usage:
    pytest tests/test_activity_manager.py -v
    python tests/test_activity_manager.py
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
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

# Import activity manager
try:
    from src.automation.activities import P6ActivityManager, ConstraintType
    MANAGER_AVAILABLE = True
except ImportError:
    MANAGER_AVAILABLE = False

# Check if P6 is running
P6_WINDOW = None
if PYWINAUTO_AVAILABLE:
    try:
        P6_WINDOW = Desktop(backend="uia").window(title_re=".*Primavera P6.*")
        if not P6_WINDOW.exists():
            P6_WINDOW = None
    except Exception:
        P6_WINDOW = None


@pytest.mark.skipif(not PYWINAUTO_AVAILABLE, reason="pywinauto not installed")
@pytest.mark.skipif(not MANAGER_AVAILABLE, reason="P6ActivityManager not available")
@pytest.mark.skipif(P6_WINDOW is None, reason="P6 Professional not running")
class TestColumnDetection:
    """Test column detection functionality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures."""
        self.manager = P6ActivityManager(P6_WINDOW, safe_mode=True)
        yield
    
    def test_get_visible_columns(self):
        """Test that visible columns can be retrieved."""
        columns = self.manager.get_visible_columns()
        assert isinstance(columns, list), "Should return a list"
        print(f"  Found {len(columns)} columns")
    
    def test_column_cache(self):
        """Test that column caching works."""
        # First call
        columns1 = self.manager.get_visible_columns()
        # Second call should use cache (within 5 seconds)
        columns2 = self.manager.get_visible_columns()
        assert columns1 == columns2, "Cached columns should match"
    
    def test_get_column_index_known(self):
        """Test getting index of common columns."""
        columns = self.manager.get_visible_columns()
        if not columns:
            pytest.skip("No columns detected")
        
        # Test first column
        idx = self.manager.get_column_index(columns[0])
        assert idx == 0, "First column should have index 0"
    
    def test_get_column_index_invalid(self):
        """Test that invalid column raises ValueError."""
        with pytest.raises(ValueError):
            self.manager.get_column_index("NonExistentColumnXYZ123")


@pytest.mark.skipif(not PYWINAUTO_AVAILABLE, reason="pywinauto not installed")
@pytest.mark.skipif(not MANAGER_AVAILABLE, reason="P6ActivityManager not available")
@pytest.mark.skipif(P6_WINDOW is None, reason="P6 Professional not running")
class TestNavigation:
    """Test navigation functionality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures."""
        self.manager = P6ActivityManager(P6_WINDOW, safe_mode=True)
        yield
    
    def test_go_to_first(self):
        """Test navigation to first activity."""
        result = self.manager.go_to_first()
        assert result is True, "go_to_first should succeed"
    
    def test_go_to_last(self):
        """Test navigation to last activity."""
        result = self.manager.go_to_last()
        assert result is True, "go_to_last should succeed"
    
    def test_move_down(self):
        """Test moving selection down."""
        self.manager.go_to_first()
        time.sleep(0.2)
        result = self.manager.move_down(1)
        assert result is True, "move_down should succeed"
    
    def test_move_up(self):
        """Test moving selection up."""
        self.manager.go_to_last()
        time.sleep(0.2)
        result = self.manager.move_up(1)
        assert result is True, "move_up should succeed"


@pytest.mark.skipif(not PYWINAUTO_AVAILABLE, reason="pywinauto not installed")
@pytest.mark.skipif(not MANAGER_AVAILABLE, reason="P6ActivityManager not available")
@pytest.mark.skipif(P6_WINDOW is None, reason="P6 Professional not running")
class TestSafeMode:
    """Test safe mode functionality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures with safe mode enabled."""
        self.manager = P6ActivityManager(P6_WINDOW, safe_mode=True)
        yield
    
    def test_safe_mode_blocks_edit(self):
        """Test that safe mode blocks edit operations."""
        from src.automation.activities import P6SafeModeError
        
        with pytest.raises(P6SafeModeError):
            self.manager.edit_activity_field("A1000", "Duration", "10d")
    
    def test_safe_mode_blocks_add(self):
        """Test that safe mode blocks add activity."""
        from src.automation.activities import P6SafeModeError
        
        with pytest.raises(P6SafeModeError):
            self.manager.add_activity()
    
    def test_safe_mode_blocks_delete(self):
        """Test that safe mode blocks delete activity."""
        from src.automation.activities import P6SafeModeError
        
        with pytest.raises(P6SafeModeError):
            self.manager.delete_activity("A1000")
    
    def test_safe_mode_allows_navigation(self):
        """Test that safe mode allows navigation."""
        # Navigation should work in safe mode
        result = self.manager.go_to_first()
        assert result is True, "Navigation should work in safe mode"


@pytest.mark.skipif(not PYWINAUTO_AVAILABLE, reason="pywinauto not installed")
@pytest.mark.skipif(not MANAGER_AVAILABLE, reason="P6ActivityManager not available")
@pytest.mark.skipif(P6_WINDOW is None, reason="P6 Professional not running")
class TestConstraintTypes:
    """Test constraint type enum."""
    
    def test_constraint_types_exist(self):
        """Test that constraint types are defined."""
        assert ConstraintType.START_ON.value == "Start On"
        assert ConstraintType.START_ON_OR_AFTER.value == "Start On or After"
        assert ConstraintType.FINISH_ON_OR_BEFORE.value == "Finish On or Before"
    
    def test_constraint_type_count(self):
        """Test that all constraint types are defined."""
        constraint_count = len(list(ConstraintType))
        assert constraint_count >= 5, f"Should have at least 5 constraint types, found {constraint_count}"


def run_tests():
    """Run tests and print results."""
    print("=" * 60)
    print("P6 Activity Manager Tests")
    print("=" * 60)
    print()
    
    if not PYWINAUTO_AVAILABLE:
        print("SKIP: pywinauto not installed")
        return 1
    
    if not MANAGER_AVAILABLE:
        print("SKIP: P6ActivityManager not available (import error)")
        return 1
    
    if P6_WINDOW is None:
        print("SKIP: P6 Professional not running")
        print("Please open P6 Professional with a project")
        return 1
    
    print(f"P6 Window: {P6_WINDOW.window_text()}")
    print()
    print("Running tests...")
    result = pytest.main([__file__, "-v", "--tb=short"])
    return result


if __name__ == "__main__":
    sys.exit(run_tests())
