# P6 Planning Integration - Maintenance Guide

## Overview

This guide covers routine maintenance procedures, monitoring, troubleshooting, and version compatibility for the P6 Planning Integration system.

---

## Maintenance Checklists

### Daily Checklist

- [ ] Review monitoring dashboard for any critical alerts
- [ ] Check success rates are above 90%
- [ ] Verify scheduled tasks completed successfully
- [ ] Review log files for unexpected errors

### Weekly Checklist

- [ ] Generate and review weekly monitoring report
- [ ] Check disk space for logs and reports directories
- [ ] Acknowledge and close resolved alerts
- [ ] Review slow operations and optimize if needed
- [ ] Verify PDF output quality on sample reports

### Monthly Checklist

- [ ] Test with current P6 version after any updates
- [ ] Review and archive old log files (>30 days)
- [ ] Update alert thresholds based on performance data
- [ ] Test database backup/restore procedures
- [ ] Review and update documentation as needed
- [ ] Check for dependency security updates

### Quarterly Checklist

- [ ] Update all Python dependencies
- [ ] Run full regression test suite
- [ ] Review and optimize GUI automation timing
- [ ] Update version compatibility matrix
- [ ] Archive metrics data older than 90 days
- [ ] Performance baseline comparison

---

## Monitoring System

### Generating Reports

```python
from src.monitoring import generate_monitoring_report

# Text report to console
print(generate_monitoring_report(format='text', hours=24))

# HTML dashboard to file
generate_monitoring_report(
    format='html',
    hours=24,
    output_path='reports/dashboard.html'
)

# JSON export
generate_monitoring_report(
    format='json',
    hours=168,  # Last week
    output_path='reports/weekly_metrics.json'
)
```

### CLI Commands

```bash
# Generate monitoring dashboard
python main.py --monitor --format html --output dashboard.html

# View recent alerts
python main.py --alerts --unacknowledged

# Check system health
python main.py --health-check
```

### Understanding Health Scores

| Score | Status | Action Required |
|-------|--------|-----------------|
| 90-100 | Healthy | None - normal operation |
| 70-89 | Degraded | Monitor closely, investigate trends |
| 50-69 | Warning | Investigate and address issues |
| 0-49 | Critical | Immediate attention required |

### Alert Levels

| Level | Description | Response Time |
|-------|-------------|---------------|
| INFO | Informational, no action needed | None |
| WARNING | Potential issue, monitor | Within 24 hours |
| ERROR | Operation failed, needs attention | Within 4 hours |
| CRITICAL | System impact, immediate action | Immediate |

---

## Log File Management

### Log Locations

```
P6PlanningIntegration/
├── logs/
│   ├── app.log           # Main application log
│   ├── automation.log    # GUI automation logs
│   ├── metrics/          # Daily metrics JSON files
│   │   └── metrics_YYYYMMDD.json
│   └── alerts/           # Daily alerts JSON files
│       └── alerts_YYYYMMDD.json
```

### Log Rotation

Logs are automatically organized by date. To archive old logs:

```bash
# Archive logs older than 30 days (Windows)
forfiles /p "logs" /s /m *.log /d -30 /c "cmd /c move @path archive/"

# Archive metrics older than 90 days
forfiles /p "logs\metrics" /s /m *.json /d -90 /c "cmd /c move @path archive/"
```

### Log Analysis

```python
# Count errors in recent logs
from pathlib import Path
import re

log_file = Path("logs/app.log")
errors = len(re.findall(r'\[ERROR\]', log_file.read_text()))
print(f"Errors found: {errors}")
```

---

## P6 Version Compatibility

### Tested Versions

| P6 Version | Status | Notes |
|------------|--------|-------|
| P6 Professional 21.12 | ✅ Fully Tested | Primary development version |
| P6 Professional 20.12 | ✅ Tested | Minor timing adjustments may be needed |
| P6 Professional 19.12 | ⚠️ Limited Testing | Some menu paths may differ |

### After P6 Updates

1. **Before updating P6:**
   - Document current working state
   - Take screenshots of key dialogs
   - Run full test suite as baseline

2. **After P6 update:**
   - Run discovery script to check UI elements
   - Test each automation module individually
   - Update timing constants if needed
   - Run full test suite
   - Document any required changes

3. **Common P6 update issues:**
   - Menu item text changes
   - Dialog layout modifications
   - New confirmation dialogs
   - Changed keyboard shortcuts

### UI Element Verification

```python
# Verify P6 UI elements after update
from pywinauto import Desktop

# Find P6 window
p6_window = Desktop(backend="uia").window(title_re=".*Primavera P6.*")

# Print all controls for inspection
p6_window.print_control_identifiers()
```

---

## Troubleshooting Guide

### Common Issues

#### 1. P6 Connection Failures

**Symptoms:** "P6 window not found" errors

**Solutions:**
- Verify P6 is running and visible
- Check P6 window title matches expected pattern
- Ensure P6 is not minimized
- Try increasing connection timeout

```python
# Increase timeout
from src.automation import P6ConnectionManager
conn = P6ConnectionManager(timeout=60)
```

#### 2. GUI Automation Timeouts

**Symptoms:** Operations fail with timeout errors

**Solutions:**
- Increase wait times in configuration
- Check P6 is not showing modal dialogs
- Verify system is not under heavy load
- Review screenshot captured on failure

```python
# Adjust timing
from src.automation.utils import wait_for_condition

# Increase wait time
wait_for_condition(condition_fn, timeout=30, poll_interval=0.5)
```

#### 3. PDF Generation Failures

**Symptoms:** PDF files not created or empty

**Solutions:**
- Verify Microsoft Print to PDF is available
- Check output directory permissions
- Ensure sufficient disk space
- Review print dialog settings

#### 4. Database Connection Issues

**Symptoms:** "Database not found" or query errors

**Solutions:**
- Verify P6_DB_PATH in .env file
- Check file permissions on SQLite database
- Ensure P6 is not locking the database
- Try read-only mode

```python
# Test database connection
from src.dao.sqlite import SQLiteManager

with SQLiteManager() as manager:
    projects = manager.get_project_dao().get_active_projects()
    print(f"Found {len(projects)} projects")
```

#### 5. High Failure Rates

**Symptoms:** Success rate drops below 90%

**Investigation steps:**
1. Check monitoring dashboard for patterns
2. Review recent failures in logs
3. Identify common failure points
4. Check for P6 updates or system changes
5. Verify network/system stability

### Debug Mode

Enable verbose logging for troubleshooting:

```python
import logging
logging.getLogger('P6Automation').setLevel(logging.DEBUG)
logging.getLogger('P6Alerts').setLevel(logging.DEBUG)
```

Or via CLI:

```bash
python main.py --verbose --debug
```

---

## Performance Optimization

### Key Metrics to Monitor

| Metric | Target | Action Threshold |
|--------|--------|------------------|
| Success Rate | >95% | <90% investigate |
| Avg PDF Generation | <30s | >60s optimize |
| Avg DB Query | <1s | >5s investigate |
| GUI Operation | <10s | >30s adjust timing |

### Optimization Strategies

1. **Reduce Wait Times:**
   - Use smart waits instead of fixed delays
   - Implement polling with early exit

2. **Batch Operations:**
   - Group multiple report generations
   - Use bulk database queries

3. **Cache Frequently Used Data:**
   - Project lists
   - Layout configurations
   - Static reference data

4. **Parallel Processing:**
   - Run independent operations concurrently
   - Use thread pools for batch jobs

---

## Backup and Recovery

### What to Backup

- `.env` configuration file
- `logs/` directory (or just metrics/alerts)
- Custom report templates
- Batch configuration files
- Any custom scripts

### Backup Schedule

| Item | Frequency | Retention |
|------|-----------|-----------|
| Configuration | Weekly | 4 versions |
| Logs | Daily | 30 days |
| Metrics | Weekly | 90 days |
| Full backup | Monthly | 6 months |

### Recovery Procedure

1. Install fresh Python environment
2. Clone repository or extract backup
3. Restore `.env` configuration
4. Install dependencies: `pip install -r requirements.txt`
5. Run test suite: `pytest tests/`
6. Verify P6 connection: `python main.py --test`

---

## Dependency Management

### Checking for Updates

```bash
# List outdated packages
pip list --outdated

# Check for security vulnerabilities
pip-audit
```

### Safe Update Procedure

1. Create virtual environment backup
2. Update one package at a time
3. Run test suite after each update
4. Document any compatibility issues

```bash
# Update specific package
pip install --upgrade package_name

# Run tests
pytest tests/ -v
```

### Key Dependencies

| Package | Purpose | Update Caution |
|---------|---------|----------------|
| pywinauto | GUI automation | High - may break automation |
| reportlab | PDF generation | Medium - API changes rare |
| pandas | Data processing | Low - stable API |
| pytest | Testing | Low - stable API |

---

## Support and Resources

### Getting Help

1. Check this maintenance guide
2. Review logs and monitoring dashboard
3. Search GitHub issues
4. Run diagnostic commands

### Useful Commands

```bash
# System health check
python main.py --health-check

# Test all connections
python main.py --test

# Generate diagnostic report
python main.py --diagnostics --output diagnostics.txt

# List all projects (verify DB)
python main.py --list-projects
```

### Contact

For issues not covered in this guide:
- Create GitHub issue with logs attached
- Include P6 version and system info
- Attach screenshots of any dialogs

---

*Last updated: January 2025*
