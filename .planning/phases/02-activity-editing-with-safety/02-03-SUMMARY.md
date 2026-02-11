# Phase 2 Plan 3: Refactor create_activity + Add backup_to_xer Summary

**One-liner:** Full activity creation workflow (name, duration, WBS, type, calendar) with on-demand XER backup export

## Task Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Refactor create_activity in P6ActivityManager | 5994296 | src/automation/activities.py |
| 2 | Add backup_to_xer to P6ExportManager | 938e585 | src/automation/exporting.py |

## What Was Built

### Task 1: create_activity refactor

Replaced the minimal `add_activity()` stub with a full `create_activity()` method that:

- Accepts activity_name, duration, wbs_node, activity_type, and calendar parameters
- Navigates to WBS node via Ctrl+F Find dialog before inserting (if specified)
- Inserts activity via INSERT key, types activity name, presses Enter
- Sets Remaining Duration on the Details Form "Status" tab
- Sets Activity Type and Calendar on the Details Form "General" tab via ComboBox selection
- Preserves `add_activity()` as a deprecated alias that calls `create_activity()`

Added two helper methods:
- `_get_details_pane()` -- locates the Activity Details bottom pane
- `_select_details_tab(tab_name)` -- clicks a tab in the details pane TabControl

Added imports: `immediate_click`, `immediate_type` from `.utils`

### Task 2: backup_to_xer

Added `backup_to_xer(output_path)` to P6ExportManager that:

- Resolves and validates the output path, ensures parent dirs exist
- Adds .xer extension if missing
- Temporarily swaps `self.output_dir` with try/finally to reuse `export_to_xer()`
- Verifies the backup file was created and is non-empty
- Logs file size in KB
- Raises P6ExportError on failure

## Deviations from Plan

None -- plan executed exactly as written.

## Verification Results

- AST parse confirms `create_activity`, `add_activity`, `_get_details_pane`, `_select_details_tab` all present in P6ActivityManager
- All 19 pre-existing methods preserved (verified by name)
- AST parse confirms `backup_to_xer` present in P6ExportManager
- All 12 pre-existing methods preserved (verified by name)
- Python syntax valid (AST parsed without errors)

## Decisions Made

None -- followed plan specification directly.

## Self-Check: PASSED
