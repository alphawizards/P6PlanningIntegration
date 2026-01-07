# Directive: List Projects

## Goal
Retrieve a list of all projects currently available in the P6 Database to provide context or selection options.

## Inputs
None

## Execution Steps
1. **Run List Script**
   - Rationale: Connects to SQLite DB and fetches project table.
   - Tool: `execution/list_projects.py`
   - Command: `python execution/list_projects.py`

## Output
- File: `.tmp/projects_list.json`
- Content: JSON array of project objects including `ObjectId`, `Id`, `Name`, `Status`.

## Edge Cases & Handling
- If `success: False` in output -> Check database path in `.env` and `src/config/settings.py`.
