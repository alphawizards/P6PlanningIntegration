# Phase 4: Import & Export - Context

**Gathered:** 2026-02-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Import XER/XML files into P6, export schedules as XER/XML, print schedule views to PDF via Print Preview, and navigate Save As dialogs with user-specified filenames and folders. No editing (Phase 2), no scheduling (Phase 3) — just reliable file import, export, and PDF generation.

</domain>

<decisions>
## Implementation Decisions

### Importing XER files
- **Menu path:** File → Import
- **Wizard:** Multi-step wizard (file selection → import options → mapping → confirmation)
- **Import action:** User changes the import action setting (Add New / Update Existing / Replace) — Claude should ask user which action to use for each import
- **Workflow:** File → Import → select .xer file → navigate wizard steps → set import action per user instruction → click Finish/Import
- **User provides:** File path/folder and import action for each import

### Importing XML files
- **Menu path:** File → Import (same menu entry as XER)
- **Wizard:** Different wizard steps than XER — XML has its own set of screens
- **Import action:** Same principle — user specifies the action each time
- **Key difference:** The wizard steps differ between XER and XML formats, so Claude needs to handle both wizard flows

### Exporting schedules (XER/XML)
- **Menu path:** File → Export
- **Wizard:** Multi-step wizard (similar structure to import)
- **Filename:** User will specify the exact filename and path to Claude each time
- **Workflow:** File → Export → navigate wizard → specify format (XER or XML) → set filename per user instruction → select destination folder → Finish

### Printing to PDF
- **Method:** File → Print Preview → File → Print (from within Print Preview)
- **PDF printer:** Microsoft Print to PDF (Windows built-in)
- **Save As dialog:** Standard Windows Save As dialog — navigate to folder, type filename, click Save
- **Filename:** User will specify the exact PDF filename (e.g., "TSFE6_Rev3_2026-02-07.pdf")
- **Folder:** User will specify the destination folder each time
- **Workflow:** File → Print Preview → File → Print → select "Microsoft Print to PDF" → OK → type filename in Save As → navigate to folder → Save

### File naming & Save As navigation
- **All filenames specified by user:** Claude doesn't generate names — user provides exact filename and path
- **Save As dialogs:** Standard Windows dialogs — navigate folder tree, type filename, click Save
- **No default naming convention:** Each export/print gets a user-specified name

### Claude's Discretion
- How to navigate the import wizard steps (button labels, timing between steps)
- How to detect wizard completion (final confirmation or return to main view)
- How to switch between XER and XML in the import wizard
- Wait timing for large file imports
- How to handle the Print Preview window state

</decisions>

<specifics>
## Specific Ideas

- Import wizard has different steps for XER vs XML — Claude needs to recognize which wizard flow is active based on the file type selected
- The import action (Add/Update/Replace) is the critical user decision per import — always ask before proceeding
- Print Preview is an intermediate step — don't try to print directly from File → Print without going through Preview first
- Microsoft Print to PDF produces a standard Windows Save As dialog — reliable for automation
- User specifies all filenames and paths — Claude navigates dialogs to enter them

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-import-export*
*Context gathered: 2026-02-07*
