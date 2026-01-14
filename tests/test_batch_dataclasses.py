"""
Tests for batch module data classes.

Tests BatchStatus, BatchResult, and BatchSummary without requiring P6.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from src.automation.batch import (
    BatchStatus,
    BatchResult,
    BatchSummary,
)


class TestBatchStatus:
    """Tests for BatchStatus enum."""

    def test_all_statuses_defined(self):
        """Test all expected statuses are defined."""
        expected = ['PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED']
        actual = [s.name for s in BatchStatus]
        assert set(actual) == set(expected)

    def test_status_values(self):
        """Test status enum values."""
        assert BatchStatus.PENDING.value == "pending"
        assert BatchStatus.RUNNING.value == "running"
        assert BatchStatus.COMPLETED.value == "completed"
        assert BatchStatus.FAILED.value == "failed"
        assert BatchStatus.CANCELLED.value == "cancelled"

    def test_status_from_value(self):
        """Test creating status from string value."""
        assert BatchStatus("pending") == BatchStatus.PENDING
        assert BatchStatus("completed") == BatchStatus.COMPLETED

    def test_status_comparison(self):
        """Test status comparison."""
        assert BatchStatus.PENDING != BatchStatus.COMPLETED
        assert BatchStatus.FAILED == BatchStatus.FAILED

    def test_status_in_collection(self):
        """Test status membership in collections."""
        success_statuses = {BatchStatus.COMPLETED}
        failure_statuses = {BatchStatus.FAILED, BatchStatus.CANCELLED}

        assert BatchStatus.COMPLETED in success_statuses
        assert BatchStatus.FAILED in failure_statuses
        assert BatchStatus.PENDING not in failure_statuses


class TestBatchResult:
    """Tests for BatchResult dataclass."""

    def test_create_minimal_result(self):
        """Test creating result with minimal fields."""
        result = BatchResult(
            item_name="Project A",
            status=BatchStatus.COMPLETED
        )
        assert result.item_name == "Project A"
        assert result.status == BatchStatus.COMPLETED
        assert result.output_path is None
        assert result.error is None
        assert result.duration_seconds == 0.0

    def test_create_full_result(self):
        """Test creating result with all fields."""
        result = BatchResult(
            item_name="Project B",
            status=BatchStatus.COMPLETED,
            output_path=Path("reports/project_b.pdf"),
            error=None,
            duration_seconds=15.5
        )
        assert result.item_name == "Project B"
        assert result.status == BatchStatus.COMPLETED
        assert result.output_path == Path("reports/project_b.pdf")
        assert result.duration_seconds == 15.5

    def test_create_failed_result(self):
        """Test creating a failed result with error."""
        result = BatchResult(
            item_name="Project C",
            status=BatchStatus.FAILED,
            error="Print dialog timed out"
        )
        assert result.status == BatchStatus.FAILED
        assert result.error == "Print dialog timed out"

    def test_result_is_dataclass(self):
        """Test BatchResult is a proper dataclass."""
        result = BatchResult(
            item_name="Test",
            status=BatchStatus.PENDING
        )
        # Dataclasses have __dataclass_fields__
        assert hasattr(result, '__dataclass_fields__')

    def test_result_equality(self):
        """Test result equality comparison."""
        result1 = BatchResult(
            item_name="Project A",
            status=BatchStatus.COMPLETED,
            duration_seconds=10.0
        )
        result2 = BatchResult(
            item_name="Project A",
            status=BatchStatus.COMPLETED,
            duration_seconds=10.0
        )
        assert result1 == result2

    def test_result_inequality(self):
        """Test result inequality."""
        result1 = BatchResult(item_name="A", status=BatchStatus.COMPLETED)
        result2 = BatchResult(item_name="B", status=BatchStatus.COMPLETED)
        assert result1 != result2


class TestBatchSummary:
    """Tests for BatchSummary dataclass."""

    def test_create_empty_summary(self):
        """Test creating empty summary with defaults."""
        summary = BatchSummary()
        assert summary.total == 0
        assert summary.successful == 0
        assert summary.failed == 0
        assert summary.cancelled == 0
        assert summary.results == []
        assert summary.start_time is None
        assert summary.end_time is None

    def test_create_summary_with_counts(self):
        """Test creating summary with counts."""
        summary = BatchSummary(
            total=10,
            successful=8,
            failed=1,
            cancelled=1
        )
        assert summary.total == 10
        assert summary.successful == 8
        assert summary.failed == 1
        assert summary.cancelled == 1

    def test_summary_with_results(self):
        """Test summary with result list."""
        results = [
            BatchResult("A", BatchStatus.COMPLETED),
            BatchResult("B", BatchStatus.COMPLETED),
            BatchResult("C", BatchStatus.FAILED, error="Error"),
        ]
        summary = BatchSummary(
            total=3,
            successful=2,
            failed=1,
            results=results
        )
        assert len(summary.results) == 3
        assert summary.results[0].item_name == "A"

    def test_duration_property_with_times(self):
        """Test duration calculation with start/end times."""
        start = datetime(2024, 1, 1, 10, 0, 0)
        end = datetime(2024, 1, 1, 10, 5, 30)  # 5 min 30 sec later

        summary = BatchSummary(
            total=5,
            start_time=start,
            end_time=end
        )

        assert summary.duration == 330.0  # 5*60 + 30 = 330 seconds

    def test_duration_property_without_times(self):
        """Test duration is 0 when times not set."""
        summary = BatchSummary(total=5)
        assert summary.duration == 0.0

    def test_duration_property_partial_times(self):
        """Test duration is 0 when only start_time set."""
        summary = BatchSummary(
            total=5,
            start_time=datetime.now()
        )
        assert summary.duration == 0.0

    def test_success_rate_all_successful(self):
        """Test success rate with all successful."""
        summary = BatchSummary(total=10, successful=10)
        assert summary.success_rate == 100.0

    def test_success_rate_partial_success(self):
        """Test success rate with partial success."""
        summary = BatchSummary(total=10, successful=7)
        assert summary.success_rate == 70.0

    def test_success_rate_all_failed(self):
        """Test success rate with all failed."""
        summary = BatchSummary(total=10, successful=0, failed=10)
        assert summary.success_rate == 0.0

    def test_success_rate_empty(self):
        """Test success rate with no items."""
        summary = BatchSummary(total=0)
        assert summary.success_rate == 0.0

    def test_summary_is_dataclass(self):
        """Test BatchSummary is a proper dataclass."""
        summary = BatchSummary()
        assert hasattr(summary, '__dataclass_fields__')


class TestBatchIntegration:
    """Integration tests for batch data classes."""

    def test_build_summary_from_results(self):
        """Test building summary from individual results."""
        results = [
            BatchResult("Project A", BatchStatus.COMPLETED, duration_seconds=10.0),
            BatchResult("Project B", BatchStatus.COMPLETED, duration_seconds=15.0),
            BatchResult("Project C", BatchStatus.FAILED, error="Timeout"),
            BatchResult("Project D", BatchStatus.CANCELLED),
        ]

        # Calculate counts
        successful = sum(1 for r in results if r.status == BatchStatus.COMPLETED)
        failed = sum(1 for r in results if r.status == BatchStatus.FAILED)
        cancelled = sum(1 for r in results if r.status == BatchStatus.CANCELLED)

        summary = BatchSummary(
            total=len(results),
            successful=successful,
            failed=failed,
            cancelled=cancelled,
            results=results,
            start_time=datetime(2024, 1, 1, 10, 0, 0),
            end_time=datetime(2024, 1, 1, 10, 1, 0),
        )

        assert summary.total == 4
        assert summary.successful == 2
        assert summary.failed == 1
        assert summary.cancelled == 1
        assert summary.success_rate == 50.0
        assert summary.duration == 60.0

    def test_filter_failed_results(self):
        """Test filtering failed results from summary."""
        results = [
            BatchResult("A", BatchStatus.COMPLETED),
            BatchResult("B", BatchStatus.FAILED, error="Error 1"),
            BatchResult("C", BatchStatus.FAILED, error="Error 2"),
            BatchResult("D", BatchStatus.COMPLETED),
        ]

        summary = BatchSummary(total=4, results=results)

        failed_results = [r for r in summary.results if r.status == BatchStatus.FAILED]
        assert len(failed_results) == 2
        assert all(r.error is not None for r in failed_results)

    def test_calculate_total_duration(self):
        """Test calculating total duration from results."""
        results = [
            BatchResult("A", BatchStatus.COMPLETED, duration_seconds=10.0),
            BatchResult("B", BatchStatus.COMPLETED, duration_seconds=20.0),
            BatchResult("C", BatchStatus.COMPLETED, duration_seconds=15.0),
        ]

        total_duration = sum(r.duration_seconds for r in results)
        assert total_duration == 45.0

    def test_get_output_paths(self):
        """Test extracting output paths from results."""
        results = [
            BatchResult("A", BatchStatus.COMPLETED, output_path=Path("a.pdf")),
            BatchResult("B", BatchStatus.COMPLETED, output_path=Path("b.pdf")),
            BatchResult("C", BatchStatus.FAILED),  # No output path
        ]

        output_paths = [r.output_path for r in results if r.output_path is not None]
        assert len(output_paths) == 2
        assert Path("a.pdf") in output_paths
        assert Path("b.pdf") in output_paths
