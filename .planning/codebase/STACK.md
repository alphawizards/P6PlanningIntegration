# Technology Stack

**Analysis Date:** 2026-02-07

## Languages

**Primary:**
- Python 3.11.9 - Core application, automation, AI agent, data processing

## Runtime

**Environment:**
- Python 3.11.9 with virtual environment support

**Package Manager:**
- pip - Python package management
- Lockfile: requirements.txt (present)

## Frameworks

**Core:**
- litellm 1.0.0+ - Unified LLM provider abstraction layer supporting Claude, OpenAI, Gemini with function calling

**Data Processing:**
- pandas 2.0.0+ - DataFrames for schedule analysis, activity/relationship data manipulation
- openpyxl 3.0.0+ - Excel file reading/writing for schedule imports and reports

**File Handling:**
- python-dotenv 1.0.0+ - Environment variable management from .env files

**GUI Automation:**
- pywinauto 0.6.8+ - Windows GUI automation for P6 Professional (primary automation engine)
- pyautogui 0.9.54+ - Fallback GUI automation for keyboard/mouse input
- psutil 5.9.0+ - Process detection and management for P6 instances

**PDF Generation:**
- reportlab 4.0.0+ - PDF generation for data reports and schedule exports
- pillow 10.0.0+ - Image handling and processing for PDF generation

**Database:**
- sqlite3 (standard library) - Native SQLite support for P6 Professional standalone databases
- JPype 1.4.1+ - Java interop for P6 Integration API (Java Object Wrapper)

## Key Dependencies

**Critical:**
- litellm 1.0.0+ - Core AI integration layer; supports multi-provider LLM calls (Claude, OpenAI, Gemini)
- JPype1 1.4.1+ - Java bridge for P6 Integration API access (enterprise mode); allows direct API calls to P6 services
- pandas 2.0.0+ - Data transformation and analysis for schedule analytics
- pywinauto 0.6.8+ - Windows automation driver for P6 Professional GUI interaction

**Testing & Development:**
- pytest 7.0.0+ - Test framework
- pytest-cov 4.0.0+ - Coverage reporting for unit and integration tests
- pylint 2.17.0+ - Code linting and quality analysis

## Configuration

**Environment:**
- Configuration loaded via `src/config/settings.py` from .env file
- Fail-fast validation on startup for required variables

**Key Environment Variables:**
- `P6_CONNECTION_MODE` - 'SQLITE' (standalone) or 'JAVA' (enterprise)
- `P6_DB_PATH` - Path to P6 SQLite database (standalone mode)
- `P6_LIB_DIR` - Path to P6 Integration API JAR files (enterprise mode)
- `P6_DB_TYPE` - 'standalone' or 'enterprise'
- `P6_USER`, `P6_PASS` - P6 authentication credentials
- `LLM_PROVIDER` - 'anthropic', 'openai', or 'gemini'
- `LLM_API_KEY` - API key for selected LLM provider
- `LLM_MODEL` - Model identifier (defaults: claude-3-5-sonnet, gpt-4-turbo, gemini-1.5-pro)
- `SAFE_MODE` - 'true' enables read-only protection (default)
- `LOG_LEVEL` - Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**Build:**
- No build configuration (pure Python, no compilation)
- pytest.ini for test configuration at `pytest.ini`

## Platform Requirements

**Development:**
- Windows 10/11 (P6 Professional is Windows-only)
- Python 3.11+
- Access to P6 Professional installation (GUI automation requires running P6)
- Optional: Java Runtime Environment (JRE) for P6 Integration API mode

**Production:**
- Windows 10/11 for P6 GUI automation features
- Primavera P6 Professional 24.x or Integration API compatible version
- Python 3.11+ runtime
- Database: SQLite (standalone) or Oracle Database (enterprise)
- LLM Provider account (Anthropic, OpenAI, or Google Cloud)

**Deployment Target:**
- Local Windows workstations running P6 Professional
- Windows servers for headless data processing (SQLite/Integration API modes)

---

*Stack analysis: 2026-02-07*
