# Feature Research: Promptable P6 Automation Tool

## Executive Summary

This document researches the features needed for a natural language-operated P6 Professional automation tool. Features are categorized by priority (table stakes vs differentiators vs anti-features) and complexity (easy/medium/hard), based on what project planners do daily and what provides the most value.

---

## 1. Table Stakes Features (Must Have)

These are core P6 operations that planners perform daily. Without these, the tool is unusable.

### 1.1 Project Management

#### Open Project by ID or Name
**What:** Connect to EPS, navigate hierarchy, open specific project
**Why:** Every P6 session starts here
**Complexity:** Medium
**GUI Challenge:**
- EPS tree can be deeply nested (5+ levels)
- Large enterprises have 1000+ projects
- Tree view lazy-loads on expand
- Search dialog is inconsistent

**Natural Language Examples:**
- "Open project 19282"
- "Open the Highway Expansion project"
- "Switch to project ABC-2024-001"

**Implementation Notes:**
```python
# Existing: src/automation/projects.py - P6ProjectManager
# Already handles EPS navigation and project opening
# Needs enhancement for fuzzy name matching
```

#### Close Current Project
**What:** Close active project without closing P6
**Why:** Free resources, switch contexts
**Complexity:** Easy
**GUI Challenge:** Simple menu operation

**Natural Language Examples:**
- "Close this project"
- "Close current project"

---

#### List Available Projects
**What:** Read EPS tree, return project list with IDs/names
**Why:** User doesn't know exact project name
**Complexity:** Medium
**GUI Challenge:**
- Must expand entire EPS tree (slow)
- Extract text from tree items
- Handle scrolling for long lists

**Natural Language Examples:**
- "Show me all projects"
- "List projects in the Downtown EPS"
- "What projects are available?"

---

### 1.2 Activity Operations

#### Find Activity by ID
**What:** Locate activity in current view/all activities
**Why:** Planners reference activities by ID constantly
**Complexity:** Medium
**GUI Challenge:**
- Activity spreadsheet has 20+ columns
- May need to scroll thousands of rows
- ID column might not be visible
- Grid cell access can be slow

**Natural Language Examples:**
- "Find activity A1010"
- "Show me task ABC-001"
- "Locate activity with ID 12345"

**Implementation Notes:**
```python
# Existing: src/automation/activities.py - P6ActivityManager
# Has select_activity() method
# Needs enhancement for cross-project search
```

---

#### Edit Activity Dates
**What:** Change start/finish dates, duration
**Why:** #1 most common planner action
**Complexity:** Hard
**GUI Challenge:**
- Must click into grid cell
- Date picker dialog (sometimes)
- Format validation (dd-MMM-yy)
- Constraint warnings (modal dialogs)
- Can trigger auto-scheduling

**Natural Language Examples:**
- "Change A1010 start date to March 15, 2024"
- "Set finish date of task ABC to 30-May-2024"
- "Update duration of activity 1234 to 10 days"
- "Move A1010 start date by 5 days"

**Data Integrity Risks:**
- Constraint conflicts (can't start before predecessor)
- Calendar violations (non-work days)
- Baseline corruption if not suspended

---

#### Edit Activity Logic (Predecessors/Successors)
**What:** Add, remove, modify activity relationships
**Why:** Critical path management, sequencing
**Complexity:** Hard
**GUI Challenge:**
- Relationship dialog is modal, multi-step
- Must select relationship type (FS, SS, FF, SF)
- Lag entry (days, hours, percent)
- Duplicate detection
- Can trigger auto-scheduling

**Natural Language Examples:**
- "Add finish-to-start from A1010 to A1020"
- "Make A1020 a successor of A1010 with 5-day lag"
- "Remove the relationship between A1010 and A1030"
- "Change lag to 10 days for A1010 -> A1020"

**Data Integrity Risks:**
- Circular logic (loops)
- Orphaned activities
- Constraint conflicts
- Schedule date corruption

---

### 1.3 Scheduling Operations

#### Run Schedule (F9)
**What:** Execute scheduling engine
**Why:** Calculate dates after changes
**Complexity:** Medium
**GUI Challenge:**
- Can take 1-300 seconds
- Progress dialog appears (unpredictable)
- Modal "Scheduling Complete" dialog
- Error dialogs for issues
- Status bar updates

**Natural Language Examples:**
- "Schedule the project"
- "Run F9"
- "Calculate the schedule"
- "Recalculate dates"

**Implementation Notes:**
```python
# Existing: src/automation/scheduling.py - P6ScheduleManager
# Has schedule_project() method
# Handles progress monitoring
```

---

#### Check Schedule Quality
**What:** Run built-in schedule health checks
**Why:** Validate schedule meets standards
**Complexity:** Medium (v22+), N/A (v21)
**GUI Challenge:**
- Feature added in v22.12
- Multi-step dialog
- Results in separate report window
- Must parse text output

**Natural Language Examples:**
- "Check schedule quality"
- "Run DCMA 14-point assessment"
- "Validate the schedule"

**Version Dependency:**
- P6 v22.12+: Built-in Check Schedule Report
- P6 v21.x: Must export and analyze externally

---

### 1.4 View/Layout Management

#### Apply Layout
**What:** Switch to different view configuration
**Why:** Different reports need different layouts
**Complexity:** Easy
**GUI Challenge:**
- Layout dropdown in toolbar
- Simple selection

**Natural Language Examples:**
- "Apply the Monthly Report layout"
- "Switch to Lookahead view"
- "Change to Cost Report layout"

**Implementation Notes:**
```python
# Existing: src/automation/layouts.py - P6LayoutManager
# Has apply_layout() method
```

---

#### List Available Layouts
**What:** Read layout dropdown, return names
**Why:** User doesn't remember exact layout name
**Complexity:** Easy
**GUI Challenge:** Read combobox items

**Natural Language Examples:**
- "Show me all layouts"
- "What layouts are available?"

---

### 1.5 Import/Export

#### Export to XER
**What:** File -> Export -> XER format
**Why:** Backups, data exchange, version control
**Complexity:** Medium
**GUI Challenge:**
- Multi-step wizard dialog
- File save dialog
- Options checkboxes
- Long export time (30-120s)
- Success/error modal

**Natural Language Examples:**
- "Export current project to XER"
- "Save a backup as XER file"
- "Export to C:\backups\project.xer"

**Implementation Notes:**
```python
# Existing: src/automation/exporting.py - P6ExportManager
# Has export_xer() method
```

---

#### Import XER File
**What:** File -> Import -> XER format
**Why:** Restore backups, load external data
**Complexity:** Hard
**GUI Challenge:**
- Multi-step wizard (5+ screens)
- EPS assignment
- Duplicate handling options
- Conflict resolution dialogs
- Can take 5+ minutes
- Error log window

**Natural Language Examples:**
- "Import the file C:\data\project.xer"
- "Load backup.xer into EPS Downtown"

**Data Integrity Risks:**
- Duplicate project IDs
- WBS conflicts
- Calendar mismatches
- Resource pool corruption

---

#### Print to PDF
**What:** Print preview -> Print to PDF printer
**Why:** Report generation, documentation
**Complexity:** Medium
**GUI Challenge:**
- Print preview window
- Printer selection dialog
- PDF save dialog
- Print settings
- Multi-page handling

**Natural Language Examples:**
- "Print current view to PDF"
- "Generate PDF report as schedule.pdf"
- "Print Gantt chart to C:\reports\gantt.pdf"

**Implementation Notes:**
```python
# Existing: src/automation/printing.py - P6PrintManager
# Has print_gantt_pdf() method
```

---

## 2. Differentiator Features (High Value)

These features save significant time and differentiate from manual P6 use.

### 2.1 Batch Operations

#### Batch Project Exports
**What:** Export multiple projects in sequence
**Why:** Save hours vs manual one-by-one
**Complexity:** Medium
**Time Savings:** 5-10 minutes per project

**Natural Language Examples:**
- "Export all projects in Downtown EPS to XER"
- "Batch export projects 19282, 19283, 19284"
- "Export all active projects to C:\exports\"

**Implementation Notes:**
```python
# Existing: src/automation/batch.py - P6BatchProcessor
# Has batch_export() method
```

---

#### Batch Layout + Print
**What:** Loop: open project -> apply layout -> print PDF
**Why:** Weekly/monthly report generation
**Complexity:** Medium
**Time Savings:** 10-30 minutes per report cycle

**Natural Language Examples:**
- "Generate weekly reports for all active projects"
- "Print Lookahead PDFs for projects A, B, C"
- "Create monthly Gantt charts for all projects in EPS Downtown"

---

#### Bulk Activity Updates
**What:** Update multiple activities with same change
**Why:** Global date shifts, mass rescheduling
**Complexity:** Hard
**Time Savings:** Hours for large projects

**Natural Language Examples:**
- "Delay all activities in WBS 1.2 by 10 days"
- "Set all procurement activities to start after March 1"
- "Change duration of all design tasks to 5 days"

**Data Integrity Risks:**
- Constraint violations
- Logic breaks
- Calendar conflicts

---

### 2.2 Smart Filters

#### Find Activities by Criteria
**What:** Query activities by multiple attributes
**Why:** Identify problem areas, generate targeted reports
**Complexity:** Medium
**GUI Challenge:**
- Must read entire activity grid
- Filter by date range, WBS, status, etc.

**Natural Language Examples:**
- "Show me all critical path activities"
- "Find activities starting next week"
- "List all late activities"
- "Show activities in WBS 1.2.3 with duration > 20 days"

---

#### Identify Schedule Issues
**What:** Detect missing logic, long durations, date constraints
**Why:** Proactive quality management
**Complexity:** Medium
**Time Savings:** 30-60 minutes of manual review

**Natural Language Examples:**
- "Find activities with no successors"
- "Show me all date constraints"
- "List activities with duration over 30 days"
- "Find hard constraints"

**Implementation Pattern:**
```python
# Read grid data -> analyze -> return filtered list
# Can leverage existing activity reading
```

---

### 2.3 Schedule Analysis

#### Compare Current vs Baseline
**What:** Highlight variance (dates, durations, logic)
**Why:** Performance tracking, trend analysis
**Complexity:** Hard
**GUI Challenge:**
- Must load baseline
- Compare two states
- Generate delta report

**Natural Language Examples:**
- "Compare current schedule to Baseline 1"
- "Show me what changed since last week"
- "Generate variance report"

---

#### Critical Path Analysis
**What:** Identify and report critical activities
**Why:** Focus on what matters
**Complexity:** Medium
**Time Savings:** 15-30 minutes

**Natural Language Examples:**
- "Show me the critical path"
- "List all critical activities"
- "What's driving the finish date?"

---

### 2.4 Automation Intelligence

#### Activity Suggestion
**What:** Recommend next steps based on schedule state
**Why:** Guidance for less experienced planners
**Complexity:** Hard
**AI Component:** Claude analyzes schedule, suggests actions

**Natural Language Examples:**
- "What should I work on next?"
- "Suggest ways to improve this schedule"
- "How can I reduce the critical path?"

**Implementation:**
```python
# Export schedule data -> Claude analysis -> suggestions
# Combines automation with LLM reasoning
```

---

#### Change Impact Preview
**What:** Simulate change before applying
**Why:** Avoid mistakes, build confidence
**Complexity:** Hard
**GUI Challenge:**
- Need read-only "what-if" mode
- Compare before/after states

**Natural Language Examples:**
- "What happens if I delay A1010 by 5 days?"
- "Preview impact of adding FS relationship"

---

## 3. Anti-Features (Do NOT Automate)

These features should be blocked or require explicit confirmation to prevent damage.

### 3.1 Destructive Operations

#### Delete Projects
**What:** Remove entire project from database
**Why Anti-Feature:** Irreversible data loss
**Mitigation:** Require manual confirmation, log action

**Blocked Commands:**
- "Delete project 19282"
- "Remove this project"

**Safe Alternative:**
- "Export project 19282 to backup.xer" (before manual delete)

---

#### Delete Baselines
**What:** Remove saved schedule snapshots
**Why Anti-Feature:** Historical data loss
**Mitigation:** Warn, require explicit "yes I'm sure"

---

#### Global Resource Pool Changes
**What:** Modify shared resources across all projects
**Why Anti-Feature:** Enterprise-wide impact, can break other projects
**Mitigation:** Read-only access

---

#### Delete Activities in Bulk
**What:** Mass deletion without careful review
**Why Anti-Feature:** Easy to delete wrong activities
**Mitigation:** Require export backup first, item-by-item confirmation

---

### 3.2 High-Risk Write Operations

#### Baseline Assignment
**What:** Change which baseline is active
**Why Anti-Feature:** Affects reporting, performance metrics
**Mitigation:** Require approval, log change

---

#### Calendar Modifications
**What:** Change work days, holidays, hours
**Why Anti-Feature:** Affects all activities using calendar
**Mitigation:** Report-only, no writes

---

#### Project Code Changes
**What:** Modify activity codes, WBS codes
**Why Anti-Feature:** Can break rollup reports, integrations
**Mitigation:** Validate before applying

---

#### Constraint Type Changes
**What:** Change from ASAP to "Must Start On"
**Why Anti-Feature:** Removes schedule flexibility
**Mitigation:** Warn about impact, suggest alternatives

---

### 3.3 Operations Requiring Human Judgment

#### Merge Projects
**Why Anti-Feature:** Complex conflict resolution
**Alternative:** Export both -> manual merge -> import

#### Change Project Dates (Start/Finish)
**Why Anti-Feature:** Global impact, calendar recalc
**Alternative:** Report date conflicts, suggest manual fix

#### Resource Leveling
**Why Anti-Feature:** Subjective, many options
**Alternative:** Report over-allocations, manual leveling

#### Cost/Earned Value Updates
**Why Anti-Feature:** Financial data, audit requirements
**Alternative:** Read-only reporting

---

## 4. Feature Complexity Matrix

| Feature | Complexity | GUI Steps | Error Modes | Data Risk | Time Savings |
|---------|-----------|-----------|-------------|-----------|--------------|
| **Open Project** | Medium | 3-5 | 3 | Low | 30s |
| **Close Project** | Easy | 1-2 | 1 | None | 10s |
| **Find Activity** | Medium | 5-10 | 2 | None | 1-2min |
| **Edit Date** | Hard | 5-8 | 5 | Medium | 30s |
| **Edit Logic** | Hard | 10-15 | 7 | High | 1-2min |
| **Run Schedule** | Medium | 2-3 | 4 | Low | 15-300s |
| **Apply Layout** | Easy | 2-3 | 1 | None | 15s |
| **Export XER** | Medium | 8-12 | 5 | Low | 2-5min |
| **Import XER** | Hard | 15-20 | 10+ | High | 5-10min |
| **Print PDF** | Medium | 8-12 | 6 | None | 2-3min |
| **Batch Export** | Medium | N×10 | N×5 | Low | N×3min |
| **Batch Print** | Medium | N×12 | N×6 | None | N×4min |
| **Bulk Updates** | Hard | N×8 | N×5 | High | Hours |
| **Find by Criteria** | Medium | 5-15 | 2 | None | 5-15min |
| **Compare Baseline** | Hard | 20-30 | 8 | Low | 15-30min |

**Legend:**
- **GUI Steps:** Number of UI interactions required
- **Error Modes:** Distinct failure scenarios
- **Data Risk:** Potential for schedule corruption
- **Time Savings:** vs manual operation

---

## 5. Progressive Disclosure Strategy

Don't build everything at once. Deliver in phases:

### Phase 1: Read-Only Core (Weeks 1-2)
- Open/close project
- List projects/layouts
- Find activity
- Apply layout
- Export XER/PDF
- Run schedule (read-only)

**Goal:** Prove GUI automation works, no data risk

---

### Phase 2: Safe Writes (Weeks 3-4)
- Edit activity dates (with constraints)
- Edit durations
- Add/remove logic
- Import XER (sandbox only)

**Goal:** Enable actual schedule changes, controlled risk

---

### Phase 3: Batch Operations (Week 5)
- Batch export
- Batch print
- Batch layout+print

**Goal:** Demonstrate time savings, ROI

---

### Phase 4: Intelligence (Week 6+)
- Smart filters
- Schedule analysis
- Change preview
- Activity suggestions

**Goal:** Differentiation, AI-powered insights

---

## 6. Natural Language Interface Design

### Command Categories

| Category | Example Commands | Feature(s) |
|----------|-----------------|------------|
| **Navigation** | "open project X", "switch to layout Y" | Open, Apply |
| **Search** | "find activity A", "show me all critical tasks" | Find, Filter |
| **Modify** | "change start date to...", "add relationship..." | Edit Date, Logic |
| **Execute** | "schedule the project", "run F9" | Schedule |
| **Report** | "export to XER", "print to PDF" | Export, Print |
| **Batch** | "export all projects", "print reports for..." | Batch ops |
| **Query** | "what layouts are available?", "list projects" | List, Query |
| **Analysis** | "compare to baseline", "show critical path" | Analysis |

### Parsing Strategy

```python
class CommandParser:
    """Map natural language to P6 operations"""

    PATTERNS = {
        "open_project": [
            r"open project (?P<identifier>[\w-]+)",
            r"load (?P<identifier>[\w-]+)",
            r"switch to (?P<identifier>[\w-]+)",
        ],
        "edit_activity_date": [
            r"change (?P<activity>\w+) start date to (?P<date>[\w\s,-]+)",
            r"set (?P<activity>\w+) finish to (?P<date>[\w\s,-]+)",
            r"update (?P<activity>\w+) duration to (?P<days>\d+) days",
        ],
        "add_relationship": [
            r"add (?P<type>FS|SS|FF|SF) from (?P<pred>\w+) to (?P<succ>\w+)",
            r"make (?P<succ>\w+) a successor of (?P<pred>\w+)",
        ],
    }

    def parse(self, command: str) -> dict:
        """Return (action, params) tuple"""
        # Claude Code's ReAct pattern will handle this
        # via tool calling
```

---

## 7. Feature Prioritization

### Priority 1: Daily Operations (Build First)
1. Open/close project
2. Apply layout
3. Find activity
4. Export XER
5. Print PDF
6. Run schedule

**Rationale:** Covers 80% of planner actions

---

### Priority 2: Time Savers (Build Second)
1. Batch export
2. Batch print
3. Edit dates (safe mode)
4. Find by criteria

**Rationale:** Clear ROI, low risk

---

### Priority 3: Advanced (Build Third)
1. Edit logic
2. Bulk updates
3. Import XER
4. Baseline comparison
5. Schedule analysis

**Rationale:** Higher value, higher complexity

---

### Priority 4: Intelligence (Build Last)
1. Activity suggestions
2. Change preview
3. Schedule optimization
4. Anomaly detection

**Rationale:** Requires Phase 1-3 foundation

---

## Sources & References

- [Sling: Employee Scheduling Features](https://getsling.com/)
- [Motion: AI Project Scheduling](https://www.usemotion.com/blog/project-scheduling-software)
- [Schedule Management Time-Savers](https://wheniwork.com)
- [Data Integrity in Automation](https://www.ibm.com/think/insights/data-integrity-strategy)
- [Common Data Integrity Issues](https://www.dataversity.net/common-data-integrity-issues-and-how-to-overcome-them/)
- [What's New in P6 v22.12](https://www.taradigm.com/whats-new-in-primavera-p6-professional-22-12/)
- [P6 Version Differences](https://www.p6consulting.ca/blog/what-are-the-differences-between-versions-of-primavera-p6/)

---

**Document Version:** 1.0
**Last Updated:** 2026-02-07
**Based On:** Project planner daily workflows, existing codebase capabilities
