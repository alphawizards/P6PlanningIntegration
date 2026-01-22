"""
Monitoring dashboard and report generation for P6 Planning Integration.

Generates HTML dashboards and text reports from metrics and alerts.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from .metrics import MetricsTracker, MetricType, MetricsSummary, get_metrics_tracker
from .alerts import AlertManager, AlertLevel, Alert, get_alert_manager


@dataclass
class SystemHealthStatus:
    """Overall system health status."""
    status: str  # 'healthy', 'degraded', 'critical'
    score: float  # 0-100
    message: str
    timestamp: str
    metrics_summary: Dict[str, Any]
    active_alerts: int
    critical_alerts: int


class MonitoringDashboard:
    """
    Generates monitoring dashboards and health reports.
    """

    def __init__(
        self,
        metrics_tracker: Optional[MetricsTracker] = None,
        alert_manager: Optional[AlertManager] = None
    ):
        """Initialize dashboard."""
        self._metrics = metrics_tracker or get_metrics_tracker()
        self._alerts = alert_manager or get_alert_manager()

    def get_system_health(self) -> SystemHealthStatus:
        """
        Calculate overall system health status.

        Returns:
            SystemHealthStatus with current health assessment
        """
        # Get metrics from last hour
        since = datetime.now() - timedelta(hours=1)
        summary = self._metrics.get_summary(since=since)

        # Get active alerts
        active_alerts = self._alerts.get_unacknowledged_alerts()
        critical_alerts = [a for a in active_alerts if a.level == AlertLevel.CRITICAL.value]

        # Calculate health score
        score = 100.0

        # Deduct for failure rate
        if summary.total_operations > 0:
            failure_penalty = min(summary.success_rate, 100) - 100  # Negative for failures
            score += failure_penalty * 0.5

        # Deduct for alerts
        score -= len(active_alerts) * 5
        score -= len(critical_alerts) * 15

        # Ensure score is in valid range
        score = max(0, min(100, score))

        # Determine status
        if score >= 90:
            status = 'healthy'
            message = 'All systems operating normally'
        elif score >= 70:
            status = 'degraded'
            message = 'Some issues detected, monitoring recommended'
        else:
            status = 'critical'
            message = 'Critical issues detected, immediate attention required'

        return SystemHealthStatus(
            status=status,
            score=round(score, 1),
            message=message,
            timestamp=datetime.now().isoformat(),
            metrics_summary=summary.to_dict(),
            active_alerts=len(active_alerts),
            critical_alerts=len(critical_alerts)
        )

    def generate_text_report(
        self,
        hours: int = 24,
        include_details: bool = True
    ) -> str:
        """
        Generate a text-based monitoring report.

        Args:
            hours: Number of hours to include in report
            include_details: Include detailed metrics breakdown

        Returns:
            Formatted text report
        """
        since = datetime.now() - timedelta(hours=hours)
        health = self.get_system_health()

        lines = [
            "=" * 70,
            "P6 PLANNING INTEGRATION - MONITORING REPORT",
            "=" * 70,
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Period: Last {hours} hours",
            "",
            "-" * 70,
            "SYSTEM HEALTH",
            "-" * 70,
            "",
            f"  Status: {health.status.upper()}",
            f"  Health Score: {health.score}/100",
            f"  Message: {health.message}",
            "",
            f"  Active Alerts: {health.active_alerts}",
            f"  Critical Alerts: {health.critical_alerts}",
            "",
        ]

        # Overall metrics summary
        summary = self._metrics.get_summary(since=since)
        lines.extend([
            "-" * 70,
            "OPERATIONS SUMMARY",
            "-" * 70,
            "",
            f"  Total Operations: {summary.total_operations}",
            f"  Successful: {summary.successful}",
            f"  Failed: {summary.failed}",
            f"  Warnings: {summary.warnings}",
            f"  Success Rate: {summary.success_rate:.1f}%",
            "",
            f"  Avg Duration: {summary.avg_duration_ms:.0f}ms",
            f"  Min Duration: {summary.min_duration_ms:.0f}ms",
            f"  Max Duration: {summary.max_duration_ms:.0f}ms",
            "",
        ])

        if include_details:
            # Breakdown by metric type
            lines.extend([
                "-" * 70,
                "BREAKDOWN BY OPERATION TYPE",
                "-" * 70,
                "",
            ])

            for metric_type in MetricType:
                type_summary = self._metrics.get_summary(metric_type=metric_type, since=since)
                if type_summary.total_operations > 0:
                    lines.extend([
                        f"  {metric_type.value}:",
                        f"    Operations: {type_summary.total_operations}",
                        f"    Success Rate: {type_summary.success_rate:.1f}%",
                        f"    Avg Duration: {type_summary.avg_duration_ms:.0f}ms",
                        "",
                    ])

            # Recent failures
            failures = self._metrics.get_recent_failures(count=5)
            if failures:
                lines.extend([
                    "-" * 70,
                    "RECENT FAILURES",
                    "-" * 70,
                    "",
                ])
                for f in failures:
                    lines.extend([
                        f"  [{f.timestamp}] {f.metric_type}/{f.operation}",
                        f"    Error: {f.error_message}",
                        "",
                    ])

            # Active alerts
            alerts = self._alerts.get_unacknowledged_alerts()
            if alerts:
                lines.extend([
                    "-" * 70,
                    "ACTIVE ALERTS",
                    "-" * 70,
                    "",
                ])
                for a in alerts:
                    lines.extend([
                        f"  [{a.level.upper()}] {a.title}",
                        f"    {a.message}",
                        f"    Time: {a.timestamp} | ID: {a.alert_id}",
                        "",
                    ])

        lines.extend([
            "=" * 70,
            "END OF REPORT",
            "=" * 70,
        ])

        return "\n".join(lines)

    def generate_html_dashboard(
        self,
        hours: int = 24,
        output_path: Optional[Path] = None
    ) -> str:
        """
        Generate an HTML monitoring dashboard.

        Args:
            hours: Number of hours to include
            output_path: Optional path to save HTML file

        Returns:
            HTML content string
        """
        since = datetime.now() - timedelta(hours=hours)
        health = self.get_system_health()
        summary = self._metrics.get_summary(since=since)
        alerts = self._alerts.get_alerts(since=since)

        # Status color
        status_colors = {
            'healthy': '#28a745',
            'degraded': '#ffc107',
            'critical': '#dc3545'
        }
        status_color = status_colors.get(health.status, '#6c757d')

        # Build metrics by type data
        type_data = []
        for metric_type in MetricType:
            type_summary = self._metrics.get_summary(metric_type=metric_type, since=since)
            if type_summary.total_operations > 0:
                type_data.append({
                    'type': metric_type.value,
                    'total': type_summary.total_operations,
                    'success_rate': type_summary.success_rate,
                    'avg_duration': type_summary.avg_duration_ms
                })

        # Build alerts table rows
        alert_rows = ""
        for a in sorted(alerts, key=lambda x: x.timestamp, reverse=True)[:20]:
            level_class = 'danger' if a.level in ['critical', 'error'] else 'warning' if a.level == 'warning' else 'info'
            ack_badge = '<span class="badge bg-success">Ack</span>' if a.acknowledged else '<span class="badge bg-secondary">Open</span>'
            alert_rows += f"""
            <tr>
                <td><span class="badge bg-{level_class}">{a.level.upper()}</span></td>
                <td>{a.title}</td>
                <td>{a.timestamp[:19]}</td>
                <td>{ack_badge}</td>
            </tr>
            """

        # Build type summary rows
        type_rows = ""
        for t in type_data:
            success_class = 'success' if t['success_rate'] >= 90 else 'warning' if t['success_rate'] >= 70 else 'danger'
            type_rows += f"""
            <tr>
                <td>{t['type']}</td>
                <td>{t['total']}</td>
                <td><span class="text-{success_class}">{t['success_rate']:.1f}%</span></td>
                <td>{t['avg_duration']:.0f}ms</td>
            </tr>
            """

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>P6 Planning Integration - Monitoring Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #f8f9fa; }}
        .health-card {{ border-left: 5px solid {status_color}; }}
        .metric-card {{ transition: transform 0.2s; }}
        .metric-card:hover {{ transform: translateY(-2px); }}
        .dashboard-header {{ background: linear-gradient(135deg, #1a3a5c 0%, #2c5282 100%); color: white; }}
    </style>
</head>
<body>
    <div class="dashboard-header py-4 mb-4">
        <div class="container">
            <h1><i class="bi bi-graph-up"></i> P6 Planning Integration</h1>
            <p class="mb-0">Monitoring Dashboard - Last {hours} Hours</p>
        </div>
    </div>

    <div class="container">
        <!-- System Health -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card health-card">
                    <div class="card-body">
                        <div class="row align-items-center">
                            <div class="col-md-3">
                                <h2 class="mb-0" style="color: {status_color}">{health.status.upper()}</h2>
                                <p class="text-muted mb-0">System Status</p>
                            </div>
                            <div class="col-md-3">
                                <h2 class="mb-0">{health.score}</h2>
                                <p class="text-muted mb-0">Health Score</p>
                            </div>
                            <div class="col-md-3">
                                <h2 class="mb-0">{health.active_alerts}</h2>
                                <p class="text-muted mb-0">Active Alerts</p>
                            </div>
                            <div class="col-md-3">
                                <p class="mb-0">{health.message}</p>
                                <small class="text-muted">Updated: {health.timestamp[:19]}</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Metrics Summary -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card metric-card text-center">
                    <div class="card-body">
                        <h3 class="text-primary">{summary.total_operations}</h3>
                        <p class="mb-0">Total Operations</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card text-center">
                    <div class="card-body">
                        <h3 class="text-success">{summary.successful}</h3>
                        <p class="mb-0">Successful</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card text-center">
                    <div class="card-body">
                        <h3 class="text-danger">{summary.failed}</h3>
                        <p class="mb-0">Failed</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card text-center">
                    <div class="card-body">
                        <h3 class="{'text-success' if summary.success_rate >= 90 else 'text-warning' if summary.success_rate >= 70 else 'text-danger'}">{summary.success_rate:.1f}%</h3>
                        <p class="mb-0">Success Rate</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Two Column Layout -->
        <div class="row">
            <!-- Operations by Type -->
            <div class="col-md-6 mb-4">
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="mb-0">Operations by Type</h5>
                    </div>
                    <div class="card-body">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Type</th>
                                    <th>Count</th>
                                    <th>Success</th>
                                    <th>Avg Time</th>
                                </tr>
                            </thead>
                            <tbody>
                                {type_rows if type_rows else '<tr><td colspan="4" class="text-center text-muted">No data</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Recent Alerts -->
            <div class="col-md-6 mb-4">
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="mb-0">Recent Alerts</h5>
                    </div>
                    <div class="card-body">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Level</th>
                                    <th>Title</th>
                                    <th>Time</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {alert_rows if alert_rows else '<tr><td colspan="4" class="text-center text-muted">No alerts</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- Performance Metrics -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">Performance Metrics</h5>
                    </div>
                    <div class="card-body">
                        <div class="row text-center">
                            <div class="col-md-3">
                                <h4>{summary.avg_duration_ms:.0f}ms</h4>
                                <p class="text-muted">Avg Duration</p>
                            </div>
                            <div class="col-md-3">
                                <h4>{summary.min_duration_ms:.0f}ms</h4>
                                <p class="text-muted">Min Duration</p>
                            </div>
                            <div class="col-md-3">
                                <h4>{summary.max_duration_ms:.0f}ms</h4>
                                <p class="text-muted">Max Duration</p>
                            </div>
                            <div class="col-md-3">
                                <h4>{summary.total_duration_ms/1000:.1f}s</h4>
                                <p class="text-muted">Total Time</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <footer class="text-center text-muted py-4">
            <small>P6 Planning Integration Monitoring | Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>
        </footer>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)

        return html

    def generate_json_report(
        self,
        hours: int = 24,
        output_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Generate a JSON monitoring report.

        Args:
            hours: Number of hours to include
            output_path: Optional path to save JSON file

        Returns:
            Report data dictionary
        """
        since = datetime.now() - timedelta(hours=hours)
        health = self.get_system_health()

        # Build type summaries
        type_summaries = {}
        for metric_type in MetricType:
            type_summary = self._metrics.get_summary(metric_type=metric_type, since=since)
            if type_summary.total_operations > 0:
                type_summaries[metric_type.value] = type_summary.to_dict()

        # Get failure rates
        failure_rates = self._metrics.get_failure_rate_by_type()

        report = {
            'generated_at': datetime.now().isoformat(),
            'period_hours': hours,
            'period_start': since.isoformat(),
            'system_health': {
                'status': health.status,
                'score': health.score,
                'message': health.message,
                'active_alerts': health.active_alerts,
                'critical_alerts': health.critical_alerts
            },
            'overall_summary': self._metrics.get_summary(since=since).to_dict(),
            'by_type': type_summaries,
            'failure_rates': failure_rates,
            'recent_failures': [
                m.to_dict() for m in self._metrics.get_recent_failures(count=10)
            ],
            'alerts_summary': self._alerts.get_alert_summary(),
            'unacknowledged_alerts': [
                a.to_dict() for a in self._alerts.get_unacknowledged_alerts()
            ]
        }

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)

        return report


def generate_monitoring_report(
    format: str = 'text',
    hours: int = 24,
    output_path: Optional[Path] = None
) -> str:
    """
    Convenience function to generate monitoring report.

    Args:
        format: 'text', 'html', or 'json'
        hours: Number of hours to include
        output_path: Optional output file path

    Returns:
        Report content (text/html) or JSON string
    """
    dashboard = MonitoringDashboard()

    if format == 'text':
        report = dashboard.generate_text_report(hours=hours)
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report)
        return report

    elif format == 'html':
        return dashboard.generate_html_dashboard(hours=hours, output_path=output_path)

    elif format == 'json':
        data = dashboard.generate_json_report(hours=hours, output_path=output_path)
        return json.dumps(data, indent=2, default=str)

    else:
        raise ValueError(f"Unknown format: {format}. Use 'text', 'html', or 'json'")
