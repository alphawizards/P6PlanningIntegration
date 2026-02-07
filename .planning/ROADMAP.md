# Roadmap: P6 Planning Integration

## Overview

This roadmap transforms P6 Professional from a complex desktop application requiring manual GUI operation into a conversational tool operated through Claude Code. Starting with reliable connection and navigation (Phase 1), we build toward safe activity editing with transaction guards (Phase 2), scheduling operations with validation (Phase 3), import/export capabilities (Phase 4), layout management (Phase 5), and finally a natural language interface that orchestrates all capabilities (Phase 6). Each phase delivers verifiable user capabilities while progressively managing risk through read-only operations first, validated writes second, and batch/intelligence features last.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Connection & Navigation Foundation** - Detect P6, navigate EPS, open projects, track state
- [ ] **Phase 2: Activity Editing with Safety** - Edit dates/durations/logic with validation and rollback
- [ ] **Phase 3: Scheduling Operations** - Run scheduler, read logic, validate constraints, analyze critical path
- [ ] **Phase 4: Import & Export** - Import XER/XML, export schedules, print PDFs with custom naming
- [ ] **Phase 5: Layouts & Filters** - Apply layouts, filters, create/modify layout definitions
- [ ] **Phase 6: Natural Language Interface** - Claude Code skills orchestrating all operations with confirmation

## Phase Details

### Phase 1: Connection & Navigation Foundation
**Goal**: Claude can reliably connect to P6, navigate projects, and track application state
**Depends on**: Nothing (first phase)
**Requirements**: NAV-01, NAV-02, NAV-03, NAV-04, NAV-05, SAFE-03, SAFE-04
**Success Criteria** (what must be TRUE):
  1. Claude detects and connects to a running P6 Professional instance
  2. Claude navigates the EPS tree to locate any project by Project ID
  3. Claude opens a specified project and confirms it is active
  4. Claude closes the current project and returns to EPS view
  5. Claude tracks which project is open, which view is active, and which layout is applied
  6. Claude recovers from unexpected P6 states (modal dialogs, timeouts, element not found)
**Plans**: TBD

Plans:
- [ ] TBD during planning

### Phase 2: Activity Editing with Safety
**Goal**: Claude can modify activity data through P6 GUI with comprehensive validation and rollback capability
**Depends on**: Phase 1 (requires navigation to open projects)
**Requirements**: EDIT-01, EDIT-02, EDIT-03, EDIT-04, EDIT-05, EDIT-06, EDIT-07, SAFE-01, SAFE-02
**Success Criteria** (what must be TRUE):
  1. Claude exports an XER backup before making any edits
  2. Claude edits activity start dates, finish dates, and durations through the P6 GUI activity table
  3. Claude adds, removes, and modifies predecessor/successor relationships (FS, SS, FF, SF with lag)
  4. Claude creates new activities in the P6 activity table with valid properties
  5. Claude locates specific activities by Activity ID in the current project
  6. If any edit fails or produces invalid schedule state, Claude restores the backup XER automatically
**Plans**: TBD

Plans:
- [ ] TBD during planning

### Phase 3: Scheduling Operations
**Goal**: Claude can run the scheduler, analyze results, validate constraints, and report critical path
**Depends on**: Phase 2 (requires editing capability to make changes worth scheduling)
**Requirements**: SCHED-01, SCHED-02, SCHED-03, SCHED-04
**Success Criteria** (what must be TRUE):
  1. Claude runs the P6 scheduler (F9) after making changes and confirms completion
  2. Claude reads back and reports activity relationships and logic from the P6 GUI
  3. Claude identifies and reports which activities are on the critical path
  4. Claude validates constraints before editing (detects conflicts like SNET vs FNLT) and blocks invalid edits
**Plans**: TBD

Plans:
- [ ] TBD during planning

### Phase 4: Import & Export
**Goal**: Claude can import schedules into P6 and export schedules/PDFs with custom naming
**Depends on**: Phase 1 (requires navigation and state tracking)
**Requirements**: IO-01, IO-02, IO-03, IO-04, IO-05, IO-06
**Success Criteria** (what must be TRUE):
  1. Claude imports XER files from a user-specified folder into P6 via GUI import dialog
  2. Claude imports XML files from a user-specified folder into P6 via GUI import dialog
  3. Claude exports the current schedule as XER or XML to a user-specified folder
  4. Claude prints the current schedule view to PDF via P6 print dialog
  5. Claude names the PDF file according to user specification (e.g., "TSFE6_Rev3_2026-02-07.pdf")
  6. Claude saves all exported/printed files to user-specified folders by navigating Save As dialogs
**Plans**: TBD

Plans:
- [ ] TBD during planning

### Phase 5: Layouts & Filters
**Goal**: Claude can apply, create, and modify P6 layouts and filters to control schedule views
**Depends on**: Phase 1 (requires P6 connection and navigation)
**Requirements**: LAYOUT-01, LAYOUT-02, LAYOUT-03
**Success Criteria** (what must be TRUE):
  1. Claude applies an existing named layout in P6 and confirms the view changed
  2. Claude applies activity filters to show/hide specific activities in the current view
  3. Claude creates or modifies layout definitions in P6 based on user specifications
**Plans**: TBD

Plans:
- [ ] TBD during planning

### Phase 6: Natural Language Interface
**Goal**: User can operate P6 through natural language in Claude Code with confirmation and summaries
**Depends on**: Phases 1-5 (orchestrates all previous capabilities)
**Requirements**: UI-01, UI-02, UI-03, UI-04
**Success Criteria** (what must be TRUE):
  1. User can give natural language commands like "Open TSFE6 and push activity A1020 back 2 weeks" and Claude executes them
  2. User can provide an Excel/CSV file with activity IDs and changes, and Claude applies them
  3. Before editing P6, Claude summarizes proposed changes and asks for user confirmation
  4. After completing operations, Claude provides a summary of what changed and the new values
**Plans**: TBD

Plans:
- [ ] TBD during planning

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Connection & Navigation Foundation | 0/TBD | Not started | - |
| 2. Activity Editing with Safety | 0/TBD | Not started | - |
| 3. Scheduling Operations | 0/TBD | Not started | - |
| 4. Import & Export | 0/TBD | Not started | - |
| 5. Layouts & Filters | 0/TBD | Not started | - |
| 6. Natural Language Interface | 0/TBD | Not started | - |
