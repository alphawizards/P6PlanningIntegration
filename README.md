# P6 Planning Integration

A comprehensive Python platform for Oracle Primavera P6 Professional with full GUI automation, voice-driven control, PDF reporting, SQLite database access, and AI agent integration.

---

## All 7 Phases Complete ✅

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Foundation | ✅ |
| 2 | Connection & Navigation | ✅ |
| 3 | Printing & Export | ✅ |
| 4 | Project & Layout Management | ✅ |
| 5 | Scheduling & Data Operations | ✅ |
| 6 | Batch Operations | ✅ |
| 7 | AI Agent Integration | ✅ |

---

## What The Project Can Do

### 1. GUI Automation
Automate Oracle Primavera P6 Professional through keyboard/mouse control using pywinauto:
- Open/close projects, apply layouts, switch views
- Select and edit activities with column navigation
- Set constraints, update durations, add/delete activities
- Run F9 scheduling, resource leveling, schedule checking
- Export to PDF, XER, XML, Excel
- Batch operations across multiple projects

### 2. Voice-Driven Control (Whisper)
Control P6 using voice commands through a floating overlay window:
- Push-to-talk voice recording
- Local Whisper transcription (no cloud API)
- Real-time status feedback
- Natural language commands like "Select activity A1010" or "Change duration to 10 days"

### 3. SQLite Database Access
Read-only access to P6 Professional Standalone databases:
- Immutable mode for safe reading from protected directories
- Query projects, activities, and relationships
- Duration conversion (hours to days)
- Schema validation and mapping

### 4. Summary Schedule Generation
Convert Excel WBS data to P6 XER format:
- Template-based generation preserving P6 settings
- Automatic filtering and date handling
- Direct import into Primavera P6

### 5. AI Agent Integration
LLM-powered automation with function calling:
- 12 GUI tools for activity manipulation
- System prompts for GUI agent behavior
- OpenAI and Anthropic format support
- Safe mode compliance

---

## Key Folders

```
P6PlanningIntegration/
├── src/                          # Main source code
│   ├── automation/               # 15 GUI automation modules
│   ├── ai/                       # AI agent, LLM client, tools, prompts
│   ├── dao/                      # Data access objects
│   │   └── sqlite/               # SQLite DAO for P6 Standalone
│   ├── analyzers/                # Schedule analysis
│   ├── config/                   # Configuration management
│   ├── core/                     # Core utilities
│   ├── ingestion/                # Data ingestion
│   ├── reporting/                # PDF and report generation
│   └── utils/                    # Shared utilities
├── P6 GUI Automation/            # Voice-driven GUI agent
│   ├── src/automation/           # Enhanced activity manager
│   ├── src/ai/                   # GUI tools for LLM
│   ├── src/gui/                  # Overlay window & Whisper handler
│   └── main.py                   # Entry point
├── summary_schedule_generator/   # Excel to XER conversion
│   ├── scripts/                  # Generator script
│   ├── templates/                # XER templates
│   ├── input/                    # Excel input files
│   └── output/                   # Generated XER files
├── .claude/skills/               # AI skill definitions
│   ├── p6-gui-automation/        # P6 GUI automation skill
│   ├── p6-project-controls/      # P6 project controls skill
│   └── skill-creator/            # Skill creation utilities
├── directives/                   # Standard operating procedures
├── execution/                    # Deterministic Python scripts
├── docs/                         # Documentation
├── tests/                        # Test files
└── logs/                         # Application logs
```

---

## Key Files

### Core Automation (`src/automation/`)
| File | Class | Purpose |
|------|-------|---------|
| `base.py` | `P6AutomationBase` | Connection/window management |
| `connection.py` | `P6ConnectionManager` | Process detection, login |
| `navigation.py` | `P6Navigator` | Menu, toolbar, status bar |
| `printing.py` | `P6PrintManager` | Print preview, PDF export |
| `exporting.py` | `P6ExportManager` | XER, XML, Excel export |
| `projects.py` | `P6ProjectManager` | Project tree, open/close |
| `layouts.py` | `P6LayoutManager` | Layouts, views, filters |
| `scheduling.py` | `P6ScheduleManager`, `P6BaselineManager` | F9, leveling, baselines |
| `activities.py` | `P6ActivityManager` | Activity select/edit |
| `batch.py` | `P6BatchProcessor` | Batch operations |
| `agent.py` | `P6AgentInterface` | AI agent integration |

### AI Integration (`src/ai/`)
| File | Purpose |
|------|---------|
| `agent.py` | P6 AI agent with chat interface |
| `tools.py` | Tool definitions for LLM function calling |
| `llm_client.py` | OpenAI/Anthropic client wrapper |
| `prompts.py` | System and user prompts |

### Voice Agent (`P6 GUI Automation/`)
| File | Purpose |
|------|---------|
| `main.py` | Entry point with CLI args |
| `src/gui/overlay.py` | Tkinter overlay window |
| `src/gui/whisper_handler.py` | Whisper transcription |
| `src/ai/gui_tools.py` | 12 GUI tools for LLM |
| `src/automation/activities.py` | Enhanced column navigation |

### Data Access (`src/dao/`)
| File | Purpose |
|------|---------|
| `activity_dao.py` | Activity queries |
| `project_dao.py` | Project queries |
| `relationship_dao.py` | Relationship queries |
| `sqlite/` | SQLite DAO for P6 Standalone |

---

## Quick Start

### GUI Automation
```python
from src.automation import P6PrintAutomation

with P6PrintAutomation() as p6:
    p6.open_project("My Project")
    p6.apply_layout("Monthly Report")
    p6.print_to_pdf("report.pdf")
```

### Voice Agent
```bash
cd "P6 GUI Automation"
pip install -r requirements.txt
python main.py --safe-mode      # Safe mode (no edits)
python main.py --unsafe         # Allow edits
```

### Summary Schedule Generator
```bash
cd summary_schedule_generator/scripts
python generate_summary_schedule.py
```

### SQLite DAO
```python
from src.dao.sqlite import SQLiteManager

with SQLiteManager() as manager:
    project_dao = manager.get_project_dao()
    projects = project_dao.get_all_projects()
```

---

## Configuration

```env
# P6 Settings
P6_EXECUTABLE_PATH=C:\Program Files\Oracle\Primavera P6\PM.exe
P6_WINDOW_PATTERN=.*Primavera P6.*

# Database (SQLite mode)
P6_CONNECTION_MODE=SQLITE
P6_DB_PATH=C:\Program Files\Oracle\Primavera P6\...\Data\S32DB001.db

# PDF Export
PDF_PRINTER_NAME=Microsoft Print to PDF
PDF_OUTPUT_DIR=reports/pdf

# Safety
SAFE_MODE=true

# Whisper (Voice Agent)
WHISPER_MODEL=base
WHISPER_LANGUAGE=en
```

---

## Testing

```bash
# Run basic tests (no P6 required)
python -m tests.test_automation_e2e

# Run full tests (P6 must be running)
python -m tests.test_automation_e2e --with-p6

# P6 GUI Automation tests
cd "P6 GUI Automation"
python run_tests.py --quick
```

---

## Dependencies

### Core
```
pywinauto>=0.6.8
psutil>=5.9.0
reportlab>=4.0.0
pandas>=2.0.0
python-dotenv>=1.0.0
```

### Voice Agent (optional)
```
openai-whisper>=20231117
pyaudio>=0.2.14
soundfile>=0.12.1
```

### AI Integration (optional)
```
anthropic>=0.18.0
openai>=1.12.0
```

---

## Architecture

The project follows a 3-layer architecture:

1. **Directive Layer** - SOPs in `directives/` defining goals and workflows
2. **Orchestration Layer** - AI agent making intelligent routing decisions
3. **Execution Layer** - Deterministic Python scripts in `src/` and `execution/`

---

## Safe Mode

Write operations require `safe_mode=False`:

```python
# Read-only (default)
scheduler = P6ScheduleManager(window, safe_mode=True)

# Enable modifications
scheduler = P6ScheduleManager(window, safe_mode=False)
```

---

## Documentation

| File | Description |
|------|-------------|
| `AGENTS.md` | 3-layer architecture instructions |
| `docs/SQLITE_DAO.md` | SQLite DAO layer documentation |
| `docs/PDF_GENERATOR_IMPLEMENTATION_PLAN.md` | PDF generation details |
| `P6 GUI Automation/tasks.md` | Voice agent implementation status |
| `summary_schedule_generator/README.md` | XER generator documentation |
| `PHASE_*.md` | Development phase summaries |

---

## License

See LICENSE file.
