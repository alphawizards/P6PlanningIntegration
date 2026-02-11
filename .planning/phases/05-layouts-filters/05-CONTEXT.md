# Phase 5: Layouts & Filters - Context

**Gathered:** 2026-02-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Apply existing layouts and filters in P6, create new layouts, and modify layout definitions (columns, grouping, sorting). No editing activities (Phase 2), no scheduling (Phase 3) — just reliable layout and filter management.

</domain>

<decisions>
## Implementation Decisions

### Applying layouts
- **Menu path:** View → Layout
- **Dialog:** Opens a layout management dialog (not a simple dropdown list)
- **Workflow:** View → Layout → layout management dialog → select layout by name → Apply/OK
- **Primary use case:** Selecting and applying an existing saved layout — this is the most common operation
- **User provides:** The layout name to apply

### Applying filters
- **Menu path:** View → Filters
- **Dialog:** Shows a list of saved/named filters to select and apply
- **Workflow:** View → Filters → filter dialog → select filter by name → Apply/OK
- **Primary use case:** Picking from pre-existing saved filters — not building filters on the fly
- **User provides:** The filter name to apply

### Creating and modifying layouts
- **Access:** View → Layout menu has options for creating/editing alongside the layout list
- **Modification types:** All of the following:
  - Add, remove, and reorder columns in the activity grid
  - Change activity grouping settings
  - Change sorting settings
  - Other layout settings as needed
- **User provides:** Description of desired layout changes — Claude interprets and applies them through the layout editor

### Claude's Discretion
- How to navigate the layout management dialog controls
- How to find specific layouts by name in the dialog list
- How to navigate the layout editor for column/grouping/sorting changes
- How to detect that a layout or filter has been successfully applied (view refresh)

</decisions>

<specifics>
## Specific Ideas

- Layout management is a dialog, not a dropdown — Claude needs to interact with dialog controls (list, buttons) rather than menu items
- Filter application is straightforward — pick from saved names, apply
- Layout creation/modification is the most complex operation in this phase — the layout editor has multiple tabs/sections for columns, grouping, sorting
- Applying layouts is far more common than creating them — optimize for the apply workflow

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-layouts-filters*
*Context gathered: 2026-02-07*
