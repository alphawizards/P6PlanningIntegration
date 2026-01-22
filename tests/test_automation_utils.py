"""
Tests for automation utility functions.

These tests verify the utility functions used by the automation modules
without requiring P6 to be running.
"""

import pytest
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.automation.utils import (
    retry,
    wait_for_condition,
    sanitize_filename,
    get_timestamp,
)


class TestRetryDecorator:
    """Tests for the retry decorator."""

    def test_retry_succeeds_first_attempt(self):
        """Test function succeeds on first attempt."""
        call_count = 0

        @retry(max_attempts=3, delay=0.01)
        def always_succeeds():
            nonlocal call_count
            call_count += 1
            return "success"

        result = always_succeeds()
        assert result == "success"
        assert call_count == 1

    def test_retry_succeeds_after_failures(self):
        """Test function succeeds after initial failures."""
        call_count = 0

        @retry(max_attempts=3, delay=0.01)
        def succeeds_on_third():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"

        result = succeeds_on_third()
        assert result == "success"
        assert call_count == 3

    def test_retry_exhausts_attempts(self):
        """Test all attempts exhausted raises exception."""
        call_count = 0

        @retry(max_attempts=3, delay=0.01)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_fails()
        assert call_count == 3

    def test_retry_specific_exceptions(self):
        """Test retry only catches specified exceptions."""
        @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        def raises_type_error():
            raise TypeError("Wrong type")

        # TypeError should not be caught, so only 1 attempt
        with pytest.raises(TypeError):
            raises_type_error()

    def test_retry_calls_on_retry_callback(self):
        """Test on_retry callback is called."""
        callback_calls = []

        def on_retry_callback(attempt, exception):
            callback_calls.append((attempt, str(exception)))

        call_count = 0

        @retry(max_attempts=3, delay=0.01, on_retry=on_retry_callback)
        def fails_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Attempt {call_count}")
            return "success"

        result = fails_twice()
        assert result == "success"
        assert len(callback_calls) == 2
        assert callback_calls[0] == (1, "Attempt 1")
        assert callback_calls[1] == (2, "Attempt 2")

    def test_retry_preserves_function_metadata(self):
        """Test decorator preserves function name and docstring."""
        @retry(max_attempts=3)
        def my_function():
            """My docstring."""
            pass

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."


class TestWaitForCondition:
    """Tests for wait_for_condition function."""

    def test_condition_met_immediately(self):
        """Test returns True when condition is immediately met."""
        result = wait_for_condition(
            condition=lambda: True,
            timeout=1.0,
            poll_interval=0.01,
            description="immediate"
        )
        assert result is True

    def test_condition_met_after_delay(self):
        """Test waits and returns True when condition becomes True."""
        start_time = time.time()
        delay_seconds = 0.1

        def delayed_condition():
            return time.time() - start_time > delay_seconds

        result = wait_for_condition(
            condition=delayed_condition,
            timeout=2.0,
            poll_interval=0.01,
            description="delayed"
        )
        assert result is True

    def test_condition_timeout(self):
        """Test returns False when timeout expires."""
        result = wait_for_condition(
            condition=lambda: False,
            timeout=0.1,
            poll_interval=0.01,
            description="never true"
        )
        assert result is False

    def test_condition_exception_handled(self):
        """Test exceptions in condition are handled gracefully."""
        call_count = 0

        def flaky_condition():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Flaky")
            return True

        result = wait_for_condition(
            condition=flaky_condition,
            timeout=2.0,
            poll_interval=0.01,
            description="flaky"
        )
        assert result is True
        assert call_count >= 3


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_removes_slashes(self):
        """Test removes forward and back slashes."""
        assert '/' not in sanitize_filename("path/to/file")
        assert '\\' not in sanitize_filename("path\\to\\file")

    def test_removes_colons(self):
        """Test removes colons."""
        assert ':' not in sanitize_filename("C:filename")

    def test_removes_special_characters(self):
        """Test removes special characters."""
        result = sanitize_filename('file*name?with<bad>chars|here"now')
        assert '*' not in result
        assert '?' not in result
        assert '<' not in result
        assert '>' not in result
        assert '|' not in result
        assert '"' not in result

    def test_replaces_spaces_with_underscores(self):
        """Test spaces are replaced with underscores."""
        result = sanitize_filename("my file name")
        assert ' ' not in result
        assert '_' in result

    def test_preserves_alphanumeric(self):
        """Test alphanumeric characters are preserved."""
        result = sanitize_filename("abc123XYZ")
        assert result == "abc123XYZ"

    def test_preserves_dots_underscores_hyphens(self):
        """Test dots, underscores, and hyphens are preserved."""
        result = sanitize_filename("file_name-v1.0.txt")
        # Should contain these characters
        assert '_' in result
        assert '-' in result
        assert '.' in result

    def test_handles_empty_string(self):
        """Test handles empty string."""
        result = sanitize_filename("")
        assert result == ""

    def test_handles_all_special_chars(self):
        """Test handles string with only special characters."""
        result = sanitize_filename("***???")
        assert result == ""


class TestGetTimestamp:
    """Tests for get_timestamp function."""

    def test_returns_string(self):
        """Test returns a string."""
        result = get_timestamp()
        assert isinstance(result, str)

    def test_format_is_correct(self):
        """Test timestamp format is YYYYMMDD_HHMMSS."""
        result = get_timestamp()
        # Should be 15 characters: 8 date + 1 underscore + 6 time
        assert len(result) == 15
        assert result[8] == '_'

    def test_is_numeric_except_underscore(self):
        """Test all characters except underscore are digits."""
        result = get_timestamp()
        without_underscore = result.replace('_', '')
        assert without_underscore.isdigit()

    def test_is_parseable(self):
        """Test timestamp can be parsed back to datetime."""
        result = get_timestamp()
        parsed = datetime.strptime(result, "%Y%m%d_%H%M%S")
        assert isinstance(parsed, datetime)

    def test_timestamps_are_sequential(self):
        """Test consecutive timestamps are non-decreasing."""
        ts1 = get_timestamp()
        time.sleep(0.01)
        ts2 = get_timestamp()
        assert ts2 >= ts1


class TestRetryWithRealDelay:
    """Tests that verify retry timing (slower tests)."""

    @pytest.mark.slow
    def test_retry_respects_delay(self):
        """Test retry waits the specified delay between attempts."""
        call_times = []

        @retry(max_attempts=3, delay=0.1)
        def record_time():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ValueError("Not yet")
            return "success"

        record_time()

        # Check delays between calls
        assert len(call_times) == 3
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        # Allow some tolerance
        assert delay1 >= 0.08
        assert delay2 >= 0.08
