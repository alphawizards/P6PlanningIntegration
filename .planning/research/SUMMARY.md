# Project Research Summary

**Project:** P6 Professional GUI Automation Tool
**Domain:** Enterprise Desktop Application Automation
**Researched:** 2026-02-07
**Confidence:** HIGH

## Executive Summary

This project aims to build a Claude Code-operated automation system for Oracle Primavera P6 Professional, enabling natural language control of the enterprise project management application. P6 is a Java Swing/AWT desktop application with complex GUI patterns, requiring robust automation that handles custom controls, modal dialogs, and version differences across P6 21.x-23.x.

The research reveals a clear path: use pywinauto with a hybrid UIA/Win32 backend strategy, wrapped in a layered architecture with Claude Code skills at the top. Start with read-only operations to prove the automation works, then progressively add safe write operations, batch processing, and finally AI-powered intelligence features. The existing codebase already implements many core managers (projects, layouts, activities, scheduling, printing, exporting), providing a solid foundation.

The critical risk is data corruption from GUI-based edits. P6's scheduling engine is sensitive to constraint violations, circular logic, and improper date modifications. Mitigate this through validation layers, pre-change checks, XER backups before writes, and transaction-like operations with rollback capability. Secondary risks include Java Swing's limited automation accessibility (30-40% of controls require OCR fallback), version-specific UI differences, and memory leaks requiring periodic P6 restarts during batch operations.

## Key Findings

### Recommended Stack

The stack centers on pywinauto 0.6.8+ as the primary automation framework, selected for its industry-standard Windows GUI automation capabilities, active development, and existing codebase integration. The critical decision is backend selection: UIA provides better Java Swing control visibility (70-90% coverage vs 40-60% for Win32) but runs slower. Use a hybrid strategy defaulting to UIA with Win32 fallback for performance-critical operations.

**Core technologies:**
- **pywinauto 0.6.8+**: Windows GUI automation — industry standard with dual backend support
- **tesseract/easyocr**: OCR fallback layer — handles custom-drawn controls (Gantt charts, status bars)
- **tenacity 8.2.0+**: Retry patterns — essential for enterprise app delays and unpredictable timing
- **psutil 5.9.0+**: Process management — detect P6 instances, monitor memory leaks, kill hung processes
- **structlog 23.1.0+**: Structured logging — debugging complex GUI workflows and performance tracking
- **Python 3.10/3.11**: Runtime — avoid 3.12 due to pywin32 compatibility issues

**Supporting libraries:** Pillow/OpenCV for screen capture, pywin32 for Windows integration, pandas for data validation. Use pytest with timeout extensions for testing. The stack is proven in the existing codebase which already implements core P6 automation patterns.

### Expected Features

Research identified 20+ P6 operations that planners perform daily, categorized into must-have table stakes, high-value differentiators, and anti-features that should be blocked to prevent damage.

**Must have (table stakes):**
- Open/close projects by ID or name — every P6 session starts here
- Find activities by ID — planners reference activities constantly
- Apply layouts — different reports need different views
- Export to XER — backups, version control, data exchange
- Print to PDF — report generation and documentation
- Run schedule (F9) — calculate dates after changes
- Edit activity dates/durations — most common planner action
- Edit activity logic (predecessors/successors) — critical path management

**Should have (differentiators):**
- Batch project exports — save 5-10 minutes per project vs manual
- Batch layout + print — weekly/monthly report automation
- Find activities by criteria — identify issues proactively
- Critical path analysis — focus on what drives finish date
- Compare baseline vs current — performance tracking
- Activity suggestions (AI) — recommend next steps based on schedule state

**Defer (anti-features requiring explicit confirmation):**
- Delete projects/baselines — irreversible data loss
- Global resource pool changes — enterprise-wide impact
- Bulk activity deletions — easy to delete wrong activities
- Calendar modifications — affects all activities using calendar
- Constraint type changes — removes schedule flexibility

**Progressive disclosure strategy:** Build read-only operations first (weeks 1-2) to prove automation works with no data risk. Add safe writes in weeks 3-4 with validation constraints. Enable batch operations in week 5 to demonstrate ROI. Add AI-powered intelligence features in week 6+ for differentiation.

### Architecture Approach

The system uses a five-layer architecture: Claude Code skills at the top, command translation layer for validation, orchestration layer for state management, manager layer encapsulating P6 operations, and pywinauto/OCR at the bottom. This separation enables clear boundaries between natural language processing, business rules, GUI automation, and error recovery.

**Major components:**
1. **Claude Skills Layer** — Maps natural language to structured commands, returns JSON results, no direct GUI access
2. **Command Translation Layer** — Strongly-typed command objects with validation, precondition checks, business rules
3. **P6 State Manager** — Tracks open project, active view, P6 version, modal dialogs, scheduling status; coordinates recovery
4. **GUI Automation Managers** — P6ProjectManager (EPS/projects), P6LayoutManager (views), P6ActivityManager (CRUD), P6ScheduleManager (F9/baselines), P6PrintManager (PDF), P6ExportManager (XER/XML), P6BatchProcessor (multi-ops)
5. **Error Recovery System** — Dialog monitors, retry strategies, transaction management with XER backups, adaptive timeouts

**Key patterns:** Command pattern for operations, State pattern for P6 tracking, Strategy pattern for recovery, Observer pattern for events, Transaction pattern for safe writes. Data flow is unidirectional (user → Claude → skill → command → state check → manager → GUI → state update → result). State mutation only happens in managers via StateManager to ensure atomic all-or-nothing updates.

### Critical Pitfalls

Research identified 50+ failure modes across P6 UI quirks, pywinauto reliability issues, dialog chains, data integrity risks, timing problems, and environmental factors. The top risks that must be addressed:

1. **Custom-drawn Java controls** — 30-40% of P6 controls (Gantt chart, custom toolbars, status bar segments) don't expose accessible properties. Detection: use Inspect.exe in UIA mode; if control shows as generic "Pane" with no properties, it's custom-drawn. Workaround: use OCR (slow, 300-500ms per region), keyboard shortcuts instead of clicks, or database reads for validation.

2. **Dynamic control IDs** — Java generates automation_ids dynamically on each launch, breaking scripts that hardcode them. Solution: never rely on automation_id; use title, class_name, control_type, or positional indexes; cache control references during session.

3. **Schedule corruption from constraint violations** — Editing activity dates without validating predecessor/successor relationships causes invalid schedules. Prevention: read current relationships, validate new date doesn't violate constraints, create XER backup, edit date, schedule to recalc, verify no errors, rollback on failure.

4. **Circular logic from relationship edits** — Adding relationship D→A when A→B→C→D already exists creates undetectable loop until F9 fails. Prevention: implement cycle detection with BFS graph traversal before adding any relationship.

5. **Unexpected modal dialogs block automation** — P6 shows confirmation/error/warning dialogs unpredictably (scheduling complete, constraint conflicts, file overwrite, circular logic). Solution: background thread monitoring for dialogs, auto-handle common patterns (close "Scheduling Complete", log and propagate errors, respect safe mode for confirmations).

**Secondary pitfalls:** Lazy-loading EPS tree (must expand path step-by-step), slow grid cell access (export to file instead of reading 1000+ cells), UIA backend hangs (5-10% of operations, use timeout wrapper), version-specific features (Check Schedule Report only in v22.12+), memory leaks (restart P6 every 25-50 operations in batch mode), timing issues (adaptive timeouts based on project size, not fixed).

## Implications for Roadmap

Based on architecture dependencies, feature complexity, and risk mitigation strategy, the roadmap should follow a progressive disclosure approach with five phases. Start with proven read-only operations to build confidence, add write operations with strong guards, then scale to batch operations and intelligence features.

### Phase 1: Foundation & Read-Only Operations
**Rationale:** Prove GUI automation works with existing codebase managers while building state tracking and error recovery infrastructure. Zero data corruption risk since no writes. Establishes Claude Code skills pattern for all future phases.

**Delivers:** Working P6 automation with natural language interface for safe operations
- Claude Code skills wrapper around existing managers
- P6 State Manager tracking open project, view, version, dialogs
- Open/close project (using existing P6ProjectManager)
- List projects/layouts (read-only tree/dropdown access)
- Find activity by ID (using existing P6ActivityManager)
- Apply layout (using existing P6LayoutManager)
- Export XER (using existing P6ExportManager)
- Print PDF (using existing P6PrintManager)
- Run schedule (F9) with progress monitoring

**Addresses Features:** Open project, close project, list projects, find activity, apply layout, list layouts, export XER, print PDF, run schedule (all from table stakes)

**Avoids Pitfalls:** No write operations = no schedule corruption, no circular logic, no baseline overwrites. Implements modal dialog monitoring and version detection from day one.

**Research Flags:** Standard patterns, no additional research needed. Existing codebase has working implementations.

### Phase 2: Safe Write Operations with Guards
**Rationale:** Enable actual schedule modifications but with comprehensive validation to prevent corruption. Build transaction system with XER backups before every write. This is the highest-risk phase requiring careful testing.

**Delivers:** Controlled write operations with rollback capability
- Command validation layer (precondition checks, constraint validation)
- Transaction manager (XER backup before write, restore on failure)
- Edit activity dates with constraint validation
- Edit activity durations with bounds checking
- Add/remove activity relationships with cycle detection
- Error recovery system for unexpected dialogs
- Safe mode flag to block writes

**Addresses Features:** Edit activity dates, edit activity durations, edit activity logic (from table stakes), constraint validation (from pitfalls prevention)

**Avoids Pitfalls:** Pre-validates constraints before date edits, implements cycle detection for relationships, creates XER backups before writes, validates schedule integrity after changes, rollback on corruption.

**Research Flags:** May need deeper research on P6's constraint resolution rules and how different constraint types interact. Test extensively on sandbox projects with complex logic.

### Phase 3: Batch Operations & Performance
**Rationale:** Demonstrate clear ROI through time savings. Batch operations expose performance issues (memory leaks, timeout problems) requiring adaptive strategies and periodic restarts.

**Delivers:** Multi-operation workflows with intelligent resource management
- Batch project exports (existing P6BatchProcessor)
- Batch layout + print workflows (monthly report generation)
- Adaptive timeout calculation based on project size
- Periodic P6 restart to prevent memory leaks (every 25-50 ops)
- Progress reporting for long-running batches
- Metrics collection (operation timing, success/failure rates)

**Addresses Features:** Batch project exports, batch layout + print, bulk updates (all from differentiators)

**Avoids Pitfalls:** Implements P6 restart strategy to handle memory leaks, uses adaptive timeouts for large projects, adds progress monitoring for scheduling delays.

**Research Flags:** Standard patterns for batch processing. Monitor for version-specific performance differences.

### Phase 4: Smart Filters & Analysis
**Rationale:** Build on read-only foundation to provide proactive quality management and schedule insights. Requires efficient grid data extraction (export to file vs cell-by-cell).

**Delivers:** Schedule quality analysis and issue detection
- Find activities by multiple criteria (critical path, date ranges, WBS, status)
- Identify schedule issues (missing logic, long durations, hard constraints)
- Critical path analysis and reporting
- Compare baseline vs current schedule
- Activity spreadsheet data extraction (via export, not grid reads)
- Integration with existing DAO layer for validation

**Addresses Features:** Find activities by criteria, identify schedule issues, critical path analysis, compare baseline (all from differentiators)

**Avoids Pitfalls:** Uses file export instead of slow grid cell-by-cell reads (150 seconds vs 5 seconds for 1000 activities).

**Research Flags:** No additional research needed. Standard data extraction and analysis patterns.

### Phase 5: AI-Powered Intelligence
**Rationale:** Differentiation through Claude's reasoning capabilities. Requires stable foundation from Phases 1-4. Combines automation data with LLM analysis to provide guidance.

**Delivers:** Intelligent schedule assistance and optimization
- Activity suggestions based on schedule state analysis
- Change impact preview (what-if simulation)
- Schedule optimization recommendations
- Anomaly detection (unusual patterns, outliers)
- Natural language schedule queries
- Integration: export schedule data → Claude analysis → suggestions

**Addresses Features:** Activity suggestions, change impact preview (from differentiators), schedule optimization (deferred to v2)

**Avoids Pitfalls:** Read-only analysis with manual approval before any suggested changes are applied.

**Research Flags:** May need research on advanced scheduling algorithms (CPM optimization, resource leveling strategies) to provide intelligent recommendations.

### Phase Ordering Rationale

- **Foundation first:** Phase 1 builds infrastructure (state management, error recovery, skills pattern) needed by all subsequent phases. Zero risk establishes confidence.
- **Writes before batch:** Phase 2 must precede Phase 3 because batch operations need validated write operations. Transaction system with backups is critical before scaling.
- **Batch before analysis:** Phase 3 handles performance issues (memory leaks, timeouts) that Phase 4's data extraction will encounter. Metrics from batch operations inform Phase 4 optimization.
- **Analysis before AI:** Phase 4 provides data extraction and validation patterns that Phase 5's intelligence features build upon. Can't analyze schedule quality without reading schedule data.
- **Progressive risk:** Each phase adds complexity only after previous foundation is stable. Read-only → validated writes → scaled writes → analysis → intelligence follows natural dependency chain.

### Research Flags Summary

**Needs deeper research during planning:**
- **Phase 2:** P6 constraint resolution rules and interaction between constraint types (ASAP, ALAP, MSO, MFO, SNET, SNLT, FNET, FNLT)
- **Phase 5:** Advanced scheduling algorithms for optimization recommendations, resource leveling strategies

**Standard patterns (skip research-phase):**
- **Phase 1:** Read-only GUI automation, state tracking, error recovery
- **Phase 3:** Batch processing, resource management, metrics collection
- **Phase 4:** Data extraction, filtering, analysis

All phases should reference PITFALLS.md during planning to ensure discovered failure modes are addressed in implementation.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | pywinauto proven in existing codebase, UIA/Win32 backends well-documented, OCR libraries mature |
| Features | HIGH | Based on planner daily workflows and existing codebase capabilities, feature complexity matrix validated |
| Architecture | HIGH | Layered architecture with clear boundaries follows established GUI automation patterns, existing managers provide foundation |
| Pitfalls | HIGH | Research covered 50+ failure modes across P6 versions 21-23, Java Swing challenges, enterprise app timing issues |

**Overall confidence:** HIGH

Research quality is high due to multiple authoritative sources (Microsoft UIA docs, pywinauto documentation, P6 release notes), existing codebase validation, and comprehensive pitfall documentation. The hybrid UIA/Win32 strategy is proven, the progressive disclosure approach mitigates risk, and transaction patterns address data corruption concerns.

### Gaps to Address

Minor gaps requiring attention during implementation:

- **P6 constraint type interactions:** How do different constraint types (ASAP, MSO, SNET, etc.) interact when editing dates? Research covered basic validation but not complex multi-constraint scenarios. Validate during Phase 2 planning with P6 documentation and sandbox testing.

- **Java Access Bridge potential:** Research identified Java Access Bridge as experimental alternative to UIA for better Swing component access. Prototype during Phase 1 if UIA coverage proves insufficient, but don't block progress on unproven approach.

- **Version-specific menu paths:** Research documented v21 vs v22+ menu reorganization but may not be exhaustive across all menus. Build version-aware menu path registry during Phase 1 implementation and expand as needed.

- **OCR accuracy thresholds:** Research recommends OCR fallback for custom-drawn controls but doesn't specify acceptable accuracy rates or preprocessing strategies for P6's fonts. Tune during Phase 1 when first encountering inaccessible controls.

- **Database lock timing:** Research warns about GUI/DB dual-access conflicts but doesn't specify exact wait times after GUI writes. Measure empirically during Phase 2 to determine safe post-write delays.

All gaps are addressable through implementation-phase research, sandbox testing, or empirical measurement. No blockers identified.

## Sources

### Primary (HIGH confidence)
- **pywinauto Documentation** — Getting started, backend selection, wait strategies, timeout patterns
- **Microsoft UI Automation Overview** — UIA architecture, control patterns, accessibility tree structure
- **Oracle P6 v22.12/v23 Release Notes** — Version-specific feature availability, UI changes, new capabilities
- **Existing codebase** (src/automation/*.py) — Validated implementations of P6ProjectManager, P6LayoutManager, P6ActivityManager, P6ScheduleManager, P6PrintManager, P6ExportManager, P6BatchProcessor

### Secondary (MEDIUM confidence)
- **Automating Windows GUIs with Pywinauto: A Practical Guide** (Medium article) — Hybrid backend strategy, Java app challenges
- **Java Application Automation with Python** (comp.lang.python discussion) — Dynamic control ID issues, Java Access Bridge approach
- **OCR in UI Test Automation** (SmartBear) — When OCR becomes necessary, fallback patterns
- **Retry Pattern - Azure Architecture** — Exponential backoff, circuit breaker, adaptive timeouts
- **Top 10 Windows Desktop Automation Tools** (AskUI) — RPA alternatives comparison, pywinauto positioning

### Tertiary (LOW confidence)
- **GUI Architectures** (Martin Fowler) — Layered architecture patterns, command pattern application
- **Decomposing High-Complexity UI Automation** (Ensolvers) — Component architecture for complex workflows
- **Application Design Patterns: State Machines** (NI) — State tracking patterns for GUI automation

---
*Research completed: 2026-02-07*
*Ready for roadmap: yes*
