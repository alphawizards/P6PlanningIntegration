# Coding Conventions

**Analysis Date:** 2026-02-07

## Naming Patterns

**Files:**
- Snake case with descriptive names: `activity_dao.py`, `schedule_analyzer.py`, `p6_automation.py`
- Module files use underscores: `sqlite_manager.py`, `llm_client.py`
- Specific file patterns: `*_dao.py` for data access objects, `*_analyzer.py` for analyzers, `*_manager.py` for managers

**Functions:**
- Snake case: `get_activities_for_project()`, `run_health_check()`, `_check_open_ends()`
- Private functions prefixed with single underscore: `_load_project_context()`, `_execute_tool()`
- Helper functions at module level documented in "HELPER FUNCTIONS" section with divider comments

**Variables:**
- Snake case for local/instance variables: `project_id`, `activity_dao`, `connection_timestamp`
- Constants in UPPER_SNAKE_CASE: `P6_DB_PATH`, `SAFE_MODE`, `HIGH_DURATION_DAYS`
- Private instance variables prefixed with underscore: `self._schema_valid`, `self._connection_timestamp`

**Types:**
- PascalCase for classes: `P6Agent`, `SQLiteManager`, `ScheduleAnalyzer`
- Enum classes: `class P6View(Enum):`, `class ActionType(Enum):`
- Exception classes inherit from base exceptions: `class P6AutomationError(Exception):`

**Imports:**
- Standard library imports first
- Third-party imports second
- Local imports last with full package paths (e.g., `from src.ai.tools import P6Tools`)
- Grouped within each category with blank lines between groups
- Example pattern from `src/ai/agent.py`:
  ```python
  import json
  from typing import Dict, List, Optional, Any

  from src.ai.tools import P6Tools
  from src.ai.prompts import SYSTEM_PROMPT
  from src.ai.llm_client import LLMClient, is_ai_enabled
  from src.utils import logger
  ```

## Code Style

**Formatting:**
- Line length limit: 100 characters (see `.pylintrc` max-line-length=100)
- Indentation: 4 spaces (see `.pylintrc` indent-string='    ')
- No specific formatter configured (no .prettierrc or black config detected)

**Linting:**
- Pylint configured via `.pylintrc`
- Disabled checks:
  - C0114: missing-module-docstring
  - C0115: missing-class-docstring
  - C0116: missing-function-docstring
  - R0903: too-few-public-methods
  - R0913: too-many-arguments
  - W0511: fixme (TODO/FIXME comments allowed)

## Error Handling

**Patterns:**
- Custom exception hierarchy under `src/automation/exceptions.py`
- Base exception: `P6AutomationError(Exception)`
- Specific exceptions:
  - `P6NotFoundError` - P6 process not found
  - `P6ConnectionError` - Connection failures
  - `P6TimeoutError` - Operation timeouts
  - `P6SafeModeError` - Safe mode blocking operations
  - `P6WindowNotFoundError` - Window not found
  - `P6LoginError` - Login failures
  - `P6ScheduleError` - Schedule operation failures

**Try-catch blocks:**
- Catch specific exceptions before broad `Exception`
- Log error context with logger before raising
- Example from `src/ai/agent.py`:
  ```python
  try:
      # operation
  except Exception as e:
      logger.error(f"Error in chat: {e}", exc_info=True)
      return f"❌ Error: {str(e)}"
  ```

**Validation:**
- Configuration validated at module import time with fail-fast in `src/config/settings.py`
- Required environment variables checked immediately: `_get_required_env()`
- ValueError raised with descriptive message including configuration guidance

## Logging

**Framework:** Python's standard `logging` module via custom `src/utils/logger.py`

**Setup:**
- Configured in `src/utils/logger.py` with centralized setup function: `setup_logger()`
- Default logger instance exported as `logger` from `src/utils/logger.py`
- Imported in all modules as: `from src.utils import logger`

**Patterns:**
- Log level usage: DEBUG (detailed flow), INFO (key milestones), WARNING (recoverables), ERROR (critical issues)
- Info logs for major state changes: `logger.info(f"SQLiteManager initialized with db_path: {self.db_path}")`
- Warning logs for degraded but functional state: `logger.warning("Already connected to SQLite database")`
- Error logs with context and exception info: `logger.error(f"Error loading project context: {e}")`
- Debug logs for diagnostic info: `logger.debug(f"Tool result: {tool_result[:200]}...")`

**Formatting:**
- Consistent format string pattern: `"Message with {variable} interpolation"`
- f-strings with context: `f"Error in {function_name}: {error_message}"`
- Exception logging with `exc_info=True`: `logger.error(f"Error: {e}", exc_info=True)`

**Sensitive data:**
- Utility function `sanitize_message()` in `src/utils/logger.py` to redact sensitive data
- Function `log_exception()` logs exceptions without full traceback to avoid leaking sensitive data

## Comments

**When to Comment:**
- Comments disabled for docstring requirements (pylint rules C0114-C0116 disabled)
- Used for clarifying complex logic and verification points
- Special markers for cross-file coordination: `# VERIFICATION POINT n:` (see `src/ai/agent.py`)
- Configuration explanations: `# Convert Hours -> Days` in DAO queries

**JSDoc/TSDoc/Docstrings:**
- Not required by linting rules but used for public methods and classes
- Follows Google-style docstrings in class/function docstrings:
  ```python
  def get_activities_for_project(
      self,
      project_object_id: int,
      filter_expr: Optional[str] = None
  ) -> pd.DataFrame:
      """
      Fetch all activities for a specific project.

      Args:
          project_object_id: Project ObjectId (proj_id)
          filter_expr: Optional additional SQL WHERE clause

      Returns:
          pd.DataFrame: DataFrame with ACTIVITY_FIELDS columns
      """
  ```

**Comment Types:**
- Section dividers: 80-character lines with description
  ```python
  # ============================================================================
  # HELPER FUNCTIONS
  # ============================================================================
  ```
- Inline explanations for non-obvious logic
- Safety notes: `# SAFETY: Opens database in READ-ONLY mode`

## Function Design

**Size:** No strict limit enforced, but typical public methods 20-60 lines with helper methods for complex logic

**Parameters:**
- Use type hints: `def run_health_check(self, project_id: int) -> Dict[str, Any]:`
- Optional parameters with defaults: `filter_expr: Optional[str] = None`
- Keyword-only arguments for configuration methods
- Named arguments encouraged when calling functions with multiple parameters

**Return Values:**
- Explicit return types in signatures: `-> pd.DataFrame`, `-> bool`, `-> str`
- Consistent return patterns within a class (DAOs return DataFrames, Managers return booleans for connection state)
- Multiple values returned as dictionaries with descriptive keys: `return {'success': True, 'data': result}`

## Module Design

**Exports:**
- No `__all__` lists detected; modules export all public (non-underscore) names
- Modules import specific classes/functions needed: `from src.ai.tools import P6Tools`
- Private imports from sibling modules use relative paths: `from .exceptions import P6AutomationError`

**Barrel Files:**
- Package `__init__.py` files exist but minimal (mostly empty for namespace packages)
- Example: `src/__init__.py` is empty, `src/dao/__init__.py` is empty
- Consumers import directly from implementation modules

**Organization Patterns:**
- DAO pattern: Base abstract classes in `src/dao/` with SQLite implementation in `src/dao/sqlite/`
- Manager classes handle lifecycle: connection, session, resource management
- Analyzer classes perform domain logic with injected dependencies
- Utility modules provide cross-cutting concerns: logging, converters, file operations

**Dependency Injection:**
- Constructor injection for dependencies: `def __init__(self, manager: SQLiteManager):`
- Required dependencies validated in constructor: `if manager is None or not manager.is_connected(): raise ValueError`
- Fixtures in pytest provide instances for tests

---

*Convention analysis: 2026-02-07*
