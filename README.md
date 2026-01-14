# P6 Planning Integration

A comprehensive Python platform for Oracle Primavera P6 Professional with full GUI automation, PDF reporting, and AI agent integration.

## Development Progress

### Completed Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Environment Setup & P6 Discovery | ✅ Complete |
| 2 | P6 Process Control | ✅ Complete |
| 3 | P6 Window & Dialog Automation | ✅ Complete |
| 4 | Project Selection & Navigation | ✅ Complete |
| 5 | Report Export Automation | ✅ Complete |
| 6 | Batch Processing Engine | ✅ Complete |
| 7 | Post-Processing & PDF Generation | ✅ Complete |
| 8 | Reliability & Error Handling | ✅ Complete |
| 9 | CLI & Scheduling Integration | ✅ Complete |
| 10 | Testing & Documentation | ✅ Complete |
| 11 | Monitoring & Maintenance | ✅ Complete |

**Overall Progress:** 100% - All Phases Complete!

---

## Command Line Interface

The CLI provides full access to all P6 Planning Integration features.

### Quick Reference

```bash
# Show help
python main.py --help

# List all projects
python main.py --list-projects
python main.py -l --verbose

# Generate PDF reports
python main.py --report summary --project 123
python main.py --report critical --project 123
python main.py --report health --project 123
python main.py --report comprehensive --project 123 --landscape

# Run schedule analysis
python main.py --analyze --project 123
python main.py --analyze --project 123 --export-json

# Parse schedule files
python main.py schedule.xer
python main.py project.xml

# Test database connection
python main.py --test
```

### CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--list-projects` | `-l` | List all available projects |
| `--report TYPE` | `-r` | Generate PDF report (summary, critical, health, comprehensive) |
| `--analyze` | `-a` | Run schedule health check analysis |
| `--test` | `-t` | Test database connection |
| `--chat` | `-c` | Start interactive AI chat mode |
| `--project ID` | `-p` | Project ObjectId for commands |
| `--output FILE` | `-o` | Output filename for reports |
| `--landscape` | | Use landscape orientation |
| `--verbose` | `-v` | Show verbose output |
| `--export-json` | | Export analysis results to JSON |

### Report Types

| Type | Description |
|------|-------------|
| `summary` | Executive-level schedule overview with statistics |
| `critical` | Critical path analysis with float distribution |
| `health` | Schedule quality validation (DCMA/AACE standards) |
| `comprehensive` | Multi-section combined report |

### Windows Batch Scripts

Located in `scripts/` for Task Scheduler automation:

| Script | Purpose |
|--------|---------|
| `p6cli.bat` | Quick command wrapper |
| `generate_daily_reports.bat` | Generate daily summary reports |
| `run_health_check.bat` | Run health analysis with export |
| `generate_comprehensive_report.bat` | Generate full project reports |

**Example: Schedule daily reports with Task Scheduler**

```batch
# Create a scheduled task to run at 6:00 AM daily
schtasks /create /tn "P6 Daily Reports" /tr "C:\path\to\scripts\generate_daily_reports.bat" /sc daily /st 06:00
```

---

## Features

### GUI Automation (15 Modules)

| Module | Class | Purpose |
|--------|-------|---------|
| base.py | `P6AutomationBase` | Connection/window management |
| connection.py | `P6ConnectionManager` | Process detection, login |
| navigation.py | `P6Navigator` | Menu, toolbar, status bar |
| printing.py | `P6PrintManager` | Print preview, PDF output |
| exporting.py | `P6ExportManager` | XER, XML, Excel export |
| projects.py | `P6ProjectManager` | Project tree, open/close |
| layouts.py | `P6LayoutManager` | Layouts, views, filters |
| scheduling.py | `P6ScheduleManager` | F9, leveling, schedule check |
| scheduling.py | `P6BaselineManager` | Baseline CRUD operations |
| activities.py | `P6ActivityManager` | Activity select/edit |
| batch.py | `P6BatchProcessor` | Batch operations coordination |
| agent.py | `P6AgentInterface` | AI agent integration |

### PDF Report Generation

Professional PDF reports generated from P6 schedule data:

| Report Type | Description |
|-------------|-------------|
| Schedule Summary | Executive-level project overview with statistics |
| Critical Path | Detailed critical path analysis with float distribution |
| Health Check | Schedule quality validation (DCMA/AACE standards) |
| Comprehensive | Multi-section combined report |

### Database Access (SQLite DAOs)

| DAO | Purpose |
|-----|---------|
| `SQLiteProjectDAO` | Project queries |
| `SQLiteActivityDAO` | Activity queries with duration conversion |
| `SQLiteRelationshipDAO` | Task relationship queries |
| `SQLiteWBSDAO` | WBS structure queries |

### Schedule Analysis

| Analyzer | Purpose |
|----------|---------|
| `ScheduleAnalyzer` | Health checks, quality validation |
| `CriticalPathAnalyzer` | Critical path calculation |
| `ProgressTracker` | Progress tracking metrics |

---

## Quick Start

### Using the CLI

```bash
# 1. First, list available projects
python main.py --list-projects

# 2. Generate a summary report for a project
python main.py --report summary --project 123

# 3. Run health check analysis
python main.py --analyze --project 123

# 4. Generate comprehensive report with landscape orientation
python main.py --report comprehensive --project 123 --landscape --output monthly_report.pdf
```

### GUI Automation

```python
from src.automation import P6PrintAutomation

with P6PrintAutomation() as p6:
    p6.open_project("My Project")
    p6.apply_layout("Monthly Report")
    p6.print_to_pdf("report.pdf")
```

### PDF Report Generation (Python API)

```python
from src.reporting import PDFGenerator, generate_pdf_report
from src.dao.sqlite import SQLiteManager

# Using convenience function
output = generate_pdf_report(
    project_id=123,
    report_type='summary'  # 'summary', 'critical', 'health', 'comprehensive'
)
print(f"Report: {output}")

# Using PDFGenerator class directly
with SQLiteManager() as manager:
    pdf_gen = PDFGenerator()
    pdf_gen.set_manager(manager)

    # Generate different report types
    pdf_gen.generate_schedule_summary(project_id=123)
    pdf_gen.generate_critical_path_report(project_id=123)
    pdf_gen.generate_health_check_report(project_id=123)
    pdf_gen.generate_comprehensive_report(project_id=123)
```

### Database Queries

```python
from src.dao.sqlite import SQLiteManager

with SQLiteManager() as manager:
    project_dao = manager.get_project_dao()
    activity_dao = manager.get_activity_dao()

    # Get all projects
    projects = project_dao.get_active_projects()

    # Get activities for a project
    activities = activity_dao.get_activities_for_project(project_id=123)

    # Get critical activities
    critical = activity_dao.get_critical_activities(project_id=123)
```

---

## Testing

### Test Coverage Summary

| Category | Coverage | Tests |
|----------|----------|-------|
| **Overall** | 31% | 243 |
| PDF Styles | 100% | 72 |
| PDF Generator | 93% | 28 |
| Schedule Analyzer | 100% | 40+ |
| Automation Exceptions | 100% | 20 |
| Automation Utilities | 47% | 25 |
| SQLite DAOs | 44-92% | 30+ |

**Key Modules at 100% Coverage:**
- `src/reporting/pdf_styles.py`
- `src/analyzers/schedule_analyzer.py`
- `src/automation/exceptions.py`
- `src/automation/__init__.py`

### Running Tests

```bash
# Run all tests
pytest tests/

# Run unit tests (no P6 or database required)
pytest tests/ -m "not integration"

# Run integration tests (requires P6 database)
pytest tests/ -m integration

# Run all tests with coverage
pytest tests/ --cov=src --cov-report=html

# Run E2E tests (P6 must be running)
pytest tests/test_automation_e2e.py --with-p6

# Run specific test files
pytest tests/test_pdf_generator.py -v
pytest tests/test_schedule_analyzer.py -v
```

---

## Configuration

Create a `.env` file in the project root:

```env
# Connection Mode
P6_CONNECTION_MODE=SQLITE  # or JAVA

# SQLite Mode Settings
P6_DB_PATH=C:\path\to\userdata.db

# GUI Automation Settings
P6_EXECUTABLE_PATH=C:\Program Files\Oracle\Primavera P6\PM.exe
PDF_PRINTER_NAME=Microsoft Print to PDF
PDF_OUTPUT_DIR=reports/pdf

# Safety Settings
SAFE_MODE=true
```

---

## Project Structure

```
P6PlanningIntegration/
├── src/
│   ├── automation/          # GUI automation modules (15 files)
│   ├── dao/sqlite/          # SQLite DAOs (8 files)
│   ├── analyzers/           # Schedule analysis (3 files)
│   ├── reporting/           # PDF & data export (5 files)
│   ├── ingestion/           # File parsers (XER, XML, MPX)
│   ├── config/              # Configuration management
│   ├── core/                # Data model definitions
│   ├── ai/                  # AI agent integration
│   ├── monitoring/          # Metrics, alerts, dashboards
│   └── utils/               # Logging, file management
├── tests/                   # Test suite (17 files, 277 tests)
├── scripts/                 # Windows batch scripts
├── docs/                    # Documentation
├── directives/              # SOPs and workflows
├── execution/               # Deterministic scripts
├── reports/                 # Output directory
└── logs/                    # Runtime logs
```

---

## Dependencies

```
# Core
pywinauto>=0.6.8       # Windows GUI automation
psutil>=5.9.0          # Process detection
pandas>=2.0.0          # Data processing

# Reporting
reportlab>=4.0.0       # PDF generation
pillow>=10.0.0         # Image handling
openpyxl>=3.0.0        # Excel export

# Configuration
python-dotenv>=1.0.0   # Environment loading

# Development
pytest>=7.0.0          # Testing
pytest-cov>=4.0.0      # Coverage
```

Install all dependencies:

```bash
pip install -r requirements.txt
```

---

## Safe Mode

Write operations require explicit `safe_mode=False`:

```python
# Read-only (default) - safe for production
scheduler = P6ScheduleManager(window, safe_mode=True)

# Enable modifications - use with caution
scheduler = P6ScheduleManager(window, safe_mode=False)
```

---

## Monitoring & Alerting

The monitoring system tracks execution metrics, generates alerts, and provides dashboards.

### Quick Start

```python
from src.monitoring import (
    get_metrics_tracker,
    get_alert_manager,
    generate_monitoring_report,
    MetricType
)

# Track operations
tracker = get_metrics_tracker()
tracker.record_success(MetricType.PDF_GENERATION, "generate_report", 1500.0)

# Generate reports
print(generate_monitoring_report(format='text', hours=24))

# Check system health
from src.monitoring import MonitoringDashboard
dashboard = MonitoringDashboard()
health = dashboard.get_system_health()
print(f"Status: {health.status}, Score: {health.score}")
```

### Monitoring Features

| Feature | Description |
|---------|-------------|
| **Metrics Tracking** | Automatic recording of operation success/failure/duration |
| **Alert Management** | Threshold-based alerts with acknowledgement workflow |
| **HTML Dashboard** | Visual dashboard with health scores and trends |
| **Text Reports** | Console-friendly monitoring reports |
| **JSON Export** | Machine-readable metrics for integration |

### Alert Levels

| Level | Description | Response |
|-------|-------------|----------|
| INFO | Informational | No action |
| WARNING | Potential issue | Monitor closely |
| ERROR | Operation failed | Investigate |
| CRITICAL | System impact | Immediate action |

### Maintenance Guide

See `docs/MAINTENANCE.md` for:
- Daily/weekly/monthly checklists
- Troubleshooting guide
- P6 version compatibility
- Log file management
- Backup procedures

---

## Future Enhancements

### Potential Improvements
- Expand test coverage for GUI automation modules
- Add more E2E test scenarios
- Performance optimization for large schedules
- Additional report templates
- Slack/Teams webhook integration for alerts

---

## Mining Industry Standards

This project follows mining industry scheduling best practices:

- **Float Thresholds:** Critical (≤0), Near-critical (1-10), Low (11-30), Moderate (31-60)
- **Duration Limits:** Flag activities >20 days
- **Logic Density:** Target ≥1.8 relationships per activity
- **Constraint Limits:** <5% constrained activities
- **DCMA 14-Point Assessment** compliance

---

## License

See LICENSE file.

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests: `pytest tests/`
4. Submit a pull request

---

*Generated with Claude Code*
