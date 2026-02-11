# Summary Schedule Generator - File Structure Guide

## 📂 Complete File Tree

```
summary_schedule_generator/
│
├── 📄 README.md                              # Quick start guide and overview
│
├── 📁 docs/                                  # Documentation folder
│   ├── README_generate_summary_schedule.md   # Technical documentation (detailed)
│   └── FILE_STRUCTURE.md                     # This file - File structure guide
│
├── 📁 scripts/                               # Executable scripts
│   └── generate_summary_schedule.py          # Main Python script (502 lines)
│
├── 📁 templates/                             # P6 XER template files
│   └── 19282-FS-Summary-FS-EXE.xer          # Template XER (50KB)
│
├── 📁 input/                                 # Input data files
│   └── WBS Summary.xlsx                      # Excel with WBS summary data
│
└── 📁 output/                                # Generated output files
    └── 19282_Summary_Schedule_Generated.xer  # Generated P6 schedule (50KB)

```

## 📋 File Details

### Root Level Files

#### `README.md`
- **Type**: Documentation
- **Size**: ~10KB
- **Purpose**: Main entry point for users
- **Contents**:
  - Quick start instructions
  - Folder structure overview
  - Installation requirements
  - Basic usage examples
  - Configuration guide
  - Troubleshooting tips

---

### `/docs` - Documentation Files

#### `README_generate_summary_schedule.md`
- **Type**: Technical Documentation
- **Size**: ~15KB
- **Purpose**: Comprehensive technical reference
- **Audience**: Developers, advanced users
- **Contents**:
  - Detailed usage instructions
  - Python dependencies
  - Input/output specifications
  - Field mapping tables
  - XER format technical details
  - Customization examples
  - Troubleshooting guide
  - API reference

#### `FILE_STRUCTURE.md` (This File)
- **Type**: Documentation
- **Size**: ~8KB
- **Purpose**: Explain folder organization and file purposes
- **Audience**: All users
- **Contents**:
  - Complete file tree
  - File descriptions
  - Relationships between files
  - Data flow diagrams

---

### `/scripts` - Python Scripts

#### `generate_summary_schedule.py`
- **Type**: Python Script
- **Size**: ~20KB (502 lines)
- **Purpose**: Main executable for schedule generation
- **Language**: Python 3.8+
- **Dependencies**:
  - `pandas` - Data manipulation
  - `openpyxl` - Excel file reading
- **Key Classes**:
  - `XERWriter` - Handles XER format writing
  - `SummaryScheduleGenerator` - Main orchestrator
- **Main Functions**:
  - `main()` - Entry point
  - `_load_summary_data()` - Load Excel
  - `_parse_template_xer()` - Parse template
  - `_extract_project_metadata()` - Get project info
  - `_generate_tasks()` - Create task records
  - `_write_output_xer()` - Write output file
- **Inputs**:
  - `../templates/19282-FS-Summary-FS-EXE.xer`
  - `../input/WBS Summary.xlsx`
- **Outputs**:
  - `../output/19282_Summary_Schedule_Generated.xer`
  - Console logging (INFO, WARNING, ERROR)

---

### `/templates` - Template XER Files

#### `19282-FS-Summary-FS-EXE.xer`
- **Type**: Primavera P6 XER File (Tab-delimited text)
- **Size**: 50KB
- **Encoding**: Windows-1252 (cp1252)
- **Purpose**: Provides P6 project structure and metadata
- **Project**: GEMCO Water Disposal Project
- **Project ID**: 48408
- **Root WBS ID**: 1256467
- **Contains**:
  - `ERMHDR` - P6 header (version 15.1)
  - `CURRTYPE` - Currency definitions (20 currencies)
  - `PROJECT` - Project metadata (1 project)
  - `PROJWBS` - WBS structure (11 WBS elements)
  - `CALENDAR` - Calendar definitions (4 calendars)
  - `FINTMPL` - Financial templates
  - `NONWORK` - Non-working time types
  - `OBS` - Organizational breakdown structure
  - `PCATTYPE` - Project category types
  - `UDFTYPE` - User-defined field types
  - `PCATVAL` - Project category values
  - `PROJPCAT` - Project category assignments
  - `SCHEDOPTIONS` - Scheduling options
  - `TASK` - Original task table (reference)
  - `TASKPRED` - Task predecessors (reference)

**Why It's Needed**:
- Defines project settings (calendars, currencies)
- Provides WBS hierarchy structure
- Ensures consistent P6 configuration
- Contains calendar working hours
- Includes project-specific metadata

**Do Not Modify**: This file should be treated as read-only template

---

### `/input` - Input Data Files

#### `WBS Summary.xlsx`
- **Type**: Microsoft Excel Workbook
- **Size**: ~13KB
- **Format**: .xlsx (Office 2007+)
- **Sheets**: 1 (Sheet1)
- **Rows**: 66 (including header)
- **Columns**: 6

**Column Specifications**:

| Column Name | Type | Required | Format | Example | Notes |
|-------------|------|----------|--------|---------|-------|
| **WBS Code** | Text | Yes | Free text | 19282-FS-CURRENT-35.6.11 | Maps to `task_code` |
| **WBS Name** | Text | Yes | Free text | Key Milestones | Maps to `task_name` |
| **Total Activities** | Number | Yes | Integer | 5 | Rows with 0 filtered out |
| **Remaining Duration** | Number | No | Decimal | 575.0 | Not used in script |
| **Start** | Date | Yes | Date/DateTime | 2026-01-19 00:00:00 | Maps to `target_start_date` |
| **Finish** | Date | Yes | Date/DateTime | 2027-08-17 00:00:00 | Maps to `target_end_date` |

**Data Characteristics**:
- 66 total rows loaded
- 12 rows filtered out (Total Activities = 0)
- 54 valid activities generated
- 20 rows with invalid Start dates (warnings)
- 3 rows with invalid Finish dates (warnings)

**Accepted Date Formats**:
- `YYYY-MM-DD HH:MM:SS` (e.g., 2026-01-19 00:00:00)
- `DD-MMM-YY` (e.g., 01-May-25)
- Any format recognized by pandas `to_datetime()`

**Data Quality Rules**:
- `Total Activities > 0` → Row included
- `Total Activities = 0, empty, NaN` → Row excluded
- Invalid dates → Warning logged, row included with empty dates
- Empty WBS Code/Name → Row included but may cause issues

---

### `/output` - Generated Output Files

#### `19282_Summary_Schedule_Generated.xer`
- **Type**: Primavera P6 XER File (Tab-delimited text)
- **Size**: ~50KB
- **Encoding**: Windows-1252 (cp1252)
- **Generated**: By `generate_summary_schedule.py`
- **Purpose**: Import-ready P6 schedule
- **Project**: Same as template (48408)
- **Tasks**: 54 activities from Excel

**File Structure**:
```
ERMHDR ... (copied from template)
%T CURRTYPE
%F curr_id ... (fields)
%R 1 ... (currency records from template)
...
%T PROJECT
%F proj_id ... (fields)
%R 48408 ... (project record from template)
...
%T PROJWBS
%F wbs_id ... (fields)
%R 1256467 ... (WBS records from template)
...
%T TASK
%F task_id proj_id wbs_id ... (fields)
%R 4600000 48408 1256467 ... (generated tasks from Excel)
%R 4600001 48408 1256467 ...
...
%T TASKPRED
%F task_pred_id task_id pred_task_id ... (fields)
(empty - no predecessor records)
```

**Generated Task Details**:
- Task IDs: 4600000 - 4600053 (sequential)
- All linked to Root WBS: 1256467
- All use calendar: 99599
- Task type: TT_Task (Task Dependent)
- Duration type: DT_FixedDUR2 (Fixed Duration)
- Status: TK_Active or TK_NotStart (based on dates)

**Import to P6**:
1. Open P6 Professional
2. File → Import → Select this XER file
3. Choose import options (new project or update existing)
4. Review import summary
5. Verify schedule structure

---

## 🔄 Data Flow Diagram

### High-Level Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    USER INTERACTION                           │
└────────────┬─────────────────────────────────────────────────┘
             │
             ▼
    ┌────────────────┐
    │  Run Script    │
    │  (manual)      │
    └────────┬───────┘
             │
             ▼
┌────────────────────────────────────────────────────────────────┐
│              SCRIPT: generate_summary_schedule.py              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  1. Load & Filter Excel Data                           │  │
│  │     Input: ../input/WBS Summary.xlsx                   │  │
│  │     Output: DataFrame (54 rows)                        │  │
│  │     Filtering: Total Activities > 0                    │  │
│  └────────────────┬───────────────────────────────────────┘  │
│                   │                                            │
│                   ▼                                            │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  2. Parse Template XER                                  │  │
│  │     Input: ../templates/19282-FS-Summary-FS-EXE.xer    │  │
│  │     Output: Dict of tables (16 tables)                 │  │
│  │     Tables: ERMHDR, PROJECT, PROJWBS, CALENDAR, etc.   │  │
│  └────────────────┬───────────────────────────────────────┘  │
│                   │                                            │
│                   ▼                                            │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  3. Extract Project Metadata                            │  │
│  │     Extract: proj_id = 48408                           │  │
│  │     Extract: root_wbs_id = 1256467                     │  │
│  │     Extract: default_calendar_id = 99599               │  │
│  └────────────────┬───────────────────────────────────────┘  │
│                   │                                            │
│                   ▼                                            │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  4. Generate TASK Records                               │  │
│  │     For each row in DataFrame:                          │  │
│  │       - Create task_id (4600000+)                       │  │
│  │       - Map Excel columns to XER fields                 │  │
│  │       - Assign to root WBS                              │  │
│  │       - Set status based on dates                       │  │
│  │     Output: DataFrame with 54 tasks                     │  │
│  └────────────────┬───────────────────────────────────────┘  │
│                   │                                            │
│                   ▼                                            │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  5. Write Output XER                                    │  │
│  │     - Write ERMHDR (from template)                      │  │
│  │     - Write metadata tables (from template)             │  │
│  │     - Write TASK table (generated)                      │  │
│  │     - Write empty TASKPRED table                        │  │
│  │     Output: ../output/19282_Summary_Schedule_Generated.xer│
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
             │
             ▼
    ┌────────────────┐
    │  Output File   │
    │  Ready for P6  │
    └────────────────┘
```

### Detailed Field Mapping

```
Excel Column           →    XER Field               Notes
─────────────────────       ──────────────────     ─────────────────────
WBS Code               →    task_code              Activity ID
WBS Name               →    task_name              Description
Start                  →    target_start_date      YYYY-MM-DD HH:MM
Start                  →    early_start_date       Same as target
Start                  →    late_start_date        Same as target
Finish                 →    target_end_date        YYYY-MM-DD HH:MM
Finish                 →    early_end_date         Same as target
Finish                 →    late_end_date          Same as target
Total Activities       →    (filter only)          Not in output
Remaining Duration     →    (not used)             Not in output

(auto-generated)       →    task_id                4600000, 4600001, ...
(from template)        →    proj_id                48408
(from template)        →    wbs_id                 1256467 (root WBS)
(from template)        →    clndr_id               99599
(calculated)           →    target_drtn_hr_cnt     (Finish-Start)×8
(calculated)           →    status_code            TK_Active or TK_NotStart
(fixed)                →    task_type              TT_Task
(fixed)                →    duration_type          DT_FixedDUR2
(fixed)                →    complete_pct_type      CP_Phys
(fixed)                →    priority_type          PT_Normal
```

---

## 🔑 Key Relationships

### Files That Depend on Each Other

```
generate_summary_schedule.py
    ↓ reads
    ├── templates/19282-FS-Summary-FS-EXE.xer    (REQUIRED - Template)
    ├── input/WBS Summary.xlsx                    (REQUIRED - Data)
    └── output/                                   (WRITES - Destination)
            └── 19282_Summary_Schedule_Generated.xer
```

### What Happens If Files Are Missing

| Missing File | Impact | Error Message |
|--------------|--------|---------------|
| Template XER | Script fails immediately | "Template XER not found: ..." |
| Input Excel | Script fails immediately | "Summary Excel not found: ..." |
| Output folder | Created automatically | No error |
| Docs | No impact on script | Documentation unavailable |

---

## 📊 File Size Reference

| File | Typical Size | Notes |
|------|--------------|-------|
| generate_summary_schedule.py | 20KB | 502 lines of code |
| Template XER | 50KB | Full P6 project structure |
| Input Excel | 10-15KB | Varies with data volume |
| Output XER | 50KB | Similar to template + tasks |
| README.md | 10KB | Main documentation |
| Technical docs | 15KB | Detailed reference |

---

## 🛠️ Maintenance Guidelines

### Adding New Template Files

1. Place template XER in `/templates/` folder
2. Update script `main()` function to reference new template
3. Verify template contains required tables (PROJECT, PROJWBS, CALENDAR)

### Adding New Input Files

1. Ensure Excel has required columns (WBS Code, WBS Name, Total Activities, Start, Finish)
2. Place in `/input/` folder
3. Update script `main()` function if filename differs

### Organizing Multiple Projects

Create subfolders:
```
input/
  ├── project_A/
  │   └── WBS_Summary_A.xlsx
  └── project_B/
      └── WBS_Summary_B.xlsx

templates/
  ├── template_A.xer
  └── template_B.xer

output/
  ├── project_A/
  └── project_B/
```

---

## 📚 Related Documentation

- **Quick Start**: See `../README.md`
- **Technical Details**: See `README_generate_summary_schedule.md`
- **Script Source**: See `../scripts/generate_summary_schedule.py`

---

**Author**: Senior Python Developer & P6 Data Engineer
**Last Updated**: 2026-01-20
