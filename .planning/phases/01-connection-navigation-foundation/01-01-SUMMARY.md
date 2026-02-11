---
phase: 01-connection-navigation-foundation
plan: 01
subsystem: automation-core
tags: [pywinauto, connection, error-handling, modal-detection]

dependency-graph:
  requires: []
  provides:
    - Simplified P6AutomationBase.connect() for always-running P6
    - Modal dialog detection via detect_unexpected_dialog()
    - Immediate-fail element operations (no retry)
    - P6UnexpectedDialogError exception
  affects:
    - 01-02 (navigation uses immediate_click/immediate_type)
    - 01-03 (window management builds on base connection)

tech-stack:
  added: []
  patterns:
    - "Connect-only pattern: never start P6, always assume running"
    - "Immediate failure: GUI element ops fail on first error, no retry"
    - "Connection retry preserved: @retry decorator on connect() only"

key-files:
  created: []
  modified:
    - src/automation/base.py
    - src/automation/utils.py
    - src/automation/exceptions.py

decisions:
  - id: "01-01-D1"
    decision: "Remove all P6 launching code (p6_path, _start_p6, start_if_not_running)"
    rationale: "User confirmed P6 is always already running and logged in"
  - id: "01-01-D2"
    decision: "Replace safe_click retry loop with immediate_click (single attempt)"
    rationale: "User requirement: no automatic retries, stop immediately and tell the user"
  - id: "01-01-D3"
    decision: "Keep safe_click/safe_type as deprecated aliases"
    rationale: "Backward compatibility during transition; existing code won't break"

metrics:
  duration: "~5 min"
  completed: 2026-02-08
---

# Phase 1 Plan 1: Connection Foundation Simplification Summary

Stripped P6AutomationBase down to connect-only behavior and removed retry logic from GUI element operations, aligning with user decisions that P6 is always running and errors should fail immediately.

## Task Commits

| Task | Name | Commit | Key Changes |
|------|------|--------|-------------|
| 1 | Simplify P6AutomationBase for always-running P6 | d628428 | Removed _start_p6(), start_if_not_running, p6_path; added detect_unexpected_dialog(); added P6UnexpectedDialogError |
| 2 | Remove retry from element-finding utilities | c9cdae9 | Replaced safe_click retry loop with immediate_click; added immediate_type; documented retry() as connection-only |

## What Changed

### src/automation/base.py
- **Removed** `p6_path` parameter from `__init__()` and `P6_EXECUTABLE_PATH` import
- **Removed** `_start_p6()` method entirely
- **Removed** `start_if_not_running` parameter from `connect()`
- **Simplified** `connect()` error handling: `ElementNotFoundError` always raises `P6NotFoundError` with message "Please start P6 and log in first"
- **Preserved** `@retry` decorator on `connect()` (connection retry is user-approved)
- **Added** `detect_unexpected_dialog()` method that checks for modal dialogs via `Desktop(backend="uia").active_window()` and returns dialog title and text
- **Added** `P6UnexpectedDialogError` to exception imports
- **Removed** `p6_path` from `get_status()` return dict
- **Removed** unused `os` import

### src/automation/utils.py
- **Replaced** `safe_click()` (had retry loop) with `immediate_click()` (single attempt, fails immediately)
- **Added** `immediate_type()` (single attempt, no retry)
- **Added** deprecated aliases: `safe_click = immediate_click`, `safe_type = immediate_type`
- **Added** docstring note on `retry()` decorator: connection-only, do not apply to GUI element operations

### src/automation/exceptions.py
- **Added** `P6UnexpectedDialogError(P6AutomationError)` for modal dialog reporting

## Decisions Made

1. **Remove all P6 launching code** -- p6_path, _start_p6(), start_if_not_running parameter all removed. P6 is always already running per user decision.
2. **Immediate failure on element operations** -- safe_click's retry loop replaced with single-attempt immediate_click. User requirement: "No automatic retries -- stop immediately and tell the user."
3. **Deprecated aliases preserved** -- safe_click and safe_type kept as aliases pointing to immediate_click/immediate_type so existing code doesn't break during transition.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused `os` import from base.py**
- **Found during:** Task 1
- **Issue:** `import os` was unused after removing p6_path logic
- **Fix:** Removed the import
- **Files modified:** src/automation/base.py

**2. [Rule 1 - Bug] Removed `p6_path` from get_status() return dict**
- **Found during:** Task 1
- **Issue:** get_status() still referenced self.p6_path which no longer exists
- **Fix:** Removed the key from the status dict
- **Files modified:** src/automation/base.py

## Verification Results

- All three files parse with valid Python syntax
- No references to `start_if_not_running`, `_start_p6`, or `P6_EXECUTABLE_PATH` in base.py
- No retry loops in immediate_click or immediate_type
- `retry()` decorator preserved (connection-only, documented)
- `detect_unexpected_dialog()` method exists in P6AutomationBase
- `P6UnexpectedDialogError` exists in exceptions.py

## Next Phase Readiness

No blockers. base.py, utils.py, and exceptions.py are ready for Plans 01-02 (navigation) and 01-03 (window management) to build upon.

## Self-Check: PASSED
