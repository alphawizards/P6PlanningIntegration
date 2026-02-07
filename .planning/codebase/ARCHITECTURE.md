# Architecture

**Analysis Date:** 2026-02-07

## Pattern Overview

**Overall:** Multi-layer modular architecture with dual-mode backend support and pluggable AI integration.

**Key Characteristics:**
- Two connection modes: SQLite (P6 Professional Standalone) and Java/JPype (P6 Integration API)
- Layered architecture: Config → Core → DAO → Business Logic → AI/Automation → Reporting
- Plugin-based parser system for multiple schedule file formats (XER, XML, MPX)
- ReAct pattern for AI agent with tool execution and conversation history
- GUI automation layer for P6 Professional desktop application

## Layers

**Configuration Layer:**
- Purpose: Centralize environment variables, feature flags, and deployment settings
- Location: `src/config/settings.py`
- Contains: Database credentials, P6 paths, logging setup, connection mode selection
- Depends on: Environment variables, .env file
- Used by: All other layers via conditional imports

**Core Definitions Layer:**
- Purpose: Define immutable P6 schema (field names) and session management
- Location: `src/core/definitions.py`, `src/core/session.py`
- Contains: PROJECT_FIELDS, ACTIVITY_FIELDS, RESOURCE_FIELDS, RELATIONSHIP_FIELDS constants; JVM/JPype session lifecycle
- Depends on: JPype (Java mode only), P6 libraries
- Used by: DAO layer, parsers, validators

**Data Access Layer (DAO):**
- Purpose: Abstract database reads/writes from application logic
- Location: `src/dao/`
- Contains:
  - Java mode: `project_dao.py`, `activity_dao.py`, `relationship_dao.py` (JPype-based)
  - SQLite mode: `sqlite/sqlite_manager.py`, `sqlite/project_dao.py`, `sqlite/activity_dao.py`, `sqlite/relationship_dao.py`
- Depends on: Core definitions, connection mode
- Used by: AI tools, analyzers, reporting

**Ingestion Layer (Parsers):**
- Purpose: Convert multiple schedule formats into standardized DataFrames
- Location: `src/ingestion/base.py`, `src/ingestion/xer_parser.py`, `src/ingestion/xml_parser.py`, `src/ingestion/mpx_parser.py`
- Contains: Abstract ScheduleParser base class; format-specific parsers
- Depends on: pandas, core definitions
- Used by: main.py test functions, CI/CD workflows

**Analysis Layer:**
- Purpose: Compute schedule metrics and insights
- Location: `src/analyzers/schedule_analyzer.py`, `src/analyzers/critical_path_analyzer.py`, `src/analyzers/progress_tracker.py`
- Contains: ScheduleAnalyzer (main), critical path computation, progress calculations
- Depends on: pandas, DAO layer
- Used by: Reporting layer, AI tools

**Reporting Layer:**
- Purpose: Export data and generate AI context
- Location: `src/reporting/exporters.py`, `src/reporting/generators.py`
- Contains: DataExporter (CSV/Excel/JSON), ContextGenerator (project summaries for AI)
- Depends on: pandas, DAO layer, analysis layer
- Used by: AI agent, main.py

**AI Agent Layer:**
- Purpose: Natural language interaction and ReAct loop execution
- Location: `src/ai/agent.py`, `src/ai/tools.py`, `src/ai/llm_client.py`, `src/ai/prompts.py`
- Contains: P6Agent (ReAct loop), P6Tools (DAO wrappers), LLMClient (Claude API), system prompts
- Depends on: DAO layer, reporting layer, anthropic SDK
- Used by: main.py, external scripts

**Automation Layer (GUI):**
- Purpose: Control P6 Professional desktop application via pywinauto
- Location: `src/automation/`
- Contains:
  - Base: `base.py` (connection, window management)
  - Managers: `projects.py`, `layouts.py`, `scheduling.py`, `activities.py`, `printing.py`, `exporting.py`
  - Orchestration: `batch.py` (batch processing), `agent.py` (agent interface)
  - Support: `connection.py` (detect/start P6), `navigation.py` (UI navigation), `utils.py` (retries, waits)
- Depends on: pywinauto, config layer
- Used by: main.py, automation tests

**Utilities Layer:**
- Purpose: Cross-cutting concerns (logging, file I/O, type conversion)
- Location: `src/utils/logger.py`, `src/utils/file_manager.py`, `src/utils/converters.py`
- Contains: Logging setup, directory management, Java↔Python type conversion
- Depends on: Standard library, JPype (converters only)
- Used by: All layers

## Data Flow

**File Ingestion Flow:**

1. `main.py` receives file path (XER/XML/MPX)
2. Detects format by extension
3. Instantiates appropriate parser (`XERParser`, `UnifiedXMLParser`, `MPXParser`)
4. Parser reads file, maps columns to core definitions (PROJECT_FIELDS, ACTIVITY_FIELDS, etc.)
5. Returns dict with `projects`, `activities`, `relationships` DataFrames
6. DataExporter exports results to CSV/Excel/JSON

**Database Read Flow:**

1. Application initializes connection mode from config (`P6_CONNECTION_MODE`)
2. If JAVA mode: P6Session starts JVM, connects via P6 Integration API
3. If SQLITE mode: SQLiteManager connects to P6 database file
4. DAO layer (ProjectDAO, ActivityDAO, RelationshipDAO) queries entities
5. Results converted to standardized format via core definitions
6. Returned as DataFrames or JSON

**AI Agent Interaction Flow:**

1. User input → P6Agent.interact()
2. Agent loads project context via P6Tools.get_project_context()
3. User query + context + tool schemas → LLMClient.call_claude()
4. LLM returns tool call (e.g., search_activities)
5. Agent executes tool via P6Tools wrapper → DAO operations
6. Tool results appended to conversation history
7. Tool results + LLM response → LLMClient.call_claude()
8. LLM generates natural language answer
9. Returned to user

**GUI Automation Flow:**

1. P6AutomationBase.start_p6() detects/launches P6 Professional
2. Specialized managers (P6ProjectManager, P6LayoutManager, etc.) navigate UI via pywinauto
3. Batch operations queued in P6BatchProcessor
4. Each action wrapped in retry logic with wait conditions
5. Screenshots captured for debugging
6. Results aggregated in BatchSummary

**State Management:**

- P6Session manages JVM lifecycle (singleton pattern in main.py)
- P6Agent maintains conversation_history list and context dict
- SQLiteManager maintains connection pool
- GUI automation maintains Application instance for window control
- Batch processor maintains queue and status tracking

## Key Abstractions

**ScheduleParser:**
- Purpose: Standardize multi-format schedule parsing
- Examples: `src/ingestion/xer_parser.py`, `src/ingestion/xml_parser.py`, `src/ingestion/mpx_parser.py`
- Pattern: Abstract base class with parse() returning standardized DataFrame dict

**DAO Pattern:**
- Purpose: Abstract data access behind consistent interface
- Examples: `src/dao/project_dao.py`, `src/dao/sqlite/project_dao.py`
- Pattern: Parallel implementations (Java and SQLite) with identical public APIs

**P6Tools:**
- Purpose: Wrap DAO operations for AI consumption
- Location: `src/ai/tools.py`
- Pattern: Methods return JSON/text; schema definitions for LLM function calling

**P6AutomationBase:**
- Purpose: Provide shared window management and connection logic
- Location: `src/automation/base.py`
- Pattern: Base class extended by specialized managers (ProjectManager, LayoutManager, etc.)

**ReAct Loop:**
- Purpose: Implement agentic reasoning with tool execution
- Location: `src/ai/agent.py` (P6Agent class)
- Pattern: User → LLM → Tool → History → LLM → Response cycle

## Entry Points

**main.py:**
- Location: `c:/Users/ckr_4/01 Projects/P6PlanningIntegration/main.py`
- Triggers: CLI invocation with subcommands (test-db, test-ingestion, etc.)
- Responsibilities:
  - Initialize connection (mode-specific)
  - Route to test/operation functions
  - Handle top-level exceptions
  - Log execution flow

**test_database_connection():**
- Location: `main.py` (lines ~128+)
- Triggers: `python main.py test-db`
- Responsibilities:
  - Test connection (JAVA or SQLITE mode)
  - Query projects/activities/relationships
  - Display results
  - Verify schema alignment

**test_file_ingestion():**
- Location: `main.py` (lines ~34+)
- Triggers: `python main.py test-ingestion <filepath>`
- Responsibilities:
  - Parse schedule file (auto-detect format)
  - Validate schema
  - Display project/activity/relationship counts

**P6Agent Initialization:**
- Location: `src/ai/agent.py` (P6Agent.__init__)
- Triggers: Called by application requiring AI interaction
- Responsibilities:
  - Accept P6Session
  - Initialize LLMClient (if AI enabled)
  - Load project context
  - Prepare for conversation loop

**P6AutomationBase.start_p6():**
- Location: `src/automation/base.py`
- Triggers: Before any GUI automation
- Responsibilities:
  - Detect P6 installation
  - Launch executable
  - Wait for main window
  - Initialize connection to UI

## Error Handling

**Strategy:** Layered exceptions with context preservation and graceful fallbacks.

**Patterns:**

- **Configuration errors:** Logged and bail early (main.py, src/config/settings.py)
- **Connection errors:** Caught in P6Session.__enter__, mode-specific handling in main.py
- **Parser errors:** Caught in ScheduleParser subclasses, re-raised with file context
- **DAO errors:** Propagated from JPype/SQLite with query context via log_exception()
- **AI errors:** Logged in LLMClient, fallback to mock mode if API fails
- **Automation errors:** Caught in P6AutomationBase methods, retries via retry() decorator, final exception: P6AutomationError or subclass
- **Batch errors:** Individual action failures captured in BatchResult; batch continues

**Log Levels:**

- ERROR: Connection failures, parse failures, API errors
- WARNING: Fallback modes (AI disabled, retry attempts)
- INFO: Operation start/end, context loading, tool execution
- DEBUG: Field mappings, query parameters (not implemented but structure ready)

## Cross-Cutting Concerns

**Logging:**
- Framework: Python logging configured in `src/utils/logger.py`
- Usage: All modules import `logger` and call logger.info/warning/error
- Sanitization: log_exception() helper prevents secrets in logs

**Validation:**
- Field validation: core/definitions.py defines mandatory fields
- Schema validation: parsers validate input DataFrames match definitions
- Connection validation: P6Session raises exception if connection fails

**Authentication:**
- Java mode: P6_USER, P6_PASS via P6Session
- SQLite mode: DB_USER, DB_PASS (Oracle) via SQLiteManager
- AI: Anthropic API key via environment (no explicit auth layer)

**Type Conversion:**
- Java↔Python: src/utils/converters.py (java_date_to_python, p6_objects_to_dict_list, etc.)
- Conditional import: Only available in JAVA mode (checked at module load)
- Fallback: SQLite mode uses native Python types

---

*Architecture analysis: 2026-02-07*
