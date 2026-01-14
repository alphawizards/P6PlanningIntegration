"""
Execution metrics tracking for P6 Planning Integration.

Tracks success/failure rates, execution times, and operation history.
"""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from functools import wraps
import threading


class MetricType(Enum):
    """Types of operations being tracked."""
    PDF_GENERATION = "pdf_generation"
    SCHEDULE_ANALYSIS = "schedule_analysis"
    DATABASE_QUERY = "database_query"
    FILE_EXPORT = "file_export"
    GUI_AUTOMATION = "gui_automation"
    BATCH_PROCESS = "batch_process"
    CLI_COMMAND = "cli_command"
    HEALTH_CHECK = "health_check"
    PROJECT_OPEN = "project_open"
    REPORT_PRINT = "report_print"


@dataclass
class ExecutionMetric:
    """Single execution metric record."""
    metric_type: str
    operation: str
    status: str  # 'success', 'failure', 'warning'
    duration_ms: float
    timestamp: str
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    project_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionMetric':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class MetricsSummary:
    """Summary statistics for metrics."""
    total_operations: int = 0
    successful: int = 0
    failed: int = 0
    warnings: int = 0
    success_rate: float = 0.0
    avg_duration_ms: float = 0.0
    min_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    total_duration_ms: float = 0.0
    period_start: Optional[str] = None
    period_end: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class MetricsTracker:
    """
    Tracks execution metrics for all P6 operations.

    Thread-safe class that persists metrics to JSON.
    Use get_metrics_tracker() for singleton access.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize metrics tracker."""
        if storage_path is None:
            # Default to logs/metrics directory
            base_dir = Path(__file__).parent.parent.parent
            storage_path = base_dir / "logs" / "metrics"

        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._metrics: List[ExecutionMetric] = []
        self._session_start = datetime.now()
        self._current_file = self._get_metrics_filename()
        self._logger = logging.getLogger('P6Metrics')
        self._lock = threading.Lock()

        # Load existing metrics for today
        self._load_metrics()

    def _get_metrics_filename(self, date: Optional[datetime] = None) -> Path:
        """Get metrics filename for a given date."""
        if date is None:
            date = datetime.now()
        return self.storage_path / f"metrics_{date.strftime('%Y%m%d')}.json"

    def _load_metrics(self) -> None:
        """Load metrics from current day's file."""
        if self._current_file.exists():
            try:
                with open(self._current_file, 'r') as f:
                    data = json.load(f)
                    self._metrics = [
                        ExecutionMetric.from_dict(m) for m in data.get('metrics', [])
                    ]
            except (json.JSONDecodeError, KeyError) as e:
                self._logger.warning(f"Failed to parse metrics file: {e}")
                self._metrics = []
            except IOError as e:
                self._logger.error(f"Failed to read metrics file: {e}")
                self._metrics = []

    def _save_metrics(self) -> None:
        """Save metrics to JSON file."""
        data = {
            'session_start': self._session_start.isoformat(),
            'last_updated': datetime.now().isoformat(),
            'metrics': [m.to_dict() for m in self._metrics]
        }
        try:
            with open(self._current_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except IOError as e:
            self._logger.error(f"Failed to save metrics to {self._current_file}: {e}")
        except (TypeError, ValueError) as e:
            self._logger.error(f"Failed to serialize metrics: {e}")

    def record(
        self,
        metric_type: MetricType,
        operation: str,
        status: str,
        duration_ms: float,
        details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        project_id: Optional[int] = None
    ) -> ExecutionMetric:
        """
        Record a new execution metric.

        Args:
            metric_type: Type of operation
            operation: Specific operation name
            status: 'success', 'failure', or 'warning'
            duration_ms: Execution duration in milliseconds
            details: Additional details dictionary
            error_message: Error message if failed
            project_id: Related project ID if applicable

        Returns:
            The recorded metric
        """
        metric = ExecutionMetric(
            metric_type=metric_type.value,
            operation=operation,
            status=status,
            duration_ms=duration_ms,
            timestamp=datetime.now().isoformat(),
            details=details or {},
            error_message=error_message,
            project_id=project_id
        )

        with self._lock:
            self._metrics.append(metric)
            self._save_metrics()

        return metric

    def record_success(
        self,
        metric_type: MetricType,
        operation: str,
        duration_ms: float,
        details: Optional[Dict[str, Any]] = None,
        project_id: Optional[int] = None
    ) -> ExecutionMetric:
        """Record a successful operation."""
        return self.record(
            metric_type=metric_type,
            operation=operation,
            status='success',
            duration_ms=duration_ms,
            details=details,
            project_id=project_id
        )

    def record_failure(
        self,
        metric_type: MetricType,
        operation: str,
        duration_ms: float,
        error_message: str,
        details: Optional[Dict[str, Any]] = None,
        project_id: Optional[int] = None
    ) -> ExecutionMetric:
        """Record a failed operation."""
        return self.record(
            metric_type=metric_type,
            operation=operation,
            status='failure',
            duration_ms=duration_ms,
            error_message=error_message,
            details=details,
            project_id=project_id
        )

    def get_metrics(
        self,
        metric_type: Optional[MetricType] = None,
        status: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        project_id: Optional[int] = None
    ) -> List[ExecutionMetric]:
        """
        Get metrics with optional filtering.

        Args:
            metric_type: Filter by metric type
            status: Filter by status ('success', 'failure', 'warning')
            since: Filter metrics after this time
            until: Filter metrics before this time
            project_id: Filter by project ID

        Returns:
            List of matching metrics
        """
        results = self._metrics.copy()

        if metric_type:
            results = [m for m in results if m.metric_type == metric_type.value]

        if status:
            results = [m for m in results if m.status == status]

        if since:
            since_str = since.isoformat()
            results = [m for m in results if m.timestamp >= since_str]

        if until:
            until_str = until.isoformat()
            results = [m for m in results if m.timestamp <= until_str]

        if project_id:
            results = [m for m in results if m.project_id == project_id]

        return results

    def get_summary(
        self,
        metric_type: Optional[MetricType] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> MetricsSummary:
        """
        Get summary statistics for metrics.

        Args:
            metric_type: Filter by metric type
            since: Start of period
            until: End of period

        Returns:
            MetricsSummary with statistics
        """
        metrics = self.get_metrics(metric_type=metric_type, since=since, until=until)

        if not metrics:
            return MetricsSummary()

        successful = len([m for m in metrics if m.status == 'success'])
        failed = len([m for m in metrics if m.status == 'failure'])
        warnings = len([m for m in metrics if m.status == 'warning'])
        total = len(metrics)

        durations = [m.duration_ms for m in metrics]

        return MetricsSummary(
            total_operations=total,
            successful=successful,
            failed=failed,
            warnings=warnings,
            success_rate=(successful / total * 100) if total > 0 else 0.0,
            avg_duration_ms=sum(durations) / len(durations) if durations else 0.0,
            min_duration_ms=min(durations) if durations else 0.0,
            max_duration_ms=max(durations) if durations else 0.0,
            total_duration_ms=sum(durations),
            period_start=min(m.timestamp for m in metrics),
            period_end=max(m.timestamp for m in metrics)
        )

    def get_recent_failures(self, count: int = 10) -> List[ExecutionMetric]:
        """Get most recent failures."""
        failures = [m for m in self._metrics if m.status == 'failure']
        return sorted(failures, key=lambda m: m.timestamp, reverse=True)[:count]

    def get_slowest_operations(
        self,
        metric_type: Optional[MetricType] = None,
        count: int = 10
    ) -> List[ExecutionMetric]:
        """Get slowest operations by duration."""
        metrics = self.get_metrics(metric_type=metric_type, status='success')
        return sorted(metrics, key=lambda m: m.duration_ms, reverse=True)[:count]

    def get_failure_rate_by_type(self) -> Dict[str, float]:
        """Get failure rate for each metric type."""
        rates = {}
        for mt in MetricType:
            metrics = self.get_metrics(metric_type=mt)
            if metrics:
                failed = len([m for m in metrics if m.status == 'failure'])
                rates[mt.value] = (failed / len(metrics)) * 100
        return rates

    def clear_metrics(self, before: Optional[datetime] = None) -> int:
        """
        Clear metrics, optionally only before a certain date.

        Args:
            before: Clear metrics before this datetime

        Returns:
            Number of metrics cleared
        """
        with self._lock:
            if before is None:
                count = len(self._metrics)
                self._metrics = []
            else:
                before_str = before.isoformat()
                old_count = len(self._metrics)
                self._metrics = [m for m in self._metrics if m.timestamp >= before_str]
                count = old_count - len(self._metrics)

            self._save_metrics()

        return count

    def export_metrics(
        self,
        output_path: Path,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        format: str = 'json'
    ) -> Optional[Path]:
        """
        Export metrics to file.

        Args:
            output_path: Output file path
            since: Start of period
            until: End of period
            format: 'json' or 'csv'

        Returns:
            Path to exported file, or None if export failed
        """
        metrics = self.get_metrics(since=since, until=until)

        try:
            if format == 'json':
                data = {
                    'exported_at': datetime.now().isoformat(),
                    'metrics_count': len(metrics),
                    'metrics': [m.to_dict() for m in metrics]
                }
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
            elif format == 'csv':
                import csv
                with open(output_path, 'w', newline='') as f:
                    if metrics:
                        writer = csv.DictWriter(f, fieldnames=metrics[0].to_dict().keys())
                        writer.writeheader()
                        for m in metrics:
                            writer.writerow(m.to_dict())
            else:
                self._logger.error(f"Unknown export format: {format}")
                return None

            return output_path

        except IOError as e:
            self._logger.error(f"Failed to export metrics to {output_path}: {e}")
            return None
        except (TypeError, ValueError) as e:
            self._logger.error(f"Failed to serialize metrics for export: {e}")
            return None


def track_execution(
    metric_type: MetricType,
    operation: str,
    project_id: Optional[int] = None
) -> Callable:
    """
    Decorator to automatically track function execution.

    Args:
        metric_type: Type of operation
        operation: Operation name
        project_id: Optional project ID

    Example:
        @track_execution(MetricType.PDF_GENERATION, "generate_summary_report")
        def generate_report(project_id):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracker = get_metrics_tracker()
            start_time = time.perf_counter()

            # Try to extract project_id from args/kwargs
            pid = project_id
            if pid is None:
                pid = kwargs.get('project_id')
                if pid is None and args:
                    # Assume first positional arg might be project_id
                    if isinstance(args[0], int):
                        pid = args[0]

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                tracker.record_success(
                    metric_type=metric_type,
                    operation=operation,
                    duration_ms=duration_ms,
                    project_id=pid
                )

                return result

            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000

                tracker.record_failure(
                    metric_type=metric_type,
                    operation=operation,
                    duration_ms=duration_ms,
                    error_message=str(e),
                    project_id=pid
                )

                raise

        return wrapper
    return decorator


# Singleton instance
_metrics_tracker: Optional[MetricsTracker] = None
_tracker_lock = threading.Lock()


def get_metrics_tracker(storage_path: Optional[Path] = None) -> MetricsTracker:
    """Get or create the singleton MetricsTracker instance."""
    global _metrics_tracker

    with _tracker_lock:
        if _metrics_tracker is None:
            _metrics_tracker = MetricsTracker(storage_path)
        return _metrics_tracker
