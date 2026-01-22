# P6 Planning Integration - Testing Guide

A comprehensive guide to testing the P6 Planning Integration project.

---

## Quick Start

```powershell
# Install dependencies
pip install -r requirements.txt

# Run basic tests (no P6 required)
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=src --cov-report=html
```

---

## Test Categories

The project includes **3 types of tests**:

| Type | Description | P6 Required | Command |
|------|-------------|-------------|---------|
| **Unit Tests** | Test individual DAOs and utilities | ❌ No | `pytest tests/test_*_dao.py -v` |
| **Integration Tests** | Test database connections | ❌ No | `pytest tests/ -m integration -v` |
| **E2E Tests** | Full automation with live P6 | ✅ Yes | `python -m tests.test_automation_e2e --with-p6` |

---

## Prerequisites

### 1. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```env
# Required for SQLite testing
P6_DB_TYPE=standalone

# Required for GUI automation tests
P6_EXECUTABLE_PATH=C:\Program Files\Oracle\Primavera P6\P6 Professional\PM.exe
PDF_PRINTER_NAME=Microsoft Print to PDF
PDF_OUTPUT_DIR=reports/pdf
SAFE_MODE=true

# Optional: AI integration testing
LLM_PROVIDER=anthropic
LLM_API_KEY=your_api_key_here
```

### 3. SQLite Database (Optional)

For DAO tests, ensure a P6 SQLite database file exists (e.g., `S32DB001.db`).

---

## Running Tests

### Basic Tests (No P6 Required)

These tests verify core functionality without needing P6 running:

```powershell
# Run all basic tests
pytest tests/ -v

# Run specific test files
pytest tests/test_activity_dao.py -v
pytest tests/test_project_dao.py -v
pytest tests/test_schedule_analyzer.py -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=html
open htmlcov/index.html
```

### DAO Tests (SQLite)

Test data access objects against the SQLite database:

```powershell
pytest tests/test_activity_dao.py -v
pytest tests/test_project_dao.py -v
pytest tests/test_wbs_dao.py -v
pytest tests/test_relationship_dao.py -v
pytest tests/test_sqlite_manager.py -v
```

### Analyzer Tests

Test schedule analysis functionality:

```powershell
pytest tests/test_schedule_analyzer.py -v
pytest tests/test_critical_path_analyzer.py -v
pytest tests/test_progress_tracker.py -v
```

### Integration Tests (Marked)

Run only tests marked as integration:

```powershell
pytest tests/ -m integration -v
```

---

## E2E Tests (Requires P6 Running)

The End-to-End test suite validates full automation against a live P6 instance.

### Prerequisites for E2E Tests

1. **P6 Professional must be open and running**
2. **User must be logged in to P6**
3. **At least one project must exist/be open**

### Running E2E Tests

```powershell
# Basic E2E (no P6 connection required for imports/exceptions)
python -m tests.test_automation_e2e

# Full E2E (P6 MUST be running)
python -m tests.test_automation_e2e --with-p6

# Verbose output
python -m tests.test_automation_e2e --with-p6 -v
```

### E2E Test Coverage

| Test Category | What It Tests |
|---------------|---------------|
| **Imports** | All automation modules can be imported |
| **Exceptions** | Custom exception hierarchy |
| **Connection** | P6 process detection, `is_p6_running()` |
| **Automation Base** | Context manager, window connection |
| **Navigator** | Window title, status bar reading |
| **Projects** | Get open projects, current project |
| **Layouts** | Current layout detection |
| **Batch** | BatchResult and BatchSummary classes |
| **Agent** | P6AgentInterface, tool definitions |

---

## Test File Reference

| File | Description |
|------|-------------|
| `tests/conftest.py` | Shared pytest fixtures |
| `tests/test_activity_dao.py` | Activity data access tests |
| `tests/test_project_dao.py` | Project data access tests |
| `tests/test_wbs_dao.py` | WBS data access tests |
| `tests/test_relationship_dao.py` | Relationship data access tests |
| `tests/test_sqlite_manager.py` | SQLite connection tests |
| `tests/test_schedule_analyzer.py` | Schedule analysis tests |
| `tests/test_critical_path_analyzer.py` | Critical path calculation tests |
| `tests/test_progress_tracker.py` | Progress tracking tests |
| `tests/test_bulk_writer.py` | Bulk write operation tests |
| `tests/test_automation_e2e.py` | Full E2E GUI automation tests |

---

## Writing New Tests

### Test Fixtures

Common fixtures are defined in `tests/conftest.py`:

```python
import pytest

@pytest.fixture
def sample_project():
    """Create a sample project for testing."""
    return {"id": "TEST001", "name": "Test Project"}
```

### Example Test

```python
import pytest
from src.dao import ActivityDAO

class TestActivityDAO:
    """Tests for ActivityDAO."""
    
    def test_get_activities(self, db_connection):
        """Test fetching activities."""
        dao = ActivityDAO(db_connection)
        activities = dao.get_all()
        assert isinstance(activities, list)
    
    @pytest.mark.integration
    def test_activity_update(self, db_connection):
        """Integration test for activity updates."""
        # This requires live database
        pass
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: src` | Run tests from project root: `cd P6PlanningIntegration` |
| `P6NotFoundError` | Ensure P6 Professional is running |
| SQLite database not found | Check `P6_DB_TYPE=standalone` and database file exists |
| GUI automation fails | Run terminal as Administrator |

### Debug Mode

```powershell
# Run with more output
pytest tests/ -v -s

# Run a single test with full output
pytest tests/test_activity_dao.py::TestActivityDAO::test_get_activities -v -s

# Show local variables on failure
pytest tests/ --tb=long
```

---

## Continuous Integration

### GitHub Actions Workflow

The project includes CI configuration at `.github/workflows/`:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --ignore=tests/test_automation_e2e.py
```

> **Note:** E2E tests are excluded from CI as they require a live P6 installation.

---

## Coverage Goals

| Component | Target Coverage |
|-----------|-----------------|
| `src/dao/` | 80% |
| `src/analyzers/` | 75% |
| `src/automation/` | 60% (requires P6) |
| `src/utils/` | 85% |

Generate coverage report:

```powershell
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
```

---

## Safe Mode Testing

The project includes a **Safe Mode** feature to prevent accidental modifications:

```python
# Safe mode ON (default) - read-only operations
scheduler = P6ScheduleManager(window, safe_mode=True)

# Safe mode OFF - allows write operations
scheduler = P6ScheduleManager(window, safe_mode=False)
```

> ⚠️ **Warning:** Always use `safe_mode=True` when testing against production data!

---

## Manual Testing Checklist

For GUI automation features, use this manual checklist:

- [ ] **Connection**: Run `python -c "from src.automation import is_p6_running; print(is_p6_running())"`
- [ ] **Window Detection**: P6 window title is correctly detected
- [ ] **Project Navigation**: Can open/close projects via automation
- [ ] **Layout Apply**: Can apply different layouts
- [ ] **Print to PDF**: PDF generation produces valid files in `reports/pdf/`
- [ ] **Export XER**: XER export creates valid files
- [ ] **Scheduling (F9)**: Schedule calculation executes without errors
- [ ] **Agent Interface**: Tool definitions are correctly generated

---

## Questions?

If you encounter issues not covered here, check:

1. `PHASE_*_SUMMARY.md` files for implementation details
2. `AGENTS.md` for AI agent configuration
3. GitHub Issues for known problems
