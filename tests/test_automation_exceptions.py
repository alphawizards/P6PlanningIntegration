"""
Tests for automation exceptions module.

Verifies exception hierarchy and behavior.
"""

import pytest

from src.automation.exceptions import (
    P6AutomationError,
    P6NotFoundError,
    P6ConnectionError,
    P6LoginError,
    P6WindowNotFoundError,
    P6TimeoutError,
    P6ProjectNotFoundError,
    P6LayoutNotFoundError,
    P6PrintError,
    P6ExportError,
    P6ScheduleError,
    P6SafeModeError,
)


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""

    def test_base_exception_inherits_from_exception(self):
        """Test P6AutomationError inherits from Exception."""
        assert issubclass(P6AutomationError, Exception)

    def test_all_exceptions_inherit_from_base(self):
        """Test all P6 exceptions inherit from P6AutomationError."""
        exception_classes = [
            P6NotFoundError,
            P6ConnectionError,
            P6LoginError,
            P6WindowNotFoundError,
            P6TimeoutError,
            P6ProjectNotFoundError,
            P6LayoutNotFoundError,
            P6PrintError,
            P6ExportError,
            P6ScheduleError,
            P6SafeModeError,
        ]

        for exc_class in exception_classes:
            assert issubclass(exc_class, P6AutomationError), \
                f"{exc_class.__name__} should inherit from P6AutomationError"

    def test_exceptions_are_catchable_by_base(self):
        """Test all exceptions can be caught by base class."""
        exception_classes = [
            P6NotFoundError,
            P6ConnectionError,
            P6LoginError,
            P6WindowNotFoundError,
            P6TimeoutError,
            P6ProjectNotFoundError,
            P6LayoutNotFoundError,
            P6PrintError,
            P6ExportError,
            P6ScheduleError,
            P6SafeModeError,
        ]

        for exc_class in exception_classes:
            try:
                raise exc_class("test message")
            except P6AutomationError as e:
                assert str(e) == "test message"
            except Exception:
                pytest.fail(f"{exc_class.__name__} not caught by P6AutomationError")


class TestExceptionMessages:
    """Tests for exception message handling."""

    def test_base_exception_message(self):
        """Test base exception preserves message."""
        exc = P6AutomationError("Custom error message")
        assert str(exc) == "Custom error message"

    def test_not_found_error_message(self):
        """Test P6NotFoundError preserves message."""
        exc = P6NotFoundError("P6 not running")
        assert "P6 not running" in str(exc)

    def test_connection_error_message(self):
        """Test P6ConnectionError preserves message."""
        exc = P6ConnectionError("Failed to connect to database")
        assert "Failed to connect" in str(exc)

    def test_timeout_error_message(self):
        """Test P6TimeoutError preserves message."""
        exc = P6TimeoutError("Window not found after 30s")
        assert "30s" in str(exc)

    def test_project_not_found_with_name(self):
        """Test P6ProjectNotFoundError with project name."""
        exc = P6ProjectNotFoundError("Project 'Highway Construction' not found")
        assert "Highway Construction" in str(exc)

    def test_safe_mode_error(self):
        """Test P6SafeModeError message."""
        exc = P6SafeModeError("Operation blocked: SAFE_MODE is enabled")
        assert "SAFE_MODE" in str(exc)


class TestExceptionRaising:
    """Tests for raising and catching exceptions."""

    def test_raise_and_catch_specific(self):
        """Test raising and catching specific exception."""
        with pytest.raises(P6TimeoutError):
            raise P6TimeoutError("Operation timed out")

    def test_raise_with_args(self):
        """Test exception with multiple arguments."""
        exc = P6PrintError("Failed", "details", 123)
        assert "Failed" in str(exc)

    def test_exception_in_try_except_else(self):
        """Test exception behavior in try/except/else."""
        caught = False

        try:
            raise P6ExportError("Export failed")
        except P6ExportError:
            caught = True

        assert caught

    def test_exception_chaining(self):
        """Test exception chaining with raise from."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise P6AutomationError("Wrapped error") from e
        except P6AutomationError as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ValueError)


class TestExceptionInstances:
    """Tests for exception instance behavior."""

    def test_exception_is_instance_of_base(self):
        """Test specific exception is instance of base."""
        exc = P6PrintError("print failed")
        assert isinstance(exc, P6AutomationError)
        assert isinstance(exc, Exception)

    def test_exception_has_args(self):
        """Test exception has args attribute."""
        exc = P6LoginError("Invalid credentials")
        assert exc.args == ("Invalid credentials",)

    def test_exception_repr(self):
        """Test exception string representation."""
        exc = P6ScheduleError("F9 failed")
        # repr should include class name
        repr_str = repr(exc)
        assert "P6ScheduleError" in repr_str

    def test_exception_equality(self):
        """Test exception equality based on args."""
        exc1 = P6WindowNotFoundError("Window not found")
        exc2 = P6WindowNotFoundError("Window not found")
        # Exceptions with same args should have same string representation
        assert str(exc1) == str(exc2)


class TestExceptionUseCases:
    """Tests for realistic exception use cases."""

    def test_timeout_in_wait_loop(self):
        """Test timeout exception in simulated wait loop."""
        def wait_for_window(timeout=0.1):
            import time
            start = time.time()
            while time.time() - start < timeout:
                # Simulate waiting
                time.sleep(0.01)
            raise P6TimeoutError(f"Window not found within {timeout}s")

        with pytest.raises(P6TimeoutError, match="0.1s"):
            wait_for_window(0.1)

    def test_project_not_found_in_search(self):
        """Test project not found during search."""
        def find_project(name, projects):
            for p in projects:
                if p == name:
                    return p
            raise P6ProjectNotFoundError(f"Project '{name}' not found")

        projects = ["Project A", "Project B"]

        # Should work
        assert find_project("Project A", projects) == "Project A"

        # Should raise
        with pytest.raises(P6ProjectNotFoundError, match="Project C"):
            find_project("Project C", projects)

    def test_safe_mode_blocks_operation(self):
        """Test safe mode blocking write operation."""
        def update_schedule(safe_mode=True):
            if safe_mode:
                raise P6SafeModeError(
                    "Cannot modify schedule: SAFE_MODE is enabled. "
                    "Set safe_mode=False to allow modifications."
                )
            return "Schedule updated"

        # Should raise in safe mode
        with pytest.raises(P6SafeModeError, match="SAFE_MODE"):
            update_schedule(safe_mode=True)

        # Should work when disabled
        result = update_schedule(safe_mode=False)
        assert result == "Schedule updated"
