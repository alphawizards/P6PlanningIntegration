# External Integrations

**Analysis Date:** 2026-02-07

## APIs & External Services

**Large Language Model (LLM) Providers:**
- **Anthropic Claude** - AI agent backbone for natural language P6 schedule analysis
  - SDK/Client: litellm 1.0.0+
  - Auth: Environment variable `LLM_API_KEY`
  - Configuration: `src/config/settings.py` (line 145-170)
  - Models supported: claude-3-5-sonnet-20241022, claude-3-opus-20240229, claude-3-haiku-20240307
  - Implementation: `src/ai/llm_client.py` LLMClient class handles completion requests with function calling

- **OpenAI GPT** - Alternative LLM provider
  - SDK/Client: litellm 1.0.0+
  - Auth: Environment variable `LLM_API_KEY`
  - Models supported: gpt-4-turbo-preview, gpt-4, gpt-3.5-turbo
  - Implementation: Abstracted through litellm to support provider swapping

- **Google Gemini** - Alternative LLM provider with native SDK fallback
  - SDK/Client: litellm 1.0.0+ (primary) or google-generativeai (fallback)
  - Auth: Environment variable `LLM_API_KEY`
  - Models supported: gemini-1.5-pro, gemini-1.5-flash
  - Implementation: Native Gemini fallback at `src/ai/llm_client.py` lines 265-325 (_chat_native_gemini method)

## Data Storage

**Databases:**
- **SQLite** (P6 Professional Standalone)
  - Client: sqlite3 (Python standard library)
  - Connection: Direct file-based connection to P6 database (immutable mode for safety)
  - Read-Only: Yes - IMMUTABLE URI flag prevents writes and lock file creation
  - Location: `src/dao/sqlite/sqlite_manager.py` manages SQLite connections
  - DAO Abstraction: `src/dao/sqlite/` directory contains SQLiteManager, SQLiteActivityDAO, SQLiteProjectDAO, SQLiteRelationshipDAO

- **Oracle Database** (P6 Integration API - Enterprise)
  - Client: JPype 1.4.1+ bridges to Java P6 Integration API
  - Connection: Via P6 Integration API using credentials from environment variables
  - Auth: `DB_USER`, `DB_PASS`, `DB_INSTANCE` environment variables
  - DAO Abstraction: `src/dao/project_dao.py`, `src/dao/activity_dao.py`, `src/dao/relationship_dao.py` support both SQLite and Oracle modes

**File Storage:**
- Local filesystem only
- PDF output directory: `reports/pdf/` (configurable via `PDF_OUTPUT_DIR`)
- Schedule file imports: XER, XML, MPX formats parsed into memory (no persistence layer)

**Caching:**
- None - All data retrieved fresh from P6 database on each request

## Authentication & Identity

**Auth Provider:**
- Custom (built-in)
  - P6 Authentication: Username/password stored in `P6_USER`, `P6_PASS` environment variables
  - Database Authentication: For enterprise Oracle mode, `DB_USER`/`DB_PASS` environment variables
  - LLM Authentication: API keys in `LLM_API_KEY` environment variable specific to provider
  - Implementation: `src/config/settings.py` loads and validates all credentials with fail-fast validation

## Monitoring & Observability

**Error Tracking:**
- None - Application logs only

**Logs:**
- File-based logging to `logs/app.log`
- Level configurable via `LOG_LEVEL` environment variable
- Implementation: `src/utils/logger.py` provides centralized logging
- Exception handling: Comprehensive try-catch with context logging via `log_exception()` helper

## CI/CD & Deployment

**Hosting:**
- None - Standalone desktop/workstation application for Windows

**CI Pipeline:**
- None detected - No automated deployment pipeline

**Testing:**
- Local pytest execution via `pytest.ini`
- Test directory: `tests/`
- Markers: Integration tests marked with `@pytest.mark.integration` for database-dependent tests

## Environment Configuration

**Required env vars:**
- `P6_CONNECTION_MODE` - Determines database access strategy (SQLITE or JAVA)
- `P6_DB_PATH` - SQLite database path (required for SQLITE mode)
- `P6_LIB_DIR` - P6 Integration API JAR directory (required for JAVA mode)
- `P6_USER` - P6 user account for authentication
- `P6_PASS` - P6 account password
- `LLM_API_KEY` - API key for configured LLM provider
- `LLM_PROVIDER` - Which LLM to use (anthropic, openai, gemini)

**Optional env vars:**
- `P6_DB_TYPE` - 'standalone' (default) or 'enterprise'
- `DB_USER`, `DB_PASS`, `DB_INSTANCE` - Oracle credentials for enterprise mode
- `LLM_MODEL` - Model identifier (defaults by provider)
- `LLM_TEMPERATURE` - Response creativity (0.0-1.0, default 0.0 for deterministic)
- `LLM_MAX_TOKENS` - Response length limit (default 4096)
- `SAFE_MODE` - Prevents write operations (default true)
- `LOG_LEVEL` - Logging verbosity (default INFO)
- `P6_EXECUTABLE_PATH` - P6 installation path for GUI automation (Windows only)
- `PDF_PRINTER_NAME` - Windows printer for PDF export (default "Microsoft Print to PDF")
- `PDF_OUTPUT_DIR` - PDF report output directory (default "reports/pdf")

**Secrets location:**
- Environment variables via `.env` file (not committed to git)
- Configuration validation: `src/config/settings.py` enforces all required vars present at startup

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Schedule File Formats (Import Only)

**XER Format (Primavera P6):**
- Parser: `src/ingestion/xer_parser.py` class XERParser
- Supports: Tab-separated format with %T (table) and %F (field) markers
- Extracts: PROJECT, TASK, TASKPRED tables into normalized DataFrames

**XML Format (P6 or MS Project):**
- Parser: `src/ingestion/xml_parser.py` class UnifiedXMLParser
- Supports: Generic XML schedule format compatible with P6 and MS Project exports

**MPX Format (Microsoft Project):**
- Parser: `src/ingestion/mpx_parser.py` class MPXParser
- Supports: Microsoft Project Exchange format for legacy schedule data

---

*Integration audit: 2026-02-07*
