# P6 Planning Integration — Agent Instructions

## Project Overview
A fully promptable P6 Professional automation tool operated through Claude Code. Users describe schedule changes in natural language — "open TSFE6 and push activity X back 2 weeks" — and Claude operates the P6 desktop application via GUI automation. Built for mining/engineering project planners managing multiple P6 schedules.

**Core Value:** A planner can sit in Claude Code and operate P6 Professional through conversation — open projects, edit activities, change logic, import files, export schedules, and print PDFs — without touching the P6 interface themselves.

## Architecture

```
Config → Core → DAO → Business Logic → AI/Automation → Reporting
```

- **P6 Application:** Delphi/DevExpress desktop app (NOT Java Swing)
  - Main window class: `TDevxMainForm`
  - Edit controls: `TCDBEdit` (data-bound Delphi Edit)
  - Grid: `TCVirtualQueryGrid`
  - Tab system: `TCCSPageControl` / `TcsTabSheet`
- **GUI Automation:** pywinauto (win32 backend) + Delphi VCL message protocol
- **Python:** 3.12+, strict type hints, Pydantic validation
- **Platform:** Windows only — P6 Professional is a Windows desktop app

## Key Technical Discoveries

- **UIA backend is unusable** on P6 20: 15-90 seconds per operation
- **win32 backend** connects instantly and `children()` exposes all controls
- **Delphi VCL message protocol** is the only working approach for editing:
  - `AttachThreadInput` for cross-process `SetFocus`
  - `EM_SETSEL(0, -1)` to select all text
  - `WM_CHAR` for each character
  - `CN_COMMAND(0xBD11)` — Delphi VCL notification
  - `WM_KEYDOWN(VK_RETURN)` to commit
  - Background thread for Confirmation dialog handling (date changes)
- **P6 20 has NO "Dates" tab** — dates are on the Status tab

## Current State (as of 2026-02-11)

- **Phase 1 (Foundation):** ✅ COMPLETED (3/3 plans)
- **Phase 2 (Activity Editing with Safety):** ✅ COMPLETED (4/4 plans)
- **Phase 3 (Logic & Relationships):** ⏳ NOT STARTED — next phase to plan
- **Overall Progress:** ~33% (2 of 6 phases)

See `.planning/STATE.md` for full state and `.planning/PROJECT.md` for requirements.

## Key Files

| File | Purpose |
|------|---------|
| `src/automation/activity_editor.py` | Core editing via Delphi VCL protocol (~734 lines) |
| `src/automation/base.py` | P6 connection/window management (still uses UIA — needs migration) |
| `src/automation/exceptions.py` | Custom exception classes |
| `src/automation/__init__.py` | Package exports |
| `.planning/STATE.md` | Current project state, decisions, metrics |
| `.planning/PROJECT.md` | Project requirements and scope |
| `.planning/phases/` | Phase plans and summaries |
| `summary_schedule_generator/` | Separate utility for generating P6 summary schedules |
| `main.py` | Main entry point |

## Conventions

- **Strict typing:** Python type hints mandatory on all functions
- **Docstrings:** Required on complex functions (>10 lines)
- **Error handling:** Raise immediately, no silent `except: pass`
- **Security:** No hardcoded secrets, use `os.environ`
- **GUI writes only:** All P6 modifications go through GUI, never direct DB
- **Tests:** pytest, colocated with modules where practical

## Agent Team Roles

When working as part of an agent team:

### Orchestrator/Planner (Lead)
- Creates implementation plans before delegating work
- Breaks tasks into independent, parallelizable units
- Reviews completed work before marking tasks done
- Does NOT implement code directly — delegates to Builder
- Reads `.planning/STATE.md` and `.planning/PROJECT.md` for context

### Builder Agent
- Implements code changes based on task specifications
- Follows project conventions strictly (type hints, docstrings, error handling)
- Writes clean, documented code
- Reports completion with summary of changes

### Tester/Validator Agent
- Writes and runs tests for completed features
- Validates code quality and conventions
- Reports issues back to lead with specific file/line references
- Runs linting, type checks, and integration tests

## Dependencies

See `requirements.txt`. Key deps:
- pywinauto (GUI automation)
- pyautogui (tab clicking)
- ctypes (Delphi VCL message protocol)
- pytest (testing)
