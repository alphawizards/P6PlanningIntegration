# Phase 3: Scheduling Operations - Context

**Gathered:** 2026-02-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Run the P6 scheduler (F9), read activity relationships and logic, identify critical path activities, and validate constraints before edits. No editing (Phase 2), no importing (Phase 4) — just reliable scheduling execution, logic reading, critical path analysis, and constraint awareness.

</domain>

<decisions>
## Implementation Decisions

### Running the scheduler (F9)
- **Trigger:** Press F9 to open the Schedule dialog
- **Settings:** Just click "Schedule" with defaults — user doesn't change settings each time
- **Data Date:** Stays the same after scheduling — F9 uses whatever Data Date is already set, does not update it
- **Completion indicator:** No progress bar or summary — P6 just returns to the Activities view with updated dates
- **Errors:** F9 only fails on circular logic between activities — P6 pops up an error showing which activities are circular
- **Claude's workflow:** Press F9 → click Schedule → wait for view to refresh → confirm dates updated (or catch circular logic error)

### Reading relationships & logic
- **Primary method:** Select activity → Relationships tab in Details Form (bottom pane)
- **Relationships tab columns:** Activity ID, Activity Name, Relationship Type (FS/SS/FF/SF), Lag
- **Alternative method:** Predecessor and Successor columns can be added to the Activity Grid for a quick overview without switching to the Details Form
- **Both methods available:** Use Relationships tab for detailed inspection, grid columns for quick scans
- **Reading workflow:** Select activity → switch to Relationships tab → read predecessor/successor entries

### Critical path reporting
- **Identification method:** Critical activities display as red bars in the Gantt chart
- **How Claude identifies critical activities:** Look for red bar indicators in the Gantt chart view (Zone B)
- **Reporting detail:** Full details — Activity ID, Activity Name, Total Float, Start Date, Finish Date, Duration
- **Alternative identification:** Total Float column in grid — zero or negative float indicates critical

### Constraint validation
- **Constraint usage:** Occasional — some activities have constraints (SNET, FNLT, etc.) but not all
- **When to check:** Claude should check for constraints on date-related edits
- **Conflict behavior:** Warn and stop — tell user about the conflict and don't make the change until user decides
- **Constraint types to watch for:** Start Not Earlier Than (SNET), Finish Not Later Than (FNLT), Mandatory Start, Mandatory Finish
- **Where constraints appear:** General tab in Details Form shows the constraint type and date for the selected activity

### Claude's Discretion
- How to detect that F9 scheduling has completed (view refresh timing)
- How to read red bar indicators from the Gantt chart (visual detection vs Total Float column approach)
- Wait timing after F9 before reading updated values
- How to efficiently scan multiple activities for critical path identification

</decisions>

<specifics>
## Specific Ideas

- F9 with defaults is the standard workflow — no need to parse or interact with scheduler dialog options beyond clicking "Schedule"
- Circular logic is the only F9 failure mode that needs handling — catch the error popup, read which activities, report to user
- The Relationships tab is the authoritative source for logic data, but grid columns provide a faster scan
- Critical path detection via Total Float = 0 may be more automatable than visual red bar detection in the Gantt
- Constraint checking before date edits prevents P6 from silently adjusting or rejecting the edit

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-scheduling-operations*
*Context gathered: 2026-02-07*
