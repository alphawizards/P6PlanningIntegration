# Architecture Research: Promptable P6 Automation System

## Executive Summary

This document researches the optimal architecture for a Claude Code-operated P6 Professional automation system. The system translates natural language commands into GUI operations while maintaining state awareness, error recovery, and data integrity.

---

## 1. High-Level Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Claude Code                          │
│  (User provides natural language commands)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Natural Language
                     │
┌────────────────────▼────────────────────────────────────────┐
│                   Claude Skills Layer                        │
│  - /open-project    - /edit-activity   - /batch-export      │
│  - /apply-layout    - /run-schedule    - /print-pdf         │
│  - /find-activity   - /export-xer      - /analyze-schedule  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Structured Commands
                     │
┌────────────────────▼────────────────────────────────────────┐
│              Command Translation Layer                       │
│  - Parse parameters    - Validate inputs                    │
│  - Map to operations   - Check preconditions                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Operation Calls
                     │
┌────────────────────▼────────────────────────────────────────┐
│               P6 State Manager                               │
│  - Track open project  - Monitor dialogs                    │
│  - Track active view   - Detect errors                      │
│  - Track P6 version    - Recovery coordination              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Stateful Operations
                     │
┌────────────────────▼────────────────────────────────────────┐
│            GUI Automation Managers                           │
│  ┌──────────────┬──────────────┬──────────────┐            │
│  │   Projects   │  Activities  │  Scheduling  │            │
│  │   Layouts    │   Printing   │  Exporting   │            │
│  │   Batch      │  Navigation  │     Base     │            │
│  └──────────────┴──────────────┴──────────────┘            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ pywinauto + OCR
                     │
┌────────────────────▼────────────────────────────────────────┐
│              P6 Professional GUI                             │
│  (Java Swing/AWT Application)                                │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Claude Code Skills Architecture

### Skill Definition Pattern

Each P6 operation is wrapped as a Claude Code skill with clear interface:

```python
# File: .claude/skills/open-project.py

from src.automation import P6PrintAutomation, P6ProjectManager
from src.automation.exceptions import ProjectNotFoundError
import json

def run(project_identifier: str, timeout: int = 60):
    """
    Open a P6 project by ID or name.

    Args:
        project_identifier: Project ID or name
        timeout: Max seconds to wait for project to load

    Returns:
        JSON with project details or error
    """
    try:
        with P6PrintAutomation() as p6:
            manager = P6ProjectManager(p6.main_window)

            # Open project
            result = manager.open_project(
                project_identifier,
                timeout=timeout
            )

            return json.dumps({
                "success": True,
                "project_id": result.project_id,
                "project_name": result.project_name,
                "message": f"Opened project: {result.project_name}"
            })

    except ProjectNotFoundError as e:
        return json.dumps({
            "success": False,
            "error": "ProjectNotFound",
            "message": str(e),
            "suggestion": "Use list-projects skill to see available projects"
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": type(e).__name__,
            "message": str(e)
        })
```

### Skill Metadata

```toml
# File: .claude/skills/open-project.toml

name = "open-project"
description = "Open a Primavera P6 project by ID or name"
version = "1.0.0"

[[parameters]]
name = "project_identifier"
type = "string"
description = "Project ID (e.g., '19282') or project name"
required = true

[[parameters]]
name = "timeout"
type = "integer"
description = "Maximum seconds to wait for project to open"
required = false
default = 60

[examples]
basic = "open-project 19282"
by_name = "open-project 'Highway Expansion'"
with_timeout = "open-project 19282 --timeout=120"
```

---

## 3. Command Translation Layer

### Natural Language → Structured Command

Claude Code's built-in ReAct pattern handles this, but we provide strong typing:

```python
# File: src/automation/commands.py

from dataclasses import dataclass
from typing import Optional, List, Union
from datetime import datetime
from enum import Enum

class CommandType(Enum):
    OPEN_PROJECT = "open_project"
    CLOSE_PROJECT = "close_project"
    APPLY_LAYOUT = "apply_layout"
    FIND_ACTIVITY = "find_activity"
    EDIT_ACTIVITY_DATE = "edit_activity_date"
    ADD_RELATIONSHIP = "add_relationship"
    RUN_SCHEDULE = "run_schedule"
    EXPORT_XER = "export_xer"
    PRINT_PDF = "print_pdf"
    BATCH_EXPORT = "batch_export"

@dataclass
class OpenProjectCommand:
    """Open project command"""
    project_identifier: str
    timeout: int = 60

@dataclass
class EditActivityDateCommand:
    """Edit activity date command"""
    activity_id: str
    field: str  # "start_date" | "finish_date" | "duration"
    value: Union[datetime, int]
    respect_constraints: bool = True

@dataclass
class AddRelationshipCommand:
    """Add activity relationship command"""
    predecessor_id: str
    successor_id: str
    relationship_type: str  # "FS" | "SS" | "FF" | "SF"
    lag_days: int = 0

class CommandValidator:
    """Validate commands before execution"""

    def validate_open_project(self, cmd: OpenProjectCommand) -> List[str]:
        """Return list of validation errors"""
        errors = []

        if not cmd.project_identifier:
            errors.append("project_identifier cannot be empty")

        if cmd.timeout < 5:
            errors.append("timeout must be at least 5 seconds")

        return errors

    def validate_edit_date(self, cmd: EditActivityDateCommand) -> List[str]:
        errors = []

        if not cmd.activity_id:
            errors.append("activity_id cannot be empty")

        if cmd.field not in ["start_date", "finish_date", "duration"]:
            errors.append(f"Invalid field: {cmd.field}")

        if cmd.field == "duration" and cmd.value < 0:
            errors.append("duration cannot be negative")

        return errors
```

### Command Execution Pattern

```python
# File: src/automation/executor.py

from typing import Union
import logging
from .commands import *
from .state import P6StateManager

logger = logging.getLogger(__name__)

class CommandExecutor:
    """Execute validated commands against P6"""

    def __init__(self, state_manager: P6StateManager):
        self.state = state_manager
        self.validator = CommandValidator()

    def execute(self, command: Union[OpenProjectCommand, EditActivityDateCommand, ...]):
        """Execute command with pre/post checks"""

        # Validate
        errors = self._validate(command)
        if errors:
            raise ValueError(f"Validation failed: {errors}")

        # Check preconditions
        self._check_preconditions(command)

        # Execute
        try:
            result = self._execute_impl(command)
            self.state.record_success(command)
            return result
        except Exception as e:
            self.state.record_error(command, e)
            raise

    def _check_preconditions(self, command):
        """Ensure P6 state is valid for command"""

        if isinstance(command, EditActivityDateCommand):
            # Must have project open
            if not self.state.current_project:
                raise RuntimeError("No project open")

            # Safe mode check
            if self.state.safe_mode:
                raise RuntimeError("Write operations disabled in safe mode")

        elif isinstance(command, OpenProjectCommand):
            # Must not have uncommitted changes
            if self.state.has_unsaved_changes:
                raise RuntimeError("Save or discard changes before opening new project")
```

---

## 4. P6 State Management

### State Tracker

```python
# File: src/automation/state.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
import logging

@dataclass
class P6State:
    """Current state of P6 application"""

    # Application state
    p6_running: bool = False
    p6_version: Optional[str] = None
    main_window_hwnd: Optional[int] = None

    # Project state
    current_project: Optional[str] = None  # Project ID
    current_project_name: Optional[str] = None
    project_opened_at: Optional[datetime] = None
    has_unsaved_changes: bool = False

    # View state
    current_layout: Optional[str] = None
    current_view: str = "Activities"  # Activities | WBS | Resources
    filters_applied: List[str] = field(default_factory=list)

    # Operation state
    last_schedule_run: Optional[datetime] = None
    scheduling_in_progress: bool = False
    modal_dialog_open: bool = False
    current_dialog_title: Optional[str] = None

    # Configuration
    safe_mode: bool = True
    auto_schedule: bool = False

    # History
    command_history: List[str] = field(default_factory=list)
    error_count: int = 0
    last_error: Optional[Exception] = None

class P6StateManager:
    """Manage and track P6 application state"""

    def __init__(self, automation):
        self.automation = automation
        self.state = P6State()
        self.logger = logging.getLogger(__name__)

    def refresh(self):
        """Update state by inspecting P6 window"""

        # Check if P6 running
        try:
            self.automation.main_window.is_visible()
            self.state.p6_running = True
        except:
            self.state.p6_running = False
            return

        # Extract project from title bar
        # Format: "Primavera P6 - [Project: 19282 - Highway Expansion]"
        title = self.automation.main_window.texts()[0]
        self.state.current_project = self._extract_project_id(title)
        self.state.current_project_name = self._extract_project_name(title)

        # Check for unsaved changes (asterisk in title)
        self.state.has_unsaved_changes = "*" in title

        # Detect modal dialogs
        self.state.modal_dialog_open = self._check_for_dialogs()

    def _extract_project_id(self, title: str) -> Optional[str]:
        """Parse project ID from title bar"""
        import re
        match = re.search(r'Project:\s*(\w+)', title)
        return match.group(1) if match else None

    def _check_for_dialogs(self) -> bool:
        """Detect if modal dialog is open"""
        try:
            # Check for common dialog classes
            dialogs = self.automation.app.windows(
                class_name="SunAwtDialog"  # Java dialogs
            )
            return len(dialogs) > 0
        except:
            return False

    def record_success(self, command):
        """Log successful command"""
        self.state.command_history.append(
            f"{datetime.now()}: {command.__class__.__name__}"
        )

    def record_error(self, command, error: Exception):
        """Log failed command"""
        self.state.error_count += 1
        self.state.last_error = error
        self.logger.error(f"Command failed: {command} - {error}")

    def wait_for_idle(self, timeout: int = 30):
        """Wait for P6 to finish background operations"""

        start = datetime.now()
        while (datetime.now() - start).seconds < timeout:
            self.refresh()

            # Check for blocking conditions
            if self.state.scheduling_in_progress:
                time.sleep(1)
                continue

            if self.state.modal_dialog_open:
                # Don't wait - caller should handle
                raise RuntimeError(f"Modal dialog detected: {self.state.current_dialog_title}")

            # Idle
            return

        raise TimeoutError("P6 did not become idle")
```

---

## 5. Error Recovery Patterns

### Recovery Strategies

```python
# File: src/automation/recovery.py

from typing import Callable, Any
import logging
from .exceptions import *

class RecoveryStrategy:
    """Base recovery strategy"""

    def can_recover(self, error: Exception, context: dict) -> bool:
        """Check if this strategy applies"""
        raise NotImplementedError

    def recover(self, error: Exception, context: dict) -> Any:
        """Attempt recovery"""
        raise NotImplementedError

class DialogRecovery(RecoveryStrategy):
    """Handle unexpected modal dialogs"""

    def can_recover(self, error: Exception, context: dict) -> bool:
        return isinstance(error, UnexpectedDialogError)

    def recover(self, error: Exception, context: dict):
        """Try to close dialog and retry"""
        dialog = error.dialog

        # Check for common patterns
        if "Error" in dialog.texts()[0]:
            # Error dialog - click OK and propagate
            dialog.child_window(title="OK").click()
            raise RuntimeError(f"P6 error: {dialog.texts()}")

        elif "Warning" in dialog.texts()[0]:
            # Warning - click OK and continue
            dialog.child_window(title="OK").click()
            return "recovered_from_warning"

        elif "Confirm" in dialog.texts()[0]:
            # Confirmation - depends on safe mode
            if context.get("safe_mode"):
                dialog.child_window(title="Cancel").click()
                raise SafeModeError("Confirmation required but safe mode enabled")
            else:
                dialog.child_window(title="OK").click()
                return "confirmed"

class SchedulingTimeoutRecovery(RecoveryStrategy):
    """Handle scheduling timeouts"""

    def can_recover(self, error: Exception, context: dict) -> bool:
        return isinstance(error, SchedulingTimeoutError)

    def recover(self, error: Exception, context: dict):
        """Check if scheduling actually completed"""

        # Look for "Scheduling Complete" dialog
        try:
            complete_dialog = context["app"].window(
                title_re=".*Scheduling.*Complete.*"
            )
            complete_dialog.close()
            return "scheduling_completed"
        except:
            # Actually timed out
            raise

class ErrorRecoveryManager:
    """Coordinate recovery strategies"""

    def __init__(self):
        self.strategies = [
            DialogRecovery(),
            SchedulingTimeoutRecovery(),
            # Add more strategies
        ]
        self.logger = logging.getLogger(__name__)

    def attempt_recovery(self, error: Exception, context: dict, max_attempts: int = 3):
        """Try recovery strategies in order"""

        for attempt in range(max_attempts):
            for strategy in self.strategies:
                if strategy.can_recover(error, context):
                    try:
                        result = strategy.recover(error, context)
                        self.logger.info(f"Recovered using {strategy.__class__.__name__}: {result}")
                        return result
                    except Exception as e:
                        self.logger.warning(f"Recovery failed: {e}")
                        continue

            # Wait before retry
            time.sleep(2 ** attempt)

        # No recovery possible
        raise RecoveryFailedError(f"Could not recover from {error}") from error
```

### Retry Wrapper

```python
# File: src/automation/retry.py

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from .recovery import ErrorRecoveryManager

def with_recovery(max_retries: int = 3):
    """Decorator that adds retry + recovery"""

    def decorator(func):
        recovery_manager = ErrorRecoveryManager()

        @retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(min=1, max=10),
            retry=retry_if_exception_type((
                ElementNotFoundError,
                TimeoutError,
                UnexpectedDialogError
            ))
        )
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Attempt recovery
                context = {
                    "function": func.__name__,
                    "args": args,
                    "kwargs": kwargs
                }
                recovery_manager.attempt_recovery(e, context)

                # Retry
                raise

        return wrapper
    return decorator
```

---

## 6. Component Boundaries

### Layered Architecture

```
┌─────────────────────────────────────────────────────────┐
│  SKILL LAYER (.claude/skills/*.py)                      │
│  - Claude Code interface                                │
│  - Parameter parsing                                    │
│  - JSON output formatting                               │
│  - High-level error messages                            │
└────────────┬────────────────────────────────────────────┘
             │ calls
┌────────────▼────────────────────────────────────────────┐
│  COMMAND LAYER (src/automation/commands.py)             │
│  - Strongly-typed command objects                       │
│  - Validation logic                                     │
│  - Precondition checks                                  │
│  - Business rules                                       │
└────────────┬────────────────────────────────────────────┘
             │ executes via
┌────────────▼────────────────────────────────────────────┐
│  ORCHESTRATION LAYER (src/automation/executor.py)       │
│  - Command execution flow                               │
│  - State management coordination                        │
│  - Error recovery orchestration                         │
│  - Transaction boundaries                               │
└────────────┬────────────────────────────────────────────┘
             │ delegates to
┌────────────▼────────────────────────────────────────────┐
│  MANAGER LAYER (src/automation/*.py)                    │
│  - P6ProjectManager: EPS, project operations            │
│  - P6LayoutManager: Layouts, views, filters             │
│  - P6ActivityManager: Activity CRUD                     │
│  - P6ScheduleManager: F9, leveling, baselines           │
│  - P6PrintManager: Print preview, PDF                   │
│  - P6ExportManager: XER, XML, Excel export              │
│  - P6BatchProcessor: Multi-operation coordination       │
└────────────┬────────────────────────────────────────────┘
             │ uses
┌────────────▼────────────────────────────────────────────┐
│  AUTOMATION LAYER (pywinauto + OCR)                     │
│  - Window/control finding                               │
│  - Click, type, read operations                         │
│  - Wait strategies                                      │
│  - Screen capture + OCR                                 │
└─────────────────────────────────────────────────────────┘
```

### Boundary Contracts

**Skill Layer → Command Layer:**
- Input: Natural language → Structured parameters
- Output: JSON results
- No direct GUI access
- Catches all exceptions

**Command Layer → Orchestration Layer:**
- Input: Typed command objects
- Output: Typed result objects
- Validation before execution
- No business logic

**Orchestration Layer → Manager Layer:**
- Input: High-level operations (e.g., "open project")
- Output: Operation results + state changes
- Coordinates multiple managers
- Handles transactions

**Manager Layer → Automation Layer:**
- Input: Specific GUI actions (e.g., "click button")
- Output: Success/failure
- Encapsulates P6 GUI knowledge
- Retry/wait logic

---

## 7. Data Flow Patterns

### Unidirectional Data Flow

```
User Command
    ↓
Claude Code (LLM reasoning)
    ↓
Skill Invocation
    ↓
Command Object Created
    ↓
Validation
    ↓
State Check (preconditions)
    ↓
Manager Execution
    ↓
GUI Automation
    ↓
P6 Application
    ↓
State Update
    ↓
Result Object
    ↓
JSON Response
    ↓
Claude Code (presents to user)
```

### State Mutation Rules

1. **Only managers mutate state** (via StateManager)
2. **Commands are immutable** (dataclasses with frozen=True)
3. **State updates are atomic** (all-or-nothing)
4. **State is read-only above manager layer**

### Event Flow

```python
# File: src/automation/events.py

from dataclasses import dataclass
from typing import Callable, List
from enum import Enum

class EventType(Enum):
    PROJECT_OPENED = "project_opened"
    PROJECT_CLOSED = "project_closed"
    LAYOUT_CHANGED = "layout_changed"
    SCHEDULE_STARTED = "schedule_started"
    SCHEDULE_COMPLETED = "schedule_completed"
    ERROR_OCCURRED = "error_occurred"

@dataclass
class P6Event:
    event_type: EventType
    timestamp: datetime
    data: dict

class EventBus:
    """Publish-subscribe for P6 events"""

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}

    def subscribe(self, event_type: EventType, handler: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def publish(self, event: P6Event):
        if event.event_type in self._subscribers:
            for handler in self._subscribers[event.event_type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Event handler failed: {e}")

# Usage in managers
event_bus = EventBus()

# Subscribe to events
event_bus.subscribe(EventType.PROJECT_OPENED, log_project_change)
event_bus.subscribe(EventType.ERROR_OCCURRED, send_alert)

# Publish events
event_bus.publish(P6Event(
    event_type=EventType.PROJECT_OPENED,
    timestamp=datetime.now(),
    data={"project_id": "19282", "project_name": "Highway"}
))
```

---

## 8. Transaction Management

### Safe Modification Pattern

```python
# File: src/automation/transactions.py

from contextlib import contextmanager
import logging

class TransactionManager:
    """Ensure atomic P6 operations"""

    def __init__(self, state_manager, export_manager):
        self.state = state_manager
        self.exporter = export_manager
        self.logger = logging.getLogger(__name__)

    @contextmanager
    def transaction(self, description: str, backup: bool = True):
        """
        Ensure all-or-nothing changes.

        Usage:
            with tx.transaction("Update activity dates", backup=True):
                manager.edit_date(...)
                manager.edit_duration(...)
        """

        backup_file = None
        initial_state = self.state.snapshot()

        try:
            # Create backup if requested
            if backup:
                backup_file = self._create_backup()
                self.logger.info(f"Created backup: {backup_file}")

            # Execute operations
            yield

            # Commit (schedule to recalc)
            if self.state.auto_schedule:
                self._run_schedule()

            self.logger.info(f"Transaction committed: {description}")

        except Exception as e:
            # Rollback
            self.logger.error(f"Transaction failed: {description} - {e}")

            if backup_file:
                self._restore_backup(backup_file)
                self.logger.info(f"Restored from backup: {backup_file}")
            else:
                self.logger.warning("No backup available, manual recovery needed")

            raise

    def _create_backup(self) -> str:
        """Export current project as XER"""
        import tempfile
        import os

        backup_dir = tempfile.gettempdir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_id = self.state.current_project
        backup_file = os.path.join(backup_dir, f"p6_backup_{project_id}_{timestamp}.xer")

        self.exporter.export_xer(backup_file)
        return backup_file
```

---

## 9. Monitoring & Observability

### Structured Logging

```python
# File: src/automation/logging_config.py

import structlog
import logging

def configure_logging():
    """Set up structured logging"""

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

# Usage
logger = structlog.get_logger()

logger.info(
    "project_opened",
    project_id="19282",
    project_name="Highway Expansion",
    duration_seconds=3.2
)

logger.error(
    "activity_edit_failed",
    activity_id="A1010",
    field="start_date",
    error="ConstraintConflict",
    recovery_attempted=True
)
```

### Metrics Collection

```python
# File: src/automation/metrics.py

from dataclasses import dataclass, field
from typing import Dict
import time

@dataclass
class OperationMetrics:
    """Track operation performance"""

    operation_name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    success: bool = False
    error: Optional[str] = None
    retry_count: int = 0

    @property
    def duration(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

class MetricsCollector:
    """Collect and report metrics"""

    def __init__(self):
        self.operations: List[OperationMetrics] = []

    @contextmanager
    def track(self, operation_name: str):
        """Track operation timing"""
        metric = OperationMetrics(operation_name=operation_name)
        self.operations.append(metric)

        try:
            yield metric
            metric.success = True
        except Exception as e:
            metric.error = str(e)
            raise
        finally:
            metric.end_time = time.time()

    def report(self) -> dict:
        """Generate metrics summary"""
        return {
            "total_operations": len(self.operations),
            "successful": sum(1 for op in self.operations if op.success),
            "failed": sum(1 for op in self.operations if not op.success),
            "avg_duration": sum(op.duration for op in self.operations) / len(self.operations),
            "by_operation": self._group_by_operation()
        }
```

---

## 10. Component Communication

### Manager Composition

```python
# File: src/automation/composition.py

class P6Orchestrator:
    """
    High-level coordinator that composes managers.
    Used by skills for complex operations.
    """

    def __init__(self, automation):
        self.automation = automation
        self.state = P6StateManager(automation)

        # Managers
        self.projects = P6ProjectManager(automation.main_window)
        self.layouts = P6LayoutManager(automation.main_window)
        self.activities = P6ActivityManager(automation.main_window)
        self.scheduling = P6ScheduleManager(automation.main_window)
        self.printing = P6PrintManager(automation.main_window)
        self.exporting = P6ExportManager(automation.main_window)

        # Cross-cutting concerns
        self.transactions = TransactionManager(self.state, self.exporting)
        self.recovery = ErrorRecoveryManager()
        self.metrics = MetricsCollector()

    def execute_workflow(self, workflow_name: str, **params):
        """Execute multi-step workflow"""

        if workflow_name == "monthly_report":
            return self._monthly_report_workflow(**params)
        elif workflow_name == "batch_update":
            return self._batch_update_workflow(**params)
        else:
            raise ValueError(f"Unknown workflow: {workflow_name}")

    def _monthly_report_workflow(self, project_ids: List[str], layout: str):
        """
        Complex workflow: open each project, apply layout, print PDF
        """
        results = []

        for project_id in project_ids:
            with self.metrics.track(f"report_{project_id}"):
                try:
                    # Open project
                    self.projects.open_project(project_id)
                    self.state.refresh()

                    # Apply layout
                    self.layouts.apply_layout(layout)

                    # Print PDF
                    pdf_path = f"reports/{project_id}_monthly.pdf"
                    self.printing.print_gantt_pdf(pdf_path)

                    results.append({"project_id": project_id, "success": True})

                except Exception as e:
                    results.append({"project_id": project_id, "success": False, "error": str(e)})

        return results
```

---

## Sources & References

- [GUI Architectures - Martin Fowler](https://martinfowler.com/eaaDev/uiArchs.html)
- [Data Flow Architecture](https://www.tutorialspoint.com/software_architecture_design/data_flow_architecture.htm)
- [Decomposing High-Complexity UI Automation](https://www.ensolvers.com/post/decomposing-high-complexity-ui-automation-through-a-specification-flow-component-architecture)
- [Automation Solutions Using Design Patterns](https://www.uipath.com/community-blog/tutorials/automation-solutions-using-design-patterns)
- [Application Design Patterns: State Machines](https://www.ni.com/en/support/documentation/supplemental/16/simple-state-machine-template-documentation.html)
- [UI Automation Control Patterns](https://learn.microsoft.com/en-us/dotnet/framework/ui-automation/ui-automation-control-patterns-overview)
- [Model-Based GUI Automation](https://link.springer.com/article/10.1007/s10270-025-01319-9)
- [Retry Pattern - Azure Architecture](https://learn.microsoft.com/en-us/azure/architecture/patterns/retry)

---

**Document Version:** 1.0
**Last Updated:** 2026-02-07
**Architecture Style:** Layered + Event-Driven
**Key Patterns:** Command, State, Strategy, Observer, Transaction
