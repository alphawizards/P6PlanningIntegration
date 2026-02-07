# Requirements: P6 Planning Integration

**Defined:** 2026-02-07
**Core Value:** A planner can operate P6 Professional through conversation in Claude Code — open projects, edit activities, change logic, import files, export schedules, and print PDFs.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Connection & Navigation

- [ ] **NAV-01**: Claude detects and connects to a running P6 Professional instance
- [ ] **NAV-02**: Claude navigates the EPS tree view to locate a project by Project ID
- [ ] **NAV-03**: Claude opens a project via right-click context menu in EPS
- [ ] **NAV-04**: Claude closes the current project when done
- [ ] **NAV-05**: Claude tracks P6 application state (which project is open, which view is active, which layout is applied)

### Activity Editing

- [ ] **EDIT-01**: Claude edits activity start dates through the P6 GUI activity table
- [ ] **EDIT-02**: Claude edits activity finish dates through the P6 GUI activity table
- [ ] **EDIT-03**: Claude edits activity original/remaining duration through the P6 GUI
- [ ] **EDIT-04**: Claude adds predecessor relationships (FS, SS, FF, SF with lag) through the P6 GUI
- [ ] **EDIT-05**: Claude removes or modifies existing predecessor/successor relationships
- [ ] **EDIT-06**: Claude creates new activities in the P6 activity table
- [ ] **EDIT-07**: Claude locates specific activities by Activity ID in the current project

### Scheduling & Analysis

- [ ] **SCHED-01**: Claude runs the scheduler (F9) after making changes
- [ ] **SCHED-02**: Claude reads back and reports activity relationships/logic from the P6 GUI
- [ ] **SCHED-03**: Claude identifies and reports critical path activities
- [ ] **SCHED-04**: Claude validates constraints before editing (detects conflicts like SNET vs FNLT)

### Import & Export

- [ ] **IO-01**: Claude imports XER files from a user-specified local folder into P6 via GUI import dialog
- [ ] **IO-02**: Claude imports XML files from a user-specified local folder into P6 via GUI import dialog
- [ ] **IO-03**: Claude exports schedules from P6 as XER or XML via GUI export dialog
- [ ] **IO-04**: Claude prints the current schedule view to PDF via P6 print dialog
- [ ] **IO-05**: Claude names the PDF file based on user specification (e.g., "TSFE6_Rev3_2026-02-07.pdf")
- [ ] **IO-06**: Claude saves exported/printed files to a user-specified folder by navigating the Save As dialog

### Layouts & Filters

- [ ] **LAYOUT-01**: Claude applies an existing named layout in P6
- [ ] **LAYOUT-02**: Claude applies activity filters in the current view
- [ ] **LAYOUT-03**: Claude creates or modifies layout definitions in P6

### Interface (Claude Code)

- [ ] **UI-01**: User can give natural language commands ("Open TSFE6 and push activity A1020 back 2 weeks")
- [ ] **UI-02**: User can provide an Excel/CSV file with activity IDs and changes for Claude to apply
- [ ] **UI-03**: Claude summarizes proposed changes and asks for confirmation before editing P6
- [ ] **UI-04**: Claude provides a change summary after completing operations (what changed, what the new values are)

### Safety & Reliability

- [ ] **SAFE-01**: Claude exports an XER backup of the current schedule before making any edits
- [ ] **SAFE-02**: Claude can rollback changes by re-importing the backup XER
- [ ] **SAFE-03**: Claude recovers from unexpected P6 states (dialog popups, timeouts, element not found)
- [ ] **SAFE-04**: Claude retries failed GUI operations with exponential backoff before reporting failure

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Batch & Performance

- **BATCH-01**: Process large change requests (50+ activities) with progress tracking
- **BATCH-02**: Periodic P6 restart during batch operations to handle memory leaks
- **BATCH-03**: Adaptive timeouts based on project size

### AI Intelligence

- **AI-01**: Change impact preview (show downstream effects before committing)
- **AI-02**: Schedule optimization suggestions
- **AI-03**: Activity ID suggestions when creating new activities (based on WBS conventions)

### Reporting

- **RPT-01**: Generate schedule comparison reports (before vs after changes)
- **RPT-02**: Generate critical path reports with float analysis

### Read-Only Mode

- **RO-01**: Preview mode that shows what would change without editing P6

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web UI or separate chat app | Claude Code is the interface — no separate app |
| Direct database writes | All changes through P6 GUI to preserve data integrity |
| P6 EPPM / cloud versions | Local P6 Professional only |
| Resource management | Schedule/activity focused, not resource-focused |
| Cost loading | Schedule focused, not cost-focused |
| P6 installation/setup | User already has P6 running |
| Multi-user concurrent access | Single planner workflow |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| NAV-01 | Phase 1 | Pending |
| NAV-02 | Phase 1 | Pending |
| NAV-03 | Phase 1 | Pending |
| NAV-04 | Phase 1 | Pending |
| NAV-05 | Phase 1 | Pending |
| EDIT-01 | Phase 2 | Pending |
| EDIT-02 | Phase 2 | Pending |
| EDIT-03 | Phase 2 | Pending |
| EDIT-04 | Phase 2 | Pending |
| EDIT-05 | Phase 2 | Pending |
| EDIT-06 | Phase 2 | Pending |
| EDIT-07 | Phase 2 | Pending |
| SCHED-01 | Phase 3 | Pending |
| SCHED-02 | Phase 3 | Pending |
| SCHED-03 | Phase 3 | Pending |
| SCHED-04 | Phase 3 | Pending |
| IO-01 | Phase 4 | Pending |
| IO-02 | Phase 4 | Pending |
| IO-03 | Phase 4 | Pending |
| IO-04 | Phase 4 | Pending |
| IO-05 | Phase 4 | Pending |
| IO-06 | Phase 4 | Pending |
| LAYOUT-01 | Phase 5 | Pending |
| LAYOUT-02 | Phase 5 | Pending |
| LAYOUT-03 | Phase 5 | Pending |
| UI-01 | Phase 6 | Pending |
| UI-02 | Phase 6 | Pending |
| UI-03 | Phase 6 | Pending |
| UI-04 | Phase 6 | Pending |
| SAFE-01 | Phase 2 | Pending |
| SAFE-02 | Phase 2 | Pending |
| SAFE-03 | Phase 1 | Pending |
| SAFE-04 | Phase 1 | Pending |

**Coverage:**
- v1 requirements: 31 total
- Mapped to phases: 31
- Unmapped: 0

---
*Requirements defined: 2026-02-07*
*Last updated: 2026-02-07 after initial definition*
