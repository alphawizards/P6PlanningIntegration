# Phase 1: Connection & Navigation Foundation - Context

**Gathered:** 2026-02-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Detect a running P6 Professional instance, navigate the EPS tree view to locate projects by Project ID, open/close projects, and track P6 application state. Error recovery from unexpected GUI states. No editing, no importing, no scheduling — just reliable connection and navigation.

</domain>

<decisions>
## Implementation Decisions

### P6 detection & startup
- P6 is always already running when user starts Claude Code — no need to launch P6
- Only ever one P6 instance running — no multi-instance handling needed
- User is already logged in — no login dialog handling needed
- P6 window title: standard "Primavera P6 Professional" (confirm exact title during implementation)
- Connect by finding the existing P6 window via pywinauto

### EPS tree navigation
- EPS hierarchy is 3 levels deep: Level 1 EPS (blue bands) → Level 2 Sub-EPS (green bands) → Projects (yellow bands)
- **Primary navigation method: Ctrl+F search** — not manual tree expansion
- Search workflow:
  1. Click inside the Project Hierarchy Grid (left pane) to ensure focus
  2. Ctrl+F to open Find dialog
  3. Type the exact Project ID (e.g., "TSFE6PFS" or "18714")
  4. Click "Find Next" — P6 auto-expands collapsed nodes and scrolls to the match
  5. Verify the highlighted row's Project ID matches the target
  6. Close the Find dialog (Esc or Close button)
- Fallback if Ctrl+F doesn't find: project doesn't exist or is filtered out — report to user
- Tree nodes are mostly collapsed — Ctrl+F handles this automatically
- User typically gives just the Project ID, not the full EPS path
- Column layout in EPS: Project ID, Project Name, Responsible Manager, Data Date, Project Baseline

### Project open/close behavior
- **Opening:** Right-click on the found project row → "Open Project" from context menu
- After opening, P6 switches to the Activities view automatically
- Activities view has three zones:
  - Zone A: Activity Grid (left pane) — WBS tree with activities, column order varies by layout
  - Zone B: Gantt Chart (right pane) — visual only, don't automate drag-drop here
  - Zone C: Details Form (bottom pane) — **primary zone for data entry** (more reliable than grid cells)
- Details form tabs: General, Status, Resources, Relationships, Codes, Notebook (tab order can change)
- Activity identification: by Activity ID column, with row highlighted blue when selected
- Critical activities marked with red indicators, completed with checkmarks
- **Closing:** File → Close All, or Ctrl+W
- P6 prompts "Are you sure you want to close project?" — Claude must click Yes/OK to confirm
- Usually one project at a time — open, work, close, then open another if needed

### Error recovery behavior
- **No automatic retries** — if Claude can't find a UI element or something goes wrong, stop immediately and tell the user
- P6 can hang when opening large projects (1000+ activities) — need appropriate wait timeouts
- Unexpected popups are rare but handle any modal dialog by reading its text and reporting to user
- **Silent operation** — don't narrate each step, just report the final result or the error

### Claude's Discretion
- Exact pywinauto backend choice (UIA vs win32) for P6 Java Swing controls
- Wait timeout durations for P6 operations
- How to detect which view is currently active (Activities vs Projects tab)
- Implementation of P6 state tracking internals

</decisions>

<specifics>
## Specific Ideas

- User provided detailed P6 EPS view structure: blue bands = Level 1 EPS, green bands = Level 2 Sub-EPS, yellow bands = Projects, white rows = WBS elements
- The Details Form (bottom pane) is more reliable for data entry than direct grid cell editing — use this principle in Phase 2
- Ctrl+F is the standard P6 protocol for finding projects — it auto-expands collapsed nodes, which is key since the tree is mostly collapsed
- After Ctrl+F, verify match by checking the Project ID column text AND the Details Form header (secondary confirmation)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-connection-navigation-foundation*
*Context gathered: 2026-02-07*
