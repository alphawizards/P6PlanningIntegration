# Phase 6: Natural Language Interface - Context

**Gathered:** 2026-02-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Build Claude Code skills that orchestrate all previous phase capabilities through natural language conversation. Handle conversational commands, spreadsheet-based batch changes, confirmation workflows, and change summaries. This phase ties everything together — no new P6 GUI automation, just orchestration and user experience.

</domain>

<decisions>
## Implementation Decisions

### Natural language commands
- **Command style:** Conversational — user talks to Claude naturally, not with structured commands
- **Examples:**
  - "I need to update the TSFE6 schedule — a few activities need their dates changed"
  - "Open GEMCO and push the earthworks activities back 2 weeks"
  - "Can you add a predecessor link from A1019 to A1020 in TSFE6?"
- **Claude interprets:** Parse the intent, identify the project, activities, and changes, then execute using Phase 1-5 capabilities
- **Multi-step:** A single conversational message may require multiple operations (open project, find activities, edit, schedule)

### Spreadsheet input (Excel/CSV)
- **Format:** User will provide specific Excel templates generated from P6 that define the structure
- **Claude's role:** Read the template, understand the column mapping, and apply changes from the spreadsheet data
- **No fixed format assumption:** Templates come from P6's own export, so Claude reads the structure rather than expecting a predefined format
- **User provides:** The Excel file path and instructions on what to do with it

### Confirmation before editing
- **Detail level:** Quick list — brief bullet points summarizing proposed changes
- **Format example:** "I'll change A1020 duration from 10d to 15d, A1021 start to 15-Mar-26"
- **When to confirm:** Before making any edits to P6 — always ask, never edit without confirmation
- **User response:** User says yes/no/modify — Claude proceeds, stops, or adjusts

### Change summary after operations
- **Detail level:** What changed + new values — list of activities modified with their new values
- **No before/after comparison needed** — just report what was done and the current state
- **Format:** Brief list of changes made and resulting values
- **Include:** Any errors or skipped activities if applicable

### Claude's Discretion
- How to parse conversational intent into specific P6 operations
- How to read and interpret P6 Excel template structures
- How to format confirmation lists and change summaries for readability
- How to chain multiple operations from a single conversational instruction
- When to ask clarifying questions vs. making reasonable assumptions

</decisions>

<specifics>
## Specific Ideas

- Conversational style means Claude should handle ambiguity — if user says "push back 2 weeks" Claude needs to understand this means adding 14 days to dates
- P6 Excel templates are the key to spreadsheet input — they define the schema, so Claude needs to parse the template structure dynamically
- Quick list confirmation keeps the workflow fast — user doesn't want to review a detailed table for every small change
- Change summaries should be concise — "A1020: Duration now 15d, A1021: Start now 15-Mar-26" style

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-natural-language-interface*
*Context gathered: 2026-02-07*
