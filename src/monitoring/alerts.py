"""
Alerting system for P6 Planning Integration.

Monitors metrics and triggers alerts on failures, thresholds, and anomalies.
"""

import json
import os
import smtplib
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import logging

from .metrics import MetricsTracker, MetricType, get_metrics_tracker


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Single alert record."""
    alert_id: str
    level: str
    title: str
    message: str
    timestamp: str
    source: str  # Component that generated the alert
    metric_type: Optional[str] = None
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Alert':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class AlertThreshold:
    """Configuration for alert thresholds."""
    metric_type: MetricType
    failure_count_threshold: int = 3  # Alert after N consecutive failures
    failure_rate_threshold: float = 25.0  # Alert if failure rate exceeds %
    duration_threshold_ms: float = 60000  # Alert if operation exceeds ms
    check_window_minutes: int = 60  # Time window to check


class AlertManager:
    """
    Manages alerts for monitoring system.

    Monitors metrics, generates alerts, and handles notifications.
    Use get_alert_manager() for singleton access.
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        metrics_tracker: Optional[MetricsTracker] = None
    ):
        """Initialize alert manager."""
        if storage_path is None:
            base_dir = Path(__file__).parent.parent.parent
            storage_path = base_dir / "logs" / "alerts"

        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._metrics_tracker = metrics_tracker or get_metrics_tracker()
        self._alerts: List[Alert] = []
        self._alert_counter = 0
        self._thresholds: Dict[MetricType, AlertThreshold] = {}
        self._handlers: List[Callable[[Alert], None]] = []
        self._current_file = self._get_alerts_filename()
        self._lock = threading.Lock()

        # Set up default thresholds
        self._setup_default_thresholds()

        # Load existing alerts
        self._load_alerts()

        # Set up logging
        self._logger = logging.getLogger('P6Alerts')

    def _get_alerts_filename(self, date: Optional[datetime] = None) -> Path:
        """Get alerts filename for a given date."""
        if date is None:
            date = datetime.now()
        return self.storage_path / f"alerts_{date.strftime('%Y%m%d')}.json"

    def _setup_default_thresholds(self) -> None:
        """Set up default alert thresholds."""
        # GUI automation - more sensitive due to UI fragility
        self._thresholds[MetricType.GUI_AUTOMATION] = AlertThreshold(
            metric_type=MetricType.GUI_AUTOMATION,
            failure_count_threshold=2,
            failure_rate_threshold=20.0,
            duration_threshold_ms=120000,
            check_window_minutes=30
        )

        # PDF generation
        self._thresholds[MetricType.PDF_GENERATION] = AlertThreshold(
            metric_type=MetricType.PDF_GENERATION,
            failure_count_threshold=3,
            failure_rate_threshold=30.0,
            duration_threshold_ms=60000,
            check_window_minutes=60
        )

        # Database queries
        self._thresholds[MetricType.DATABASE_QUERY] = AlertThreshold(
            metric_type=MetricType.DATABASE_QUERY,
            failure_count_threshold=5,
            failure_rate_threshold=10.0,
            duration_threshold_ms=30000,
            check_window_minutes=60
        )

        # Batch processing
        self._thresholds[MetricType.BATCH_PROCESS] = AlertThreshold(
            metric_type=MetricType.BATCH_PROCESS,
            failure_count_threshold=1,
            failure_rate_threshold=50.0,
            duration_threshold_ms=600000,
            check_window_minutes=120
        )

        # Default for other types
        for mt in MetricType:
            if mt not in self._thresholds:
                self._thresholds[mt] = AlertThreshold(
                    metric_type=mt,
                    failure_count_threshold=3,
                    failure_rate_threshold=25.0,
                    duration_threshold_ms=60000,
                    check_window_minutes=60
                )

    def _load_alerts(self) -> None:
        """Load alerts from current day's file."""
        if self._current_file.exists():
            try:
                with open(self._current_file, 'r') as f:
                    data = json.load(f)
                    self._alerts = [
                        Alert.from_dict(a) for a in data.get('alerts', [])
                    ]
                    self._alert_counter = data.get('counter', 0)
            except (json.JSONDecodeError, KeyError):
                self._alerts = []

    def _save_alerts(self) -> None:
        """Save alerts to JSON file."""
        data = {
            'last_updated': datetime.now().isoformat(),
            'counter': self._alert_counter,
            'alerts': [a.to_dict() for a in self._alerts]
        }
        with open(self._current_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def _generate_alert_id(self) -> str:
        """Generate unique alert ID."""
        self._alert_counter += 1
        return f"ALT-{datetime.now().strftime('%Y%m%d')}-{self._alert_counter:04d}"

    def create_alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        source: str,
        metric_type: Optional[MetricType] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """
        Create and record a new alert.

        Args:
            level: Alert severity level
            title: Short alert title
            message: Detailed message
            source: Component that generated alert
            metric_type: Related metric type if applicable
            details: Additional details

        Returns:
            Created Alert object
        """
        alert = Alert(
            alert_id=self._generate_alert_id(),
            level=level.value,
            title=title,
            message=message,
            timestamp=datetime.now().isoformat(),
            source=source,
            metric_type=metric_type.value if metric_type else None,
            details=details or {}
        )

        with self._lock:
            self._alerts.append(alert)
            self._save_alerts()

        # Log the alert
        log_method = getattr(self._logger, level.value, self._logger.info)
        log_method(f"[{alert.alert_id}] {title}: {message}")

        # Notify handlers
        self._notify_handlers(alert)

        return alert

    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add an alert handler callback."""
        self._handlers.append(handler)

    def _notify_handlers(self, alert: Alert) -> None:
        """Notify all registered handlers about an alert."""
        for handler in self._handlers:
            try:
                handler(alert)
            except Exception as e:
                self._logger.error(f"Alert handler error: {e}")

    def check_thresholds(self) -> List[Alert]:
        """
        Check all metric thresholds and generate alerts if needed.

        Returns:
            List of new alerts generated
        """
        new_alerts = []

        for metric_type, threshold in self._thresholds.items():
            alerts = self._check_threshold(metric_type, threshold)
            new_alerts.extend(alerts)

        return new_alerts

    def _check_threshold(
        self,
        metric_type: MetricType,
        threshold: AlertThreshold
    ) -> List[Alert]:
        """Check thresholds for a specific metric type."""
        alerts = []
        since = datetime.now() - timedelta(minutes=threshold.check_window_minutes)

        metrics = self._metrics_tracker.get_metrics(
            metric_type=metric_type,
            since=since
        )

        if not metrics:
            return alerts

        # Check failure rate
        failures = [m for m in metrics if m.status == 'failure']
        failure_rate = (len(failures) / len(metrics)) * 100

        if failure_rate >= threshold.failure_rate_threshold:
            alerts.append(self.create_alert(
                level=AlertLevel.ERROR,
                title=f"High Failure Rate: {metric_type.value}",
                message=f"Failure rate of {failure_rate:.1f}% exceeds threshold "
                        f"of {threshold.failure_rate_threshold}% "
                        f"({len(failures)}/{len(metrics)} operations failed)",
                source="threshold_monitor",
                metric_type=metric_type,
                details={
                    'failure_rate': failure_rate,
                    'threshold': threshold.failure_rate_threshold,
                    'failed_count': len(failures),
                    'total_count': len(metrics),
                    'window_minutes': threshold.check_window_minutes
                }
            ))

        # Check consecutive failures
        recent_metrics = sorted(metrics, key=lambda m: m.timestamp, reverse=True)
        consecutive_failures = 0
        for m in recent_metrics:
            if m.status == 'failure':
                consecutive_failures += 1
            else:
                break

        if consecutive_failures >= threshold.failure_count_threshold:
            # Check if we already alerted for this
            recent_alerts = [
                a for a in self._alerts
                if a.metric_type == metric_type.value
                and 'consecutive_failures' in a.details
                and a.timestamp > since.isoformat()
            ]

            if not recent_alerts:
                alerts.append(self.create_alert(
                    level=AlertLevel.CRITICAL,
                    title=f"Consecutive Failures: {metric_type.value}",
                    message=f"{consecutive_failures} consecutive failures detected",
                    source="threshold_monitor",
                    metric_type=metric_type,
                    details={
                        'consecutive_failures': consecutive_failures,
                        'threshold': threshold.failure_count_threshold,
                        'last_error': failures[0].error_message if failures else None
                    }
                ))

        # Check slow operations
        slow_ops = [
            m for m in metrics
            if m.status == 'success' and m.duration_ms > threshold.duration_threshold_ms
        ]

        if len(slow_ops) > 2:  # Alert if multiple slow operations
            avg_duration = sum(m.duration_ms for m in slow_ops) / len(slow_ops)
            alerts.append(self.create_alert(
                level=AlertLevel.WARNING,
                title=f"Slow Operations: {metric_type.value}",
                message=f"{len(slow_ops)} operations exceeded {threshold.duration_threshold_ms}ms "
                        f"(avg: {avg_duration:.0f}ms)",
                source="threshold_monitor",
                metric_type=metric_type,
                details={
                    'slow_count': len(slow_ops),
                    'avg_duration_ms': avg_duration,
                    'threshold_ms': threshold.duration_threshold_ms
                }
            ))

        return alerts

    def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str = "system"
    ) -> Optional[Alert]:
        """
        Acknowledge an alert.

        Args:
            alert_id: Alert ID to acknowledge
            acknowledged_by: Who acknowledged the alert

        Returns:
            Updated Alert or None if not found
        """
        with self._lock:
            for alert in self._alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    alert.acknowledged_at = datetime.now().isoformat()
                    alert.acknowledged_by = acknowledged_by
                    self._save_alerts()
                    return alert
        return None

    def get_alerts(
        self,
        level: Optional[AlertLevel] = None,
        acknowledged: Optional[bool] = None,
        metric_type: Optional[MetricType] = None,
        since: Optional[datetime] = None
    ) -> List[Alert]:
        """Get alerts with optional filtering."""
        results = self._alerts.copy()

        if level:
            results = [a for a in results if a.level == level.value]

        if acknowledged is not None:
            results = [a for a in results if a.acknowledged == acknowledged]

        if metric_type:
            results = [a for a in results if a.metric_type == metric_type.value]

        if since:
            since_str = since.isoformat()
            results = [a for a in results if a.timestamp >= since_str]

        return results

    def get_unacknowledged_alerts(self) -> List[Alert]:
        """Get all unacknowledged alerts."""
        return self.get_alerts(acknowledged=False)

    def get_critical_alerts(self) -> List[Alert]:
        """Get all critical-level alerts."""
        return self.get_alerts(level=AlertLevel.CRITICAL)

    def set_threshold(
        self,
        metric_type: MetricType,
        threshold: AlertThreshold
    ) -> None:
        """Set custom threshold for a metric type."""
        self._thresholds[metric_type] = threshold

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of current alert status."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_alerts = self.get_alerts(since=today)

        return {
            'total_alerts_today': len(today_alerts),
            'unacknowledged': len([a for a in today_alerts if not a.acknowledged]),
            'by_level': {
                level.value: len([a for a in today_alerts if a.level == level.value])
                for level in AlertLevel
            },
            'critical_count': len([a for a in today_alerts if a.level == AlertLevel.CRITICAL.value]),
            'latest_alert': today_alerts[-1].to_dict() if today_alerts else None
        }


class EmailAlertHandler:
    """Handler that sends alerts via email."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        sender_email: str,
        recipient_emails: List[str],
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        use_tls: bool = True,
        min_level: AlertLevel = AlertLevel.ERROR
    ):
        """Initialize email handler."""
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.recipient_emails = recipient_emails
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.use_tls = use_tls
        self.min_level = min_level

        self._level_order = {
            AlertLevel.INFO.value: 0,
            AlertLevel.WARNING.value: 1,
            AlertLevel.ERROR.value: 2,
            AlertLevel.CRITICAL.value: 3
        }

    def __call__(self, alert: Alert) -> None:
        """Handle alert by sending email if it meets minimum level."""
        if self._level_order.get(alert.level, 0) < self._level_order.get(self.min_level.value, 0):
            return

        self._send_email(alert)

    def _send_email(self, alert: Alert) -> None:
        """Send email notification for alert."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{alert.level.upper()}] P6 Alert: {alert.title}"
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(self.recipient_emails)

            # Plain text version
            text = f"""
P6 Planning Integration Alert

Level: {alert.level.upper()}
Title: {alert.title}
Time: {alert.timestamp}
Source: {alert.source}

Message:
{alert.message}

Alert ID: {alert.alert_id}
"""

            # HTML version
            html = f"""
<html>
<body>
<h2 style="color: {'red' if alert.level == 'critical' else 'orange' if alert.level == 'error' else 'black'}">
    P6 Planning Integration Alert
</h2>
<table>
    <tr><td><strong>Level:</strong></td><td>{alert.level.upper()}</td></tr>
    <tr><td><strong>Title:</strong></td><td>{alert.title}</td></tr>
    <tr><td><strong>Time:</strong></td><td>{alert.timestamp}</td></tr>
    <tr><td><strong>Source:</strong></td><td>{alert.source}</td></tr>
</table>
<h3>Message</h3>
<p>{alert.message}</p>
<p><small>Alert ID: {alert.alert_id}</small></p>
</body>
</html>
"""

            msg.attach(MIMEText(text, 'plain'))
            msg.attach(MIMEText(html, 'html'))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                server.sendmail(
                    self.sender_email,
                    self.recipient_emails,
                    msg.as_string()
                )

        except Exception as e:
            logging.error(f"Failed to send alert email: {e}")


class ConsoleAlertHandler:
    """Handler that prints alerts to console."""

    def __init__(self, min_level: AlertLevel = AlertLevel.WARNING):
        """Initialize console handler."""
        self.min_level = min_level
        self._level_order = {
            AlertLevel.INFO.value: 0,
            AlertLevel.WARNING.value: 1,
            AlertLevel.ERROR.value: 2,
            AlertLevel.CRITICAL.value: 3
        }

    def __call__(self, alert: Alert) -> None:
        """Print alert to console."""
        if self._level_order.get(alert.level, 0) < self._level_order.get(self.min_level.value, 0):
            return

        level_colors = {
            'info': '',
            'warning': '\033[93m',  # Yellow
            'error': '\033[91m',    # Red
            'critical': '\033[91m\033[1m'  # Bold Red
        }
        reset = '\033[0m'
        color = level_colors.get(alert.level, '')

        print(f"{color}[{alert.level.upper()}] {alert.title}{reset}")
        print(f"  {alert.message}")
        print(f"  Time: {alert.timestamp} | ID: {alert.alert_id}")


# Singleton instance
_alert_manager: Optional[AlertManager] = None
_manager_lock = threading.Lock()


def get_alert_manager(
    storage_path: Optional[Path] = None,
    metrics_tracker: Optional[MetricsTracker] = None
) -> AlertManager:
    """Get or create the singleton AlertManager instance."""
    global _alert_manager

    with _manager_lock:
        if _alert_manager is None:
            _alert_manager = AlertManager(storage_path, metrics_tracker)
        return _alert_manager
