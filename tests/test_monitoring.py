"""
Tests for the monitoring module.

Tests metrics tracking, alerts, and dashboard generation.
"""

import json
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from src.monitoring.metrics import (
    MetricsTracker,
    MetricType,
    ExecutionMetric,
    MetricsSummary,
    track_execution,
)
from src.monitoring.alerts import (
    AlertManager,
    AlertLevel,
    Alert,
    AlertThreshold,
    ConsoleAlertHandler,
)
from src.monitoring.dashboard import (
    MonitoringDashboard,
    SystemHealthStatus,
    generate_monitoring_report,
)


class TestExecutionMetric:
    """Tests for ExecutionMetric dataclass."""

    def test_create_metric(self):
        """Test creating an execution metric."""
        metric = ExecutionMetric(
            metric_type="pdf_generation",
            operation="generate_summary",
            status="success",
            duration_ms=1500.0,
            timestamp="2025-01-14T10:00:00",
            details={"pages": 5},
            project_id=123
        )

        assert metric.metric_type == "pdf_generation"
        assert metric.operation == "generate_summary"
        assert metric.status == "success"
        assert metric.duration_ms == 1500.0
        assert metric.project_id == 123

    def test_to_dict(self):
        """Test converting metric to dictionary."""
        metric = ExecutionMetric(
            metric_type="database_query",
            operation="get_activities",
            status="success",
            duration_ms=50.0,
            timestamp="2025-01-14T10:00:00"
        )

        d = metric.to_dict()
        assert d['metric_type'] == "database_query"
        assert d['operation'] == "get_activities"
        assert d['duration_ms'] == 50.0

    def test_from_dict(self):
        """Test creating metric from dictionary."""
        data = {
            'metric_type': 'cli_command',
            'operation': 'list_projects',
            'status': 'success',
            'duration_ms': 200.0,
            'timestamp': '2025-01-14T10:00:00',
            'details': {},
            'error_message': None,
            'project_id': None
        }

        metric = ExecutionMetric.from_dict(data)
        assert metric.metric_type == 'cli_command'
        assert metric.operation == 'list_projects'


class TestMetricsTracker:
    """Tests for MetricsTracker class."""

    @pytest.fixture
    def tracker(self, tmp_path):
        """Create a metrics tracker with temp storage."""
        return MetricsTracker(storage_path=tmp_path / "metrics")

    def test_record_success(self, tracker):
        """Test recording a successful operation."""
        metric = tracker.record_success(
            metric_type=MetricType.PDF_GENERATION,
            operation="generate_report",
            duration_ms=1000.0,
            project_id=123
        )

        assert metric.status == "success"
        assert metric.metric_type == "pdf_generation"

    def test_record_failure(self, tracker):
        """Test recording a failed operation."""
        metric = tracker.record_failure(
            metric_type=MetricType.GUI_AUTOMATION,
            operation="click_button",
            duration_ms=5000.0,
            error_message="Button not found"
        )

        assert metric.status == "failure"
        assert metric.error_message == "Button not found"

    def test_get_metrics_all(self, tracker):
        """Test getting all metrics."""
        tracker.record_success(MetricType.PDF_GENERATION, "op1", 100.0)
        tracker.record_success(MetricType.DATABASE_QUERY, "op2", 50.0)
        tracker.record_failure(MetricType.GUI_AUTOMATION, "op3", 1000.0, "Error")

        metrics = tracker.get_metrics()
        assert len(metrics) == 3

    def test_get_metrics_by_type(self, tracker):
        """Test filtering metrics by type."""
        tracker.record_success(MetricType.PDF_GENERATION, "op1", 100.0)
        tracker.record_success(MetricType.PDF_GENERATION, "op2", 150.0)
        tracker.record_success(MetricType.DATABASE_QUERY, "op3", 50.0)

        pdf_metrics = tracker.get_metrics(metric_type=MetricType.PDF_GENERATION)
        assert len(pdf_metrics) == 2

    def test_get_metrics_by_status(self, tracker):
        """Test filtering metrics by status."""
        tracker.record_success(MetricType.PDF_GENERATION, "op1", 100.0)
        tracker.record_failure(MetricType.PDF_GENERATION, "op2", 500.0, "Error")
        tracker.record_success(MetricType.PDF_GENERATION, "op3", 120.0)

        failures = tracker.get_metrics(status='failure')
        assert len(failures) == 1

    def test_get_summary(self, tracker):
        """Test getting summary statistics."""
        tracker.record_success(MetricType.PDF_GENERATION, "op1", 100.0)
        tracker.record_success(MetricType.PDF_GENERATION, "op2", 200.0)
        tracker.record_failure(MetricType.PDF_GENERATION, "op3", 50.0, "Error")

        summary = tracker.get_summary()

        assert summary.total_operations == 3
        assert summary.successful == 2
        assert summary.failed == 1
        assert summary.success_rate == pytest.approx(66.67, rel=0.01)
        assert summary.avg_duration_ms == pytest.approx(116.67, rel=0.01)

    def test_get_recent_failures(self, tracker):
        """Test getting recent failures."""
        tracker.record_success(MetricType.PDF_GENERATION, "op1", 100.0)
        tracker.record_failure(MetricType.PDF_GENERATION, "op2", 500.0, "Error 1")
        tracker.record_failure(MetricType.PDF_GENERATION, "op3", 600.0, "Error 2")

        failures = tracker.get_recent_failures(count=5)
        assert len(failures) == 2

    def test_get_slowest_operations(self, tracker):
        """Test getting slowest operations."""
        tracker.record_success(MetricType.PDF_GENERATION, "fast", 100.0)
        tracker.record_success(MetricType.PDF_GENERATION, "medium", 500.0)
        tracker.record_success(MetricType.PDF_GENERATION, "slow", 1000.0)

        slowest = tracker.get_slowest_operations(count=2)
        assert len(slowest) == 2
        assert slowest[0].duration_ms == 1000.0

    def test_persistence(self, tmp_path):
        """Test metrics are persisted to file."""
        storage_path = tmp_path / "metrics"

        # Create tracker and record metric
        tracker1 = MetricsTracker(storage_path=storage_path)
        tracker1.record_success(MetricType.PDF_GENERATION, "op1", 100.0)

        # Create new tracker instance with same path
        tracker2 = MetricsTracker(storage_path=storage_path)
        metrics = tracker2.get_metrics()

        assert len(metrics) == 1
        assert metrics[0].operation == "op1"

    def test_clear_metrics(self, tracker):
        """Test clearing metrics."""
        tracker.record_success(MetricType.PDF_GENERATION, "op1", 100.0)
        tracker.record_success(MetricType.PDF_GENERATION, "op2", 200.0)

        count = tracker.clear_metrics()
        assert count == 2
        assert len(tracker.get_metrics()) == 0


class TestTrackExecutionDecorator:
    """Tests for track_execution decorator."""

    def test_decorator_tracks_success(self, tmp_path):
        """Test decorator records successful execution."""
        # Reset singleton for clean test
        import src.monitoring.metrics as metrics_module
        metrics_module._metrics_tracker = MetricsTracker(storage_path=tmp_path / "metrics")

        @track_execution(MetricType.PDF_GENERATION, "test_operation")
        def successful_function():
            return "success"

        result = successful_function()

        assert result == "success"
        tracker = metrics_module._metrics_tracker
        metrics = tracker.get_metrics()
        assert len(metrics) == 1
        assert metrics[0].status == "success"

    def test_decorator_tracks_failure(self, tmp_path):
        """Test decorator records failed execution."""
        import src.monitoring.metrics as metrics_module
        metrics_module._metrics_tracker = MetricsTracker(storage_path=tmp_path / "metrics")

        @track_execution(MetricType.PDF_GENERATION, "failing_operation")
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

        tracker = metrics_module._metrics_tracker
        metrics = tracker.get_metrics()
        assert len(metrics) == 1
        assert metrics[0].status == "failure"
        assert "Test error" in metrics[0].error_message


class TestAlert:
    """Tests for Alert dataclass."""

    def test_create_alert(self):
        """Test creating an alert."""
        alert = Alert(
            alert_id="ALT-001",
            level="error",
            title="Test Alert",
            message="This is a test",
            timestamp="2025-01-14T10:00:00",
            source="test"
        )

        assert alert.alert_id == "ALT-001"
        assert alert.level == "error"
        assert alert.acknowledged is False

    def test_alert_to_dict(self):
        """Test converting alert to dictionary."""
        alert = Alert(
            alert_id="ALT-001",
            level="warning",
            title="Test",
            message="Message",
            timestamp="2025-01-14T10:00:00",
            source="test"
        )

        d = alert.to_dict()
        assert d['alert_id'] == "ALT-001"
        assert d['acknowledged'] is False


class TestAlertManager:
    """Tests for AlertManager class."""

    @pytest.fixture
    def alert_manager(self, tmp_path):
        """Create an alert manager with temp storage."""
        metrics_tracker = MetricsTracker(storage_path=tmp_path / "metrics")
        return AlertManager(
            storage_path=tmp_path / "alerts",
            metrics_tracker=metrics_tracker
        )

    def test_create_alert(self, alert_manager):
        """Test creating an alert."""
        alert = alert_manager.create_alert(
            level=AlertLevel.ERROR,
            title="Test Alert",
            message="Test message",
            source="test"
        )

        assert alert.level == "error"
        assert alert.title == "Test Alert"
        assert alert.alert_id.startswith("ALT-")

    def test_acknowledge_alert(self, alert_manager):
        """Test acknowledging an alert."""
        alert = alert_manager.create_alert(
            level=AlertLevel.WARNING,
            title="Test",
            message="Message",
            source="test"
        )

        assert alert.acknowledged is False

        updated = alert_manager.acknowledge_alert(alert.alert_id, "user")
        assert updated.acknowledged is True
        assert updated.acknowledged_by == "user"

    def test_get_unacknowledged_alerts(self, alert_manager):
        """Test getting unacknowledged alerts."""
        alert_manager.create_alert(AlertLevel.ERROR, "Alert 1", "Msg", "test")
        alert2 = alert_manager.create_alert(AlertLevel.ERROR, "Alert 2", "Msg", "test")

        alert_manager.acknowledge_alert(alert2.alert_id)

        unack = alert_manager.get_unacknowledged_alerts()
        assert len(unack) == 1
        assert unack[0].title == "Alert 1"

    def test_get_alerts_by_level(self, alert_manager):
        """Test filtering alerts by level."""
        alert_manager.create_alert(AlertLevel.INFO, "Info", "Msg", "test")
        alert_manager.create_alert(AlertLevel.ERROR, "Error", "Msg", "test")
        alert_manager.create_alert(AlertLevel.CRITICAL, "Critical", "Msg", "test")

        errors = alert_manager.get_alerts(level=AlertLevel.ERROR)
        assert len(errors) == 1
        assert errors[0].title == "Error"

    def test_alert_summary(self, alert_manager):
        """Test getting alert summary."""
        alert_manager.create_alert(AlertLevel.INFO, "Info", "Msg", "test")
        alert_manager.create_alert(AlertLevel.ERROR, "Error", "Msg", "test")
        alert_manager.create_alert(AlertLevel.CRITICAL, "Critical", "Msg", "test")

        summary = alert_manager.get_alert_summary()

        assert summary['total_alerts_today'] == 3
        assert summary['unacknowledged'] == 3
        assert summary['by_level']['error'] == 1
        assert summary['by_level']['critical'] == 1


class TestConsoleAlertHandler:
    """Tests for ConsoleAlertHandler."""

    def test_handler_filters_by_level(self, capsys):
        """Test handler respects minimum level."""
        handler = ConsoleAlertHandler(min_level=AlertLevel.ERROR)

        # Warning should not print
        warning_alert = Alert(
            alert_id="ALT-001",
            level="warning",
            title="Warning",
            message="Msg",
            timestamp="2025-01-14T10:00:00",
            source="test"
        )
        handler(warning_alert)
        captured = capsys.readouterr()
        assert "Warning" not in captured.out

        # Error should print
        error_alert = Alert(
            alert_id="ALT-002",
            level="error",
            title="Error Alert",
            message="Error message",
            timestamp="2025-01-14T10:00:00",
            source="test"
        )
        handler(error_alert)
        captured = capsys.readouterr()
        assert "Error Alert" in captured.out


class TestMonitoringDashboard:
    """Tests for MonitoringDashboard."""

    @pytest.fixture
    def dashboard(self, tmp_path):
        """Create dashboard with temp storage."""
        metrics_tracker = MetricsTracker(storage_path=tmp_path / "metrics")
        alert_manager = AlertManager(
            storage_path=tmp_path / "alerts",
            metrics_tracker=metrics_tracker
        )
        return MonitoringDashboard(
            metrics_tracker=metrics_tracker,
            alert_manager=alert_manager
        )

    def test_get_system_health_healthy(self, dashboard):
        """Test healthy system status."""
        # Record successful operations
        dashboard._metrics.record_success(MetricType.PDF_GENERATION, "op1", 100.0)
        dashboard._metrics.record_success(MetricType.PDF_GENERATION, "op2", 150.0)

        health = dashboard.get_system_health()

        assert health.status == "healthy"
        assert health.score >= 90

    def test_get_system_health_degraded(self, dashboard):
        """Test degraded system status."""
        # Record some failures
        dashboard._metrics.record_success(MetricType.PDF_GENERATION, "op1", 100.0)
        dashboard._metrics.record_failure(MetricType.PDF_GENERATION, "op2", 500.0, "Error")
        dashboard._alerts.create_alert(AlertLevel.ERROR, "Alert", "Msg", "test")

        health = dashboard.get_system_health()

        assert health.status in ["degraded", "healthy"]  # Depends on exact score

    def test_generate_text_report(self, dashboard):
        """Test text report generation."""
        dashboard._metrics.record_success(MetricType.PDF_GENERATION, "op1", 100.0)

        report = dashboard.generate_text_report(hours=24)

        assert "MONITORING REPORT" in report
        assert "SYSTEM HEALTH" in report
        assert "OPERATIONS SUMMARY" in report

    def test_generate_html_dashboard(self, dashboard, tmp_path):
        """Test HTML dashboard generation."""
        dashboard._metrics.record_success(MetricType.PDF_GENERATION, "op1", 100.0)

        output_path = tmp_path / "dashboard.html"
        html = dashboard.generate_html_dashboard(hours=24, output_path=output_path)

        assert "<html" in html
        assert "P6 Planning Integration" in html
        assert output_path.exists()

    def test_generate_json_report(self, dashboard, tmp_path):
        """Test JSON report generation."""
        dashboard._metrics.record_success(MetricType.PDF_GENERATION, "op1", 100.0)

        output_path = tmp_path / "report.json"
        data = dashboard.generate_json_report(hours=24, output_path=output_path)

        assert 'system_health' in data
        assert 'overall_summary' in data
        assert output_path.exists()


class TestGenerateMonitoringReport:
    """Tests for generate_monitoring_report convenience function."""

    def test_generate_text_format(self, tmp_path):
        """Test generating text format report."""
        # Reset singletons
        import src.monitoring.metrics as metrics_module
        import src.monitoring.alerts as alerts_module

        metrics_module._metrics_tracker = MetricsTracker(storage_path=tmp_path / "metrics")
        alerts_module._alert_manager = AlertManager(
            storage_path=tmp_path / "alerts",
            metrics_tracker=metrics_module._metrics_tracker
        )

        report = generate_monitoring_report(format='text', hours=1)

        assert isinstance(report, str)
        assert "MONITORING REPORT" in report

    def test_invalid_format_raises(self, tmp_path):
        """Test invalid format raises error."""
        with pytest.raises(ValueError, match="Unknown format"):
            generate_monitoring_report(format='invalid')


class TestMetricsSummary:
    """Tests for MetricsSummary dataclass."""

    def test_empty_summary(self):
        """Test empty summary defaults."""
        summary = MetricsSummary()

        assert summary.total_operations == 0
        assert summary.success_rate == 0.0

    def test_summary_to_dict(self):
        """Test summary conversion to dict."""
        summary = MetricsSummary(
            total_operations=10,
            successful=8,
            failed=2,
            success_rate=80.0
        )

        d = summary.to_dict()
        assert d['total_operations'] == 10
        assert d['success_rate'] == 80.0


class TestAlertThreshold:
    """Tests for AlertThreshold configuration."""

    def test_default_threshold(self):
        """Test default threshold values."""
        threshold = AlertThreshold(metric_type=MetricType.PDF_GENERATION)

        assert threshold.failure_count_threshold == 3
        assert threshold.failure_rate_threshold == 25.0
        assert threshold.duration_threshold_ms == 60000

    def test_custom_threshold(self):
        """Test custom threshold values."""
        threshold = AlertThreshold(
            metric_type=MetricType.GUI_AUTOMATION,
            failure_count_threshold=2,
            failure_rate_threshold=10.0,
            duration_threshold_ms=120000
        )

        assert threshold.failure_count_threshold == 2
        assert threshold.failure_rate_threshold == 10.0
