# P6 Planning Integration

A comprehensive Python platform for Oracle Primavera P6 Professional with full GUI automation, PDF reporting, and AI agent integration.

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

## Quick Start

```python
from src.automation import P6PrintAutomation

with P6PrintAutomation() as p6:
    p6.open_project("My Project")
    p6.apply_layout("Monthly Report")
    p6.print_to_pdf("report.pdf")
```

---

## 15 Automation Modules

| Module | Class | Purpose |
|--------|-------|---------|
| base.py | `P6AutomationBase` | Connection/window management |
| connection.py | `P6ConnectionManager` | Process detection, login |
| navigation.py | `P6Navigator` | Menu, toolbar, status bar |
| printing.py | `P6PrintManager` | Print preview, PDF |
| exporting.py | `P6ExportManager` | XER, XML, Excel |
| projects.py | `P6ProjectManager` | Project tree, open/close |
| layouts.py | `P6LayoutManager` | Layouts, views, filters |
| scheduling.py | `P6ScheduleManager` | F9, leveling, check |
| scheduling.py | `P6BaselineManager` | Baseline CRUD |
| activities.py | `P6ActivityManager` | Activity select/edit |
| batch.py | `P6BatchProcessor` | Batch operations |
| agent.py | `P6AgentInterface` | AI agent integration |

---

## Usage Examples

### Schedule and Print
```python
from src.automation import (
    P6PrintAutomation,
    P6ScheduleManager,
    P6PrintManager
)

with P6PrintAutomation() as p6:
    scheduler = P6ScheduleManager(p6.main_window, safe_mode=False)
    scheduler.schedule_project()  # F9
    
    printer = P6PrintManager(p6.main_window)
    printer.print_gantt_pdf("schedule.pdf")
```

### Batch Export
```python
from src.automation import (
    P6PrintAutomation,
    P6ProjectManager,
    P6LayoutManager,
    P6ExportManager,
    P6BatchProcessor
)

with P6PrintAutomation() as p6:
    batch = P6BatchProcessor(
        project_manager=P6ProjectManager(p6.main_window),
        layout_manager=P6LayoutManager(p6.main_window),
        export_manager=P6ExportManager(p6.main_window)
    )
    
    summary = batch.batch_export(
        project_names=["Project A", "Project B"],
        format="xer"
    )
    print(f"Exported: {summary.successful}/{summary.total}")
```

### AI Agent
```python
from src.automation import P6AgentInterface

agent = P6AgentInterface(
    automation=p6,
    project_manager=projects,
    layout_manager=layouts
)

# Execute action
result = agent.execute("open_project", project_name="Highway")
print(result.to_json())

# Get LLM tool definitions
tools = agent.get_tool_definitions()
```

---

## Testing

```bash
# Run basic tests (no P6 required)
python -m tests.test_automation_e2e

# Run full tests (P6 must be running)
python -m tests.test_automation_e2e --with-p6
```

---

## Configuration

```env
P6_EXECUTABLE_PATH=C:\Program Files\Oracle\Primavera P6\PM.exe
PDF_PRINTER_NAME=Microsoft Print to PDF
PDF_OUTPUT_DIR=reports/pdf
SAFE_MODE=true
```

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

## Dependencies

```
pywinauto>=0.6.8
psutil>=5.9.0
reportlab>=4.0.0
pandas>=2.0.0
```

---

## License

See LICENSE file.
