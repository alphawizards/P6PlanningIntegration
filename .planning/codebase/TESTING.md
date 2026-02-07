# Testing Patterns

**Analysis Date:** 2026-02-07

## Test Framework

**Runner:**
- pytest 7.0.0+
- Config: `pytest.ini` in project root
- Test discovery: `tests/` directory

**Assertion Library:**
- pytest built-in assertions (no external assertion library)

**Run Commands:**
```bash
pytest                    # Run all tests
pytest -v                 # Verbose output with test names
pytest tests/             # Run tests in tests directory
pytest -m integration     # Run only integration tests (marked with @pytest.mark.integration)
pytest --cov             # Run with coverage (pytest-cov)
pytest -ra -q            # Quiet mode with summary (configured in pytest.ini)
```

**Dependencies:**
- pytest >= 7.0.0
- pytest-cov >= 4.0.0 (for coverage reporting)
- unittest.mock (standard library mocking)

## Test File Organization

**Location:**
- Co-located with source code: `tests/` directory mirrors `src/` structure
- Root test files for integration tests: `test_dao_integration.py`, `test_sqlite.py`

**Naming:**
- Pattern: `test_*.py` for pytest discovery
- Class pattern: `TestClassName` for test classes
- Function pattern: `test_description()` for test methods

**Structure:**
```
tests/
├── conftest.py                      # Shared fixtures
├── test_activity_dao.py             # DAO layer tests
├── test_project_dao.py              # DAO layer tests
├── test_relationship_dao.py         # DAO layer tests
├── test_sqlite_manager.py           # Manager tests
├── test_bulk_writer.py              # Writer tests
├── test_schedule_analyzer.py        # Analyzer tests
├── test_critical_path_analyzer.py   # Analyzer tests
├── test_progress_tracker.py         # Analyzer tests
├── test_automation_e2e.py           # E2E automation tests
└── __init__.py
```

## Test Structure

**Suite Organization:**

Test classes group related tests with descriptive names:
```python
@pytest.mark.integration
class TestActivityDAOBasic:
    """Basic tests for ActivityDAO."""

    def test_get_activities_for_project_returns_dataframe(self, activity_dao, project_dao):
        """Test that get_activities_for_project returns a DataFrame."""
        # Arrange
        projects = project_dao.get_active_projects()
        if len(projects) > 0:
            # Act
            project_id = int(projects.iloc[0]['ObjectId'])
            result = activity_dao.get_activities_for_project(project_id)

            # Assert
            assert isinstance(result, pd.DataFrame)
```

**Patterns:**
- Arrange-Act-Assert (AAA) pattern used implicitly
- Setup via fixtures rather than setUp methods
- Conditional assertions for data-dependent tests (checking if data exists before asserting)

**Test Markers:**
- Integration tests marked with `@pytest.mark.integration` (defined in `pytest.ini`)
- Marks tests that require live database connection
- Run subset with: `pytest -m integration`

## Mocking

**Framework:** Python's `unittest.mock` module (standard library)

**Patterns:**

Mock DAO managers for unit tests (from `tests/test_schedule_analyzer.py`):
```python
@pytest.fixture
def mock_dao_manager():
    """Create a mock SQLiteManager with mock DAOs."""
    manager = Mock()
    manager.get_activity_dao.return_value = Mock()
    manager.get_relationship_dao.return_value = Mock()
    return manager

@pytest.fixture
def analyzer(mock_dao_manager):
    """Create analyzer instance with mock manager."""
    return ScheduleAnalyzer(mock_dao_manager)
```

Mock return values:
```python
analyzer.activity_dao.get_activities_for_project.return_value = activities
analyzer.relationship_dao.get_relationships.return_value = relationships
```

Patch configuration values (from `tests/test_bulk_writer.py`):
```python
# Patch SAFE_MODE to False for testing
self.patcher = patch('src.dao.sqlite.bulk_writer.SAFE_MODE', False)
self.patcher.start()
```

**What to Mock:**
- External service dependencies (SQLiteManager, file I/O)
- Configuration flags that affect behavior (SAFE_MODE)
- System dependencies (P6 GUI automation via pywinauto)

**What NOT to Mock:**
- Core logic in classes under test
- DAO data transformations (unless testing integration behavior)
- Exception raising - let actual exceptions propagate in tests

## Fixtures and Factories

**Test Data:**

Helper functions create test DataFrames with required columns (from `tests/test_schedule_analyzer.py`):
```python
def create_mock_activities(data):
    """Helper to create activities DataFrame."""
    columns = [
        'ObjectId', 'Id', 'Name', 'Status', 'PlannedDuration',
        'StartDate', 'FinishDate', 'ActualStartDate', 'ActualFinishDate',
        'Type', 'ConstraintType', 'TotalFloat', 'ProjectObjectId'
    ]
    df = pd.DataFrame(data)
    for col in columns:
        if col not in df.columns:
            df[col] = None
    return df

def create_mock_relationships(data):
    """Helper to create relationships DataFrame."""
    columns = ['ObjectId', 'PredecessorObjectId', 'SuccessorObjectId', 'Type', 'Lag']
    df = pd.DataFrame(data)
    for col in columns:
        if col not in df.columns:
            df[col] = None
    return df
```

**Session-scoped Fixtures (from `tests/conftest.py`):**

Live database fixtures for integration tests:
```python
@pytest.fixture(scope="session")
def sqlite_manager():
    """
    Session-scoped fixture providing a connected SQLiteManager.

    Uses the live P6 database in read-only (immutable) mode.
    Connection is shared across all tests for efficiency.
    """
    manager = SQLiteManager()
    manager.connect()
    yield manager
    manager.disconnect()

@pytest.fixture
def project_dao(sqlite_manager):
    """Fixture providing ProjectDAO instance."""
    return sqlite_manager.get_project_dao()

@pytest.fixture
def activity_dao(sqlite_manager):
    """Fixture providing ActivityDAO instance."""
    return sqlite_manager.get_activity_dao()

@pytest.fixture
def relationship_dao(sqlite_manager):
    """Fixture providing RelationshipDAO instance."""
    return sqlite_manager.get_relationship_dao()
```

**Location:**
- Shared fixtures in `tests/conftest.py` - imported automatically by pytest
- Test-specific fixtures in test files near usage
- Factory functions defined at module level in test files

## Coverage

**Requirements:** No minimum coverage enforced (no coverage configuration in pytest.ini)

**View Coverage:**
```bash
pytest --cov=src --cov-report=html    # Generate HTML coverage report
pytest --cov=src --cov-report=term    # Terminal coverage report
```

**Current Coverage Areas:**
- DAO layer: Moderate coverage via `test_activity_dao.py`, `test_project_dao.py`
- SQLite manager: Basic coverage via `test_sqlite_manager.py`
- Analyzers: Moderate coverage via `test_schedule_analyzer.py`, `test_critical_path_analyzer.py`
- Bulk operations: Coverage via `test_bulk_writer.py`
- Automation: E2E coverage via `test_automation_e2e.py` (integration test)

## Test Types

**Unit Tests:**
- Scope: Individual methods/functions with mocked dependencies
- Approach: Mock external dependencies, test single responsibility
- Examples: `test_schedule_analyzer.py` test suite uses mocked DAOs
- Location: Typically in test files matching source module names

**Integration Tests:**
- Scope: Multiple components working together with live database
- Approach: Use real SQLiteManager, real database connection
- Marked with: `@pytest.mark.integration` decorator
- Examples:
  - `test_activity_dao.py::TestActivityDAOBasic` - uses real database
  - `test_automation_e2e.py` - end-to-end automation flows
- Setup: Session-scoped fixture provides real connected SQLiteManager

**E2E Tests:**
- Scope: Full automation flows including GUI interaction
- Framework: Not explicitly configured; would use pywinauto
- Location: `tests/test_automation_e2e.py`
- Status: Marked as integration tests

## Common Patterns

**Async Testing:**
Not applicable - no async/await in codebase

**Error Testing:**

Test expected exceptions using pytest.raises (pattern inference from exception handling):
```python
# Expected pattern for error testing
def test_invalid_project_raises_error(self):
    """Test that invalid project ID raises ValueError."""
    with pytest.raises(ValueError, match="Invalid project"):
        analyzer.run_health_check(invalid_id)
```

**Data-Dependent Tests:**

Tests that conditionally assert based on available data (from `tests/test_activity_dao.py`):
```python
def test_duration_converted_to_days(self, activity_dao, project_dao):
    """Test that PlannedDuration is in days (divided by 8)."""
    projects = project_dao.get_active_projects()
    if len(projects) > 0:  # Only test if data available
        project_id = int(projects.iloc[0]['ObjectId'])
        activities = activity_dao.get_activities_for_project(project_id)

        if len(activities) > 0:  # Only assert if activities exist
            durations = activities['PlannedDuration'].dropna()
            if len(durations) > 0:
                assert durations.max() < 1000
```

**Test Setup and Teardown:**

unittest.TestCase pattern for file-based tests (from `tests/test_bulk_writer.py`):
```python
class TestSQLiteBulkWriter(unittest.TestCase):

    def setUp(self):
        """Create temporary database for test."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.db_fd)
        # Initialize schema...
        self.patcher = patch('src.dao.sqlite.bulk_writer.SAFE_MODE', False)
        self.patcher.start()
        self.writer = SQLiteBulkWriter(self.db_path)

    def tearDown(self):
        """Clean up after test."""
        self.patcher.stop()
        # Cleanup temporary files
```

**Test Isolation:**

- Each test method is independent
- Fixtures provide fresh instances for each test
- Session-scoped fixtures used only for expensive operations (database connection)
- Temporary files created and cleaned up in setUp/tearDown

---

*Testing analysis: 2026-02-07*
