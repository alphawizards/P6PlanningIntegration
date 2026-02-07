# P6 Planning Integration

## What This Is

A fully promptable P6 Professional automation tool operated through Claude Code. Users describe schedule changes in natural language — "open TSFE6 and push activity X back 2 weeks" — and Claude operates the P6 desktop application via GUI automation to make it happen. Built for mining/engineering project planners managing multiple P6 schedules.

## Core Value

A planner can sit in Claude Code and operate P6 Professional through conversation — open projects, edit activities, change logic, import files, export schedules, and print PDFs — without touching the P6 interface themselves.

## Requirements

### Validated

- ✓ Dual connection modes (SQLite standalone + Java/JPype enterprise) — existing
- ✓ File parsers for XER, XML, MPX schedule formats — existing
- ✓ AI agent with ReAct pattern and multi-provider LLM support — existing
- ✓ GUI automation foundation via pywinauto for P6 Professional — existing
- ✓ Schedule analysis and reporting layers — existing
- ✓ Automation manager classes (projects, layouts, scheduling, activities, printing, exporting) — existing (partial)

### Active

- [ ] Navigate P6 EPS view and open projects by Project ID
- [ ] Edit activity start/finish dates through P6 GUI
- [ ] Edit activity durations through P6 GUI
- [ ] Edit activity predecessors/successors (logic ties) through P6 GUI
- [ ] Create new activities in P6 through GUI
- [ ] Run scheduler (F9) after changes
- [ ] Review and read back logic/relationship data from P6 GUI
- [ ] Import XER/XML files from local folders into P6 via GUI
- [ ] Export schedules from P6 (XER, PDF, Excel) via GUI
- [ ] Print schedule PDFs with custom naming convention
- [ ] Save exported/printed files to user-specified folders
- [ ] Apply and switch layouts/filters in P6 via GUI
- [ ] Claude Code skills/tools as the interaction interface
- [ ] Handle verbal/email-style change requests (1-10 activity changes)
- [ ] Handle spreadsheet-based change requests (Excel/CSV with activity IDs and values)

### Out of Scope

- Web UI or separate chat application — Claude Code is the interface
- Direct database writes — all changes go through P6 GUI
- P6 EPPM/cloud versions — local P6 Professional only
- Bulk re-baseline operations (50+ activities) — focus on typical 1-10 change requests
- Resource management — focus on schedule/activity operations
- Cost loading — schedule-focused, not cost-focused

## Context

**Existing codebase:** Substantial foundation already built with layered architecture (Config → Core → DAO → Business Logic → AI/Automation → Reporting). GUI automation layer exists but has incomplete implementations (TODOs in navigation, dialog handling, project tree traversal). The AI agent ReAct loop works but needs P6 GUI tools wired in as Claude Code skills.

**Target user:** Mining/engineering project planner managing multiple P6 schedules (TSFE6, GEMCO Excess Water, TSF17, GEMCO Closure, etc.). Receives change requests via email or spreadsheet, needs to apply them across projects quickly.

**P6 environment:** P6 Professional 21.x-23.x running locally on Windows. Standalone mode (SQLite database). GUI interaction only — no direct database writes.

**Key technical challenge:** P6's GUI is complex with tree views, right-click context menus, dialog chains, and dynamic table layouts. Reliable GUI automation requires robust element identification, wait conditions, and error recovery.

**Existing automation gaps (from codebase analysis):**
- Project tree navigation in EPS view is incomplete
- Dialog handling for import/export has TODOs
- Activity editing through GUI cells not fully implemented
- Print automation has stubbed-out features
- Broad `except Exception: pass` blocks hide failures

## Constraints

- **Platform**: Windows only — P6 Professional is a Windows desktop application
- **GUI-only writes**: All P6 modifications must go through the GUI, not direct database access
- **P6 Version**: Must work with P6 Professional 21.x-23.x
- **Interface**: Claude Code is the sole user interface — no separate app
- **Reliability**: GUI automation must handle P6's inconsistent UI timing (dialogs, loading, tree expansion)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| GUI-only for all writes | User wants P6 to see and process all changes natively; avoids database corruption risk | -- Pending |
| Claude Code as interface | No separate app to build/maintain; leverages existing Claude Code skills system | -- Pending |
| Focus on 1-10 activity changes per request | Matches typical workflow; larger batches deferred | -- Pending |
| P6 Professional 21.x-23.x target | User's current environment | -- Pending |
| Read data through GUI (not database) | User preference for consistency — Claude sees what the user sees | -- Pending |

---
*Last updated: 2026-02-07 after initialization*
