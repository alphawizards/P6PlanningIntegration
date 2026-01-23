#!/usr/bin/env python3
"""
P6 GUI Automation Test Runner.

Convenience script to run all tests with proper setup and reporting.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py --quick      # Quick validation only
    python run_tests.py --verbose    # Verbose output
"""

import sys
import argparse
from pathlib import Path

# Add paths - LOCAL path must be first to use P6 GUI Automation's own src/
# not the parent project's src/
_gui_automation_dir = Path(__file__).parent
sys.path.insert(0, str(_gui_automation_dir))
# Parent only for shared utilities if needed
sys.path.insert(1, str(_gui_automation_dir.parent))


def check_prerequisites():
    """Check that all prerequisites are met."""
    print("Checking prerequisites...")
    print()
    
    issues = []
    warnings = []
    
    # Check Python version
    if sys.version_info < (3, 10):
        issues.append(f"Python 3.10+ required, found {sys.version_info.major}.{sys.version_info.minor}")
    else:
        print(f"  [OK] Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check pywinauto
    try:
        import pywinauto
        print(f"  [OK] pywinauto {pywinauto.__version__ if hasattr(pywinauto, '__version__') else 'installed'}")
    except ImportError:
        issues.append("pywinauto not installed (pip install pywinauto)")
    
    # Check pyaudio
    try:
        import pyaudio
        print("  [OK] pyaudio installed")
    except ImportError:
        warnings.append("pyaudio not installed (voice features disabled)")
    
    # Check whisper
    try:
        import whisper
        print("  [OK] whisper installed")
    except ImportError:
        warnings.append("whisper not installed (voice features disabled)")
    
    # Check P6 running
    try:
        from pywinauto import Desktop
        window = Desktop(backend="uia").window(title_re=".*Primavera P6.*")
        if window.exists():
            print(f"  [OK] P6 Professional running: {window.window_text()}")
        else:
            warnings.append("P6 Professional not running (GUI tests will be skipped)")
    except Exception:
        warnings.append("Could not check for P6 window")
    
    print()
    
    # Report issues
    if issues:
        print("ERRORS (must fix):")
        for issue in issues:
            print(f"  [X] {issue}")
        print()
    
    if warnings:
        print("WARNINGS (optional):")
        for warning in warnings:
            print(f"  [!] {warning}")
        print()
    
    return len(issues) == 0


def run_quick_validation():
    """Run quick validation checks."""
    print("Running quick validation...")
    print()
    
    passed = 0
    failed = 0
    
    # Test 1: Import main modules
    print("[1/4] Testing module imports...")
    try:
        from src.automation.activities import P6ActivityManager
        from src.ai.gui_tools import P6GUITools
        from src.gui.overlay import P6VoiceOverlay
        print("      OK - All modules imported")
        passed += 1
    except Exception as e:
        print(f"      FAIL - Import error: {e}")
        failed += 1
    
    # Test 2: Config loading
    print("[2/4] Testing configuration...")
    try:
        from src.config import SAFE_MODE, WHISPER_MODEL
        print(f"      OK - SAFE_MODE={SAFE_MODE}, WHISPER_MODEL={WHISPER_MODEL}")
        passed += 1
    except Exception as e:
        print(f"      FAIL - Config error: {e}")
        failed += 1
    
    # Test 3: Logs directory
    print("[3/4] Checking logs directory...")
    logs_dir = Path(__file__).parent / "logs"
    if logs_dir.exists():
        print(f"      OK - {logs_dir}")
        passed += 1
    else:
        print(f"      FAIL - logs directory missing")
        failed += 1
    
    # Test 4: Constraint types
    print("[4/4] Testing constraint types...")
    try:
        from src.automation.activities import ConstraintType
        count = len(list(ConstraintType))
        print(f"      OK - {count} constraint types defined")
        passed += 1
    except Exception as e:
        print(f"      FAIL - {e}")
        failed += 1
    
    print()
    print(f"Results: {passed} passed, {failed} failed")
    
    return failed == 0


def run_full_tests(verbose=False):
    """Run full pytest suite."""
    print("Running full test suite...")
    print()
    
    try:
        import pytest
    except ImportError:
        print("ERROR: pytest not installed. Run: pip install pytest")
        return False
    
    args = ["tests/", "-v" if verbose else "-q"]
    result = pytest.main(args)
    
    return result == 0


def main():
    parser = argparse.ArgumentParser(description="P6 GUI Automation Test Runner")
    parser.add_argument("--quick", action="store_true", help="Quick validation only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--skip-prereqs", action="store_true", help="Skip prerequisite checks")
    args = parser.parse_args()
    
    print("=" * 60)
    print("P6 GUI Automation - Test Runner")
    print("=" * 60)
    print()
    
    # Check prerequisites
    if not args.skip_prereqs:
        if not check_prerequisites():
            print("Fix the errors above before running tests.")
            return 1
    
    # Run tests
    if args.quick:
        success = run_quick_validation()
    else:
        success = run_quick_validation()
        if success:
            print()
            print("-" * 60)
            print()
            success = run_full_tests(verbose=args.verbose)
    
    print()
    print("=" * 60)
    if success:
        print("All tests passed!")
    else:
        print("Some tests failed. See output above.")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
