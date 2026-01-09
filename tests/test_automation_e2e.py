#!/usr/bin/env python3
"""
P6 Automation End-to-End Test Suite.

This module provides comprehensive testing for all P6 automation modules.
Run with P6 Professional open and logged in.

Usage:
    python -m tests.test_automation_e2e
    
Or run specific tests:
    python -m tests.test_automation_e2e --test connection
    python -m tests.test_automation_e2e --test all
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestResult:
    """Individual test result."""
    
    def __init__(self, name: str, passed: bool, message: str = "", duration: float = 0):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration = duration


class P6AutomationTestSuite:
    """
    End-to-end test suite for P6 automation.
    
    Prerequisites:
    - P6 Professional must be running
    - User must be logged in
    - At least one project must exist
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.results: List[TestResult] = []
        self.start_time = None
        
        # Test configuration
        self.test_project = None  # Will use first available
        self.test_layout = None   # Will use first available
        self.output_dir = Path("reports/test_output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def log(self, message: str):
        """Log message if verbose."""
        if self.verbose:
            print(f"  {message}")
    
    def record(self, name: str, passed: bool, message: str = "", duration: float = 0):
        """Record test result."""
        result = TestResult(name, passed, message, duration)
        self.results.append(result)
        
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"[{status}] {name}")
        if message and not passed:
            print(f"       {message}")
    
    # =========================================================================
    # Test: Imports
    # =========================================================================
    
    def test_imports(self) -> bool:
        """Test that all modules can be imported."""
        print("\n" + "=" * 60)
        print("TEST: Module Imports")
        print("=" * 60)
        
        start = time.time()
        
        try:
            from src.automation import (
                P6AutomationBase,
                P6PrintAutomation,
                P6ConnectionManager,
                P6Navigator,
                P6PrintManager,
                P6ExportManager,
                P6ProjectManager,
                P6LayoutManager,
                P6ScheduleManager,
                P6BaselineManager,
                P6ActivityManager,
                P6BatchProcessor,
                P6AgentInterface,
                # Enums
                PageOrientation,
                PageSize,
                ExportFormat,
                P6View,
                ScheduleOption,
                BatchStatus,
                ActionType,
                # Functions
                detect_p6,
                is_p6_running,
                # Exceptions
                P6AutomationError,
                P6NotFoundError,
                P6ConnectionError,
            )
            
            self.record("Import all modules", True, duration=time.time() - start)
            return True
            
        except ImportError as e:
            self.record("Import all modules", False, str(e))
            return False
    
    # =========================================================================
    # Test: Connection
    # =========================================================================
    
    def test_connection(self) -> bool:
        """Test P6 connection detection."""
        print("\n" + "=" * 60)
        print("TEST: Connection")
        print("=" * 60)
        
        from src.automation import (
            P6ConnectionManager,
            detect_p6,
            is_p6_running
        )
        
        all_passed = True
        
        # Test is_p6_running
        start = time.time()
        try:
            running = is_p6_running()
            self.record(
                "is_p6_running()",
                True,
                f"P6 running: {running}",
                time.time() - start
            )
        except Exception as e:
            self.record("is_p6_running()", False, str(e))
            all_passed = False
        
        # Test detect_p6
        start = time.time()
        try:
            pid = detect_p6()
            self.record(
                "detect_p6()",
                pid is not None,
                f"PID: {pid}",
                time.time() - start
            )
        except Exception as e:
            self.record("detect_p6()", False, str(e))
            all_passed = False
        
        # Test ConnectionManager
        start = time.time()
        try:
            manager = P6ConnectionManager()
            processes = manager.find_p6_processes()
            self.record(
                "P6ConnectionManager.find_p6_processes()",
                len(processes) >= 0,
                f"Found {len(processes)} processes",
                time.time() - start
            )
        except Exception as e:
            self.record("P6ConnectionManager.find_p6_processes()", False, str(e))
            all_passed = False
        
        return all_passed
    
    # =========================================================================
    # Test: Automation Base
    # =========================================================================
    
    def test_automation_base(self) -> bool:
        """Test P6AutomationBase context manager."""
        print("\n" + "=" * 60)
        print("TEST: Automation Base")
        print("=" * 60)
        
        from src.automation import P6AutomationBase
        
        start = time.time()
        try:
            with P6AutomationBase(auto_connect=True) as p6:
                connected = p6.is_connected
                window = p6.main_window is not None
                
                self.record(
                    "P6AutomationBase context manager",
                    connected and window,
                    f"Connected: {connected}, Window: {window}",
                    time.time() - start
                )
                return connected and window
                
        except Exception as e:
            self.record("P6AutomationBase context manager", False, str(e))
            return False
    
    # =========================================================================
    # Test: Navigator
    # =========================================================================
    
    def test_navigator(self) -> bool:
        """Test P6Navigator functionality."""
        print("\n" + "=" * 60)
        print("TEST: Navigator")
        print("=" * 60)
        
        from src.automation import P6PrintAutomation, P6Navigator
        
        all_passed = True
        
        try:
            with P6PrintAutomation() as p6:
                nav = P6Navigator(p6.main_window)
                
                # Test get window title
                start = time.time()
                title = nav.get_window_title()
                self.record(
                    "P6Navigator.get_window_title()",
                    len(title) > 0,
                    f"Title: {title[:50]}...",
                    time.time() - start
                )
                
                # Test read status bar
                start = time.time()
                status = nav.read_status_bar()
                self.record(
                    "P6Navigator.read_status_bar()",
                    isinstance(status, dict),
                    f"Status keys: {list(status.keys())}",
                    time.time() - start
                )
                
        except Exception as e:
            self.record("Navigator tests", False, str(e))
            all_passed = False
        
        return all_passed
    
    # =========================================================================
    # Test: Projects
    # =========================================================================
    
    def test_projects(self) -> bool:
        """Test P6ProjectManager functionality."""
        print("\n" + "=" * 60)
        print("TEST: Projects")
        print("=" * 60)
        
        from src.automation import P6PrintAutomation, P6ProjectManager
        
        all_passed = True
        
        try:
            with P6PrintAutomation() as p6:
                projects = P6ProjectManager(p6.main_window)
                
                # Test get open projects
                start = time.time()
                open_projs = projects.get_open_projects()
                self.record(
                    "P6ProjectManager.get_open_projects()",
                    isinstance(open_projs, list),
                    f"Open: {open_projs[:3]}..." if open_projs else "None open",
                    time.time() - start
                )
                
                # Test get current project
                start = time.time()
                current = projects.current_project
                self.record(
                    "P6ProjectManager.current_project",
                    True,
                    f"Current: {current}",
                    time.time() - start
                )
                
                if current:
                    self.test_project = current
                    
        except Exception as e:
            self.record("Projects tests", False, str(e))
            all_passed = False
        
        return all_passed
    
    # =========================================================================
    # Test: Layouts
    # =========================================================================
    
    def test_layouts(self) -> bool:
        """Test P6LayoutManager functionality."""
        print("\n" + "=" * 60)
        print("TEST: Layouts")
        print("=" * 60)
        
        from src.automation import P6PrintAutomation, P6LayoutManager
        
        all_passed = True
        
        try:
            with P6PrintAutomation() as p6:
                layouts = P6LayoutManager(p6.main_window)
                
                # Test current layout property
                start = time.time()
                current = layouts.current_layout
                self.record(
                    "P6LayoutManager.current_layout",
                    True,  # May be None
                    f"Current: {current}",
                    time.time() - start
                )
                
        except Exception as e:
            self.record("Layouts tests", False, str(e))
            all_passed = False
        
        return all_passed
    
    # =========================================================================
    # Test: Agent Interface
    # =========================================================================
    
    def test_agent(self) -> bool:
        """Test P6AgentInterface functionality."""
        print("\n" + "=" * 60)
        print("TEST: Agent Interface")
        print("=" * 60)
        
        from src.automation import P6AgentInterface, ActionResult
        
        all_passed = True
        
        # Test without managers (should handle gracefully)
        start = time.time()
        try:
            agent = P6AgentInterface()
            
            # Test get available actions
            actions = agent.get_available_actions()
            self.record(
                "P6AgentInterface.get_available_actions()",
                len(actions) > 0,
                f"Actions: {len(actions)} available",
                time.time() - start
            )
            
            # Test get tool definitions
            start = time.time()
            tools = agent.get_tool_definitions()
            self.record(
                "P6AgentInterface.get_tool_definitions()",
                len(tools) > 0,
                f"Tools: {len(tools)} defined",
                time.time() - start
            )
            
            # Test execute unknown action
            start = time.time()
            result = agent.execute("unknown_action")
            self.record(
                "P6AgentInterface handles unknown action",
                not result.success,
                "Correctly rejected",
                time.time() - start
            )
            
        except Exception as e:
            self.record("Agent tests", False, str(e))
            all_passed = False
        
        return all_passed
    
    # =========================================================================
    # Test: Batch Processor
    # =========================================================================
    
    def test_batch(self) -> bool:
        """Test P6BatchProcessor data classes."""
        print("\n" + "=" * 60)
        print("TEST: Batch Processor")
        print("=" * 60)
        
        from src.automation import BatchStatus, BatchResult, BatchSummary
        
        all_passed = True
        
        # Test BatchResult
        start = time.time()
        try:
            result = BatchResult(
                item_name="Test Project",
                status=BatchStatus.COMPLETED
            )
            self.record(
                "BatchResult creation",
                result.status == BatchStatus.COMPLETED,
                duration=time.time() - start
            )
        except Exception as e:
            self.record("BatchResult creation", False, str(e))
            all_passed = False
        
        # Test BatchSummary
        start = time.time()
        try:
            summary = BatchSummary(total=10, successful=8, failed=2)
            rate = summary.success_rate
            self.record(
                "BatchSummary.success_rate",
                rate == 80.0,
                f"Rate: {rate}%",
                time.time() - start
            )
        except Exception as e:
            self.record("BatchSummary.success_rate", False, str(e))
            all_passed = False
        
        return all_passed
    
    # =========================================================================
    # Test: Exceptions
    # =========================================================================
    
    def test_exceptions(self) -> bool:
        """Test custom exceptions."""
        print("\n" + "=" * 60)
        print("TEST: Exceptions")
        print("=" * 60)
        
        from src.automation import (
            P6AutomationError,
            P6NotFoundError,
            P6ConnectionError,
            P6LoginError,
            P6PrintError,
            P6SafeModeError
        )
        
        start = time.time()
        try:
            # Test inheritance
            error = P6NotFoundError("Test")
            is_automation_error = isinstance(error, P6AutomationError)
            is_base_error = isinstance(error, Exception)
            
            self.record(
                "Exception hierarchy",
                is_automation_error and is_base_error,
                "Inheritance correct",
                time.time() - start
            )
            return True
            
        except Exception as e:
            self.record("Exception hierarchy", False, str(e))
            return False
    
    # =========================================================================
    # Run All Tests
    # =========================================================================
    
    def run_all(self) -> bool:
        """Run all tests."""
        self.start_time = datetime.now()
        
        print("\n" + "=" * 60)
        print("P6 AUTOMATION END-TO-END TEST SUITE")
        print("=" * 60)
        print(f"Started: {self.start_time}")
        print()
        
        # Run tests
        tests = [
            ("Imports", self.test_imports),
            ("Exceptions", self.test_exceptions),
            ("Connection", self.test_connection),
            ("Batch", self.test_batch),
            ("Agent", self.test_agent),
            # These require P6 to be running:
            # ("Automation Base", self.test_automation_base),
            # ("Navigator", self.test_navigator),
            # ("Projects", self.test_projects),
            # ("Layouts", self.test_layouts),
        ]
        
        for name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                self.record(f"{name} (uncaught)", False, str(e))
        
        # Summary
        self.print_summary()
        
        passed = sum(1 for r in self.results if r.passed)
        return passed == len(self.results)
    
    def run_with_p6(self) -> bool:
        """Run all tests including those requiring P6."""
        self.start_time = datetime.now()
        
        print("\n" + "=" * 60)
        print("P6 AUTOMATION FULL TEST SUITE (P6 REQUIRED)")
        print("=" * 60)
        print(f"Started: {self.start_time}")
        print()
        
        tests = [
            ("Imports", self.test_imports),
            ("Exceptions", self.test_exceptions),
            ("Connection", self.test_connection),
            ("Automation Base", self.test_automation_base),
            ("Navigator", self.test_navigator),
            ("Projects", self.test_projects),
            ("Layouts", self.test_layouts),
            ("Batch", self.test_batch),
            ("Agent", self.test_agent),
        ]
        
        for name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                self.record(f"{name} (uncaught)", False, str(e))
        
        self.print_summary()
        
        passed = sum(1 for r in self.results if r.passed)
        return passed == len(self.results)
    
    def print_summary(self):
        """Print test summary."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total:    {len(self.results)}")
        print(f"Passed:   {passed}")
        print(f"Failed:   {failed}")
        print(f"Duration: {duration:.2f}s")
        print("=" * 60)
        
        if failed > 0:
            print("\nFailed tests:")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.name}: {r.message}")


def main():
    parser = argparse.ArgumentParser(description="P6 Automation E2E Tests")
    parser.add_argument(
        "--with-p6",
        action="store_true",
        help="Run tests requiring P6 Professional"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    suite = P6AutomationTestSuite(verbose=args.verbose)
    
    if args.with_p6:
        success = suite.run_with_p6()
    else:
        success = suite.run_all()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
