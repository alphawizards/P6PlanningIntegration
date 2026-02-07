# Codebase Structure

**Analysis Date:** 2026-02-07

## Directory Layout

```
P6PlanningIntegration/
├── .claude/                    # Claude agent configurations and skills
│   ├── agents/                 # Agent definitions
│   └── skills/                 # Skills including code-reviewer, p6-project-controls, docx, xlsx
├── .github/                    # GitHub workflows (CI/CD)
├── .planning/                  # GSD planning artifacts
│   └── codebase/               # Codebase analysis documents (this directory)
├── src/                        # Main application source code
│   ├── __init__.py             # Package marker
│   ├── ai/                     # AI agent and LLM integration
│   ├── analyzers/              # Schedule analysis and metrics
│   ├── automation/             # P6 Professional GUI automation (pywinauto)
│   ├── config/                 # Configuration and settings
│   ├── core/                   # Core definitions and session management
│   ├── dao/                    # Data access objects (DAO pattern)
│   │   └── sqlite/             # SQLite-specific DAO implementations
│   ├── ingestion/              # Schedule file parsers (XER, XML, MPX)
│   ├── reporting/              # Data export and context generation
│   └── utils/                  # Cross-cutting utilities
├── tests/                      # Unit and integration tests
├── directives/                 # Prompt directives for AI
├── execution/                  # Execution logs and outputs (generated)
├── scripts/                    # Standalone scripts and utilities
├── docs/                       # Documentation
├── main.py                     # CLI entry point
├── .env.example                # Environment variables template
├── Dockerfile                  # Container configuration
├── .pylintrc                   # Python linting configuration
├── AGENTS.md                   # Agent configuration documentation
└── PHASE_*.md                  # Phase summaries (analysis/planning artifacts)
```

## Directory Purposes

**src/ai:**
- Purpose: Natural language interaction with P6 via Claude API
- Contains: Agent implementation (ReAct loop), LLM client, tool definitions, prompts
- Key files: `agent.py` (main agent), `llm_client.py` (Claude API wrapper), `tools.py` (DAO-wrapped tools), `prompts.py` (system messages)

**src/analyzers:**
- Purpose: Compute schedule metrics and insights
- Contains: Schedule analysis, critical path detection, progress tracking
- Key files: `schedule_analyzer.py` (main analyzer), `critical_path_analyzer.py`, `progress_tracker.py`

**src/automation:**
- Purpose: GUI control of P6 Professional desktop application
- Contains: Window management, project/activity/schedule operations, printing/exporting, batch processing
- Key files: `base.py` (foundation), `agent.py` (agent interface), `batch.py` (batch operations), `connection.py` (launch/detect)

**src/config:**
- Purpose: Centralized configuration and environment management
- Contains: Settings from environment variables, connection mode selection, path initialization
- Key files: `settings.py` (all configuration)

**src/core:**
- Purpose: Schema definitions and session lifecycle
- Contains: Immutable field definitions for P6 entities, JVM session management
- Key files: `definitions.py` (field constants), `session.py` (P6Session class)

**src/dao:**
- Purpose: Data access abstraction with dual-mode support
- Contains: Java mode (JPype-based) and SQLite mode implementations
- Key files:
  - Java mode: `project_dao.py`, `activity_dao.py`, `relationship_dao.py`
  - SQLite mode: `sqlite/sqlite_manager.py`, `sqlite/project_dao.py`, `sqlite/activity_dao.py`, `sqlite/relationship_dao.py`

**src/dao/sqlite:**
- Purpose: SQLite-specific data access for P6 Professional standalone
- Contains: SQLite connection management, query builders, bulk write operations
- Key files: `sqlite_manager.py` (connection), `project_dao.py`, `activity_dao.py`, `relationship_dao.py`, `bulk_writer.py`

**src/ingestion:**
- Purpose: Parse multiple schedule file formats into standardized schema
- Contains: XER parser (Primavera), XML parser (P6/MS Project), MPX parser (Microsoft Project)
- Key files: `base.py` (abstract ScheduleParser), `xer_parser.py`, `xml_parser.py`, `mpx_parser.py`

**src/reporting:**
- Purpose: Export data and generate AI context
- Contains: Data exporters (CSV/Excel/JSON), context generators for AI
- Key files: `exporters.py` (DataExporter class), `generators.py` (ContextGenerator class)

**src/utils:**
- Purpose: Cross-cutting utilities and helpers
- Contains: Logging setup, file management, type conversion (Java↔Python)
- Key files: `logger.py` (logging), `file_manager.py` (directories/paths), `converters.py` (JPype conversion)

**tests:**
- Purpose: Unit and integration tests
- Contains: DAO tests, automation tests, analyzer tests
- Key files: `conftest.py` (pytest fixtures), `test_*.py` (test modules)

**scripts:**
- Purpose: Standalone utility scripts
- Contains: Test scripts (Gemini API, etc.), analysis scripts
- Key files: `test_gemini.py`, `test_gemini_native.py`

**directives:**
- Purpose: Prompt engineering artifacts for AI agent behavior
- Contains: System prompts, behavior guidelines
- Generated by: GSD planning phase

**execution:**
- Purpose: Runtime logs and generated artifacts
- Contains: Execution logs, batch results, exported data
- Generated at: Runtime, not committed

**docs:**
- Purpose: Project documentation
- Contains: README, setup guides, API documentation

## Key File Locations

**Entry Points:**
- `main.py`: CLI interface with subcommands (test-db, test-ingestion, etc.)
- `src/ai/agent.py` (P6Agent): Core AI agent for natural language interaction
- `src/automation/base.py` (P6AutomationBase.start_p6()): GUI automation initiation

**Configuration:**
- `src/config/settings.py`: All environment variables and settings
- `.env.example`: Template for required environment variables
- `src/core/definitions.py`: P6 schema field definitions (PROJECT_FIELDS, ACTIVITY_FIELDS, etc.)

**Core Logic:**
- `src/core/session.py`: P6Session (JVM and database connection lifecycle)
- `src/dao/project_dao.py`: Project queries (Java mode)
- `src/dao/sqlite/project_dao.py`: Project queries (SQLite mode)
- `src/ai/llm_client.py`: Anthropic Claude API client
- `src/ingestion/base.py`: Abstract ScheduleParser base class

**Testing:**
- `tests/conftest.py`: Pytest fixtures and mocking setup
- `tests/test_activity_dao.py`: DAO layer tests
- `tests/test_automation_e2e.py`: End-to-end automation tests
- `tests/test_schedule_analyzer.py`: Analyzer tests

## Naming Conventions

**Files:**

- `*_dao.py`: Data access object implementations
- `*_analyzer.py`: Analysis and computation modules
- `*_manager.py`: Manager classes for subsystems (P6ProjectManager, P6LayoutManager, etc.)
- `*_parser.py`: Schedule file parsers
- `test_*.py`: Test files (pytest convention)
- `main.py`: CLI entry point
- `base.py`: Abstract base classes (e.g., P6AutomationBase)

**Directories:**

- `src/`: Main source code (Python convention)
- `tests/`: Test files (pytest convention)
- `sqlite/`: SQLite-specific implementations (nested under dao/)
- `schemas/`: Data schemas and validation (nested under skills/docx/)
- `references/`: Reference documentation (nested under skills/)

**Classes:**

- `P6*`: P6-related classes (P6Agent, P6Session, P6AutomationBase, P6ProjectManager, etc.)
- `*DAO`: Data access object classes (ProjectDAO, ActivityDAO, SQLiteProjectDAO, etc.)
- `*Manager`: Manager/orchestrator classes (P6ConnectionManager, P6ProjectManager, P6BatchProcessor, etc.)
- `*Analyzer`: Analysis classes (ScheduleAnalyzer, CriticalPathAnalyzer, ProgressTracker)
- `*Parser`: Parser classes (XERParser, UnifiedXMLParser, MPXParser, ScheduleParser base)

**Functions:**

- Snake_case for all functions (Python convention)
- `test_*`: Test functions (pytest convention)
- `get_*`: Query/accessor functions
- `create_*`: Factory functions
- `is_*`, `has_*`: Boolean predicates

## Where to Add New Code

**New Feature (e.g., resource leveling endpoint):**
- Primary code: `src/analyzers/` (analysis logic) or `src/automation/` (GUI operations)
- DAO queries: Add methods to `src/dao/project_dao.py` and `src/dao/sqlite/project_dao.py`
- AI integration: Add tool schema to `src/ai/tools.py` and P6Tools method
- Tests: `tests/test_resource_leveler.py` or extend `tests/test_automation_e2e.py`
- Export: Add method to `src/reporting/exporters.py` if generating reports

**New Schedule File Format:**
- Parser: Create `src/ingestion/yourformat_parser.py` extending `src/ingestion/base.py`
- Integration: Import in `src/ingestion/__init__.py` and main.py test function
- Tests: Add test case to `tests/test_ingestion.py` (if exists) or create new file

**New Analyzer/Metric:**
- Implementation: `src/analyzers/your_analyzer.py`
- Export logic: `src/reporting/generators.py` (if generating context)
- Integration: Called from main.py or AI tools

**New GUI Automation:**
- Base implementation: Extend `src/automation/base.py` or create in `src/automation/your_manager.py`
- Agent integration: Add ActionType enum value in `src/automation/agent.py`
- Batch support: Register in `src/automation/batch.py`

**New Configuration:**
- Setting definition: `src/config/settings.py`
- Export from: `src/config/__init__.py`
- Documentation: `.env.example`

**Utilities:**
- File/directory helpers: `src/utils/file_manager.py`
- Type conversion: `src/utils/converters.py`
- Logging: `src/utils/logger.py`
- New concern: Create new file `src/utils/your_util.py` and export from `src/utils/__init__.py`

## Special Directories

**src/dao/sqlite:**
- Purpose: SQLite-specific DAO implementations for P6 Professional standalone
- Generated: No (source code)
- Committed: Yes
- Contains: Parallel implementations of project_dao.py, activity_dao.py, relationship_dao.py, plus sqlite_manager.py, bulk_writer.py, schema_validator.py

**execution:**
- Purpose: Runtime outputs (logs, exported files, batch results)
- Generated: Yes (at runtime)
- Committed: No (in .gitignore)
- Cleanup: Use src/utils/cleanup_old_exports() or manual deletion

**tests:**
- Purpose: Unit and integration tests
- Generated: No (source code)
- Committed: Yes
- Coverage: Covers DAO layer, analyzers, automation basics

**.claude/skills:**
- Purpose: Reusable Claude skills and instructions
- Generated: No (manually crafted)
- Committed: Yes
- Used by: Claude agent for code review, document parsing, project controls

**.planning/codebase:**
- Purpose: GSD codebase analysis documents (ARCHITECTURE.md, STRUCTURE.md, etc.)
- Generated: Yes (by /gsd:map-codebase)
- Committed: Yes
- Used by: /gsd:plan-phase and /gsd:execute-phase

---

*Structure analysis: 2026-02-07*
