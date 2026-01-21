# Generate P6 Summary Schedule Script

## Overview

`generate_summary_schedule.py` is a Python script that generates a high-level Primavera P6 Summary Schedule in XER format from Excel summary data.

## Purpose

This script automates the creation of P6 summary schedules by:
1. Loading summary WBS data from an Excel file
2. Parsing a template XER file to extract P6 project structure and settings
3. Generating TASK records from the Excel data
4. Writing a new XER file in P6-compatible format

## Requirements

### Python Dependencies
```bash
pandas
openpyxl  # For reading Excel files
```

Install with:
```bash
pip install pandas openpyxl
```

### Input Files

1. **Template XER File**: `19282-FS-Summary-FS-EXE.xer`
   - Purpose: Provides the P6 project structure, calendar definitions, and metadata
   - Contains: ERMHDR, PROJECT, PROJWBS, CALENDAR tables

2. **Summary Data Excel**: `WBS Summary.xlsx`
   - Purpose: Drives the content of the summary schedule
   - Required Columns:
     - `WBS Code`: Activity ID
     - `WBS Name`: Activity description
     - `Total Activities`: Number of activities (rows with 0 or empty are filtered out)
     - `Start`: Start date
     - `Finish`: Finish date

## Usage

### Basic Usage

```bash
cd /path/to/p6planningintegration
python scripts/generate_summary_schedule.py
```

### File Paths

By default, the script looks for files in:
```
C:/Users/ckr_4/01 Projects/P6PlanningIntegration/
├── 19282-FS-Summary-FS-EXE.xer          (template input)
├── WBS Summary.xlsx                      (data input)
└── 19282_Summary_Schedule_Generated.xer  (output)
```

To customize paths, edit the `main()` function in the script:

```python
def main():
    # Define file paths
    main_project_dir = Path("YOUR_PROJECT_DIRECTORY")

    template_xer = main_project_dir / "YOUR_TEMPLATE.xer"
    summary_excel = main_project_dir / "YOUR_SUMMARY.xlsx"
    output_xer = main_project_dir / "OUTPUT_NAME.xer"
```

## Output

The script generates a P6 XER file with:

### Preserved from Template
- ERMHDR (P6 header)
- CURRTYPE (currency definitions)
- PROJECT (project metadata)
- PROJWBS (WBS structure)
- CALENDAR (calendar definitions)
- FINTMPL, NONWORK, OBS, PCATTYPE, UDFTYPE (metadata tables)

### Generated from Excel
- TASK table with activities mapped from Excel data:
  - `task_code` = WBS Code
  - `task_name` = WBS Name
  - `target_start_date` = Start
  - `target_end_date` = Finish
  - `task_type` = TT_Task (Task Dependent)
  - `status_code` = TK_Active (if started) or TK_NotStart
  - All tasks linked to Root WBS

### Empty Tables
- TASKPRED (no logic links - summary level only)

## Data Filtering

The script automatically filters out rows from the Excel file where:
- `Total Activities` is 0
- `Total Activities` is empty/NaN
- This ensures only WBS elements with actual work are included

## Date Handling

- Dates are parsed using pandas `to_datetime()` with error coercion
- Invalid dates are logged as warnings
- P6 date format: `YYYY-MM-DD HH:MM`
- Duration calculated as: `(Finish - Start) × 8 hours/day`

## Status Determination

Task status is automatically determined:
- `TK_Active` (In Progress): Start date is in the past
- `TK_NotStart` (Not Started): Start date is in the future

## File Encoding

Output XER files use Windows-1252 (cp1252) encoding for P6 compatibility.

## Logging

The script provides detailed logging:
- INFO: Progress updates and summary statistics
- WARNING: Data quality issues (invalid dates, filtered rows)
- ERROR: Critical failures

Example output:
```
2026-01-20 11:18:28 | INFO     | ================================================================================
2026-01-20 11:18:28 | INFO     | P6 Summary Schedule Generator
2026-01-20 11:18:28 | INFO     | ================================================================================
2026-01-20 11:18:28 | INFO     | Loading summary data from: C:\...\WBS Summary.xlsx
2026-01-20 11:18:28 | INFO     | Loaded 66 rows from Excel
2026-01-20 11:18:28 | INFO     | Filtered out 12 rows with zero/empty activities
2026-01-20 11:18:28 | INFO     | Remaining rows: 54
2026-01-20 11:18:28 | WARNING  | 20 rows have invalid Start dates
2026-01-20 11:18:28 | WARNING  | 3 rows have invalid Finish dates
2026-01-20 11:18:28 | INFO     | Parsing template XER: C:\...\19282-FS-Summary-FS-EXE.xer
2026-01-20 11:18:28 | INFO     | Extracted 16 tables from template
2026-01-20 11:18:28 | INFO     | Project ID: 48408
2026-01-20 11:18:28 | INFO     | Root WBS ID: 1256467
2026-01-20 11:18:28 | INFO     | Default Calendar ID: 99599
2026-01-20 11:18:28 | INFO     | Generated 54 tasks from summary data
2026-01-20 11:18:28 | INFO     | Wrote 54 tasks to output XER file
2026-01-20 11:18:28 | INFO     | ✓ Successfully generated summary schedule
```

## Testing / Verification

### Automatic Date Validation (Built-in)

The script includes an automatic **date validation check** that runs after generating the XER file. This ensures data integrity between the Excel input and XER output.

**What it validates:**
- Compares `target_start_date` in XER against `Start` in Excel
- Compares `target_end_date` in XER against `Finish` in Excel
- Reports matches and mismatches for each activity

**Example Output - Success:**
```
2026-01-20 13:18:30 | INFO     | Validating output dates against input Excel data...
2026-01-20 13:18:30 | INFO     | Date Validation Complete: 44/44 activities matched
2026-01-20 13:18:30 | INFO     | ✓ All dates validated successfully!
```

**Example Output - With Mismatches:**
```
2026-01-20 13:18:30 | WARNING  | Date mismatch for A1040: Excel Start=2025-12-22 00:00 vs XER Start=2025-12-23 00:00, Excel Finish=2026-08-17 00:00 vs XER Finish=2026-08-17 00:00
2026-01-20 13:18:30 | INFO     | Date Validation Complete: 43/44 activities matched
2026-01-20 13:18:30 | WARNING  | ⚠ 1 activities had date mismatches
```

### Automatic Activity Code Generation

The script automatically generates **Activity Codes** (Column A) if not provided in Excel:
- Starts at `A1000`
- Increments by 10 for each row: `A1000`, `A1010`, `A1020`, etc.
- This allows for inserting activities between existing ones in the future

**Example:**
| Row | Generated Code |
|-----|----------------|
| 1 | A1000 |
| 2 | A1010 |
| 3 | A1020 |
| ... | ... |

### Date-Stamped Output Files

Output files now include the generation date in the filename:
```
19282_Summary_Schedule_Generated_20_Jan_2026.xer
```

This helps track when each version was created and prevents accidental overwrites.

### Manual Verification Steps

1. **Check File Size**: Generated XER should be ~45-55KB for typical projects
2. **Verify XER Structure**: Open in text editor, confirm `%T`, `%F`, `%R` markers
3. **Import Test**: Import into P6 Professional to verify structure
4. **Spot Check Dates**: Compare a few activities manually between Excel and XER


## Technical Details

### XER Format

The XER format uses tab-delimited tables with special markers:
- `%T` = Table name marker
- `%F` = Field names marker
- `%R` = Data record marker

Example:
```
%T	TASK
%F	task_id	proj_id	wbs_id	task_code	task_name
%R	4600000	48408	1256467	A1000	Sample Activity
```

### Task Field Mapping

| Excel Column | XER Field | Notes |
|--------------|-----------|-------|
| WBS Code | task_code | Activity ID |
| WBS Name | task_name | Description |
| Start | target_start_date, early_start_date, late_start_date | Multiple date fields |
| Finish | target_end_date, early_end_date, late_end_date | Multiple date fields |
| - | task_type | Fixed: TT_Task |
| - | duration_type | Fixed: DT_FixedDUR2 |
| - | wbs_id | Linked to Root WBS from template |
| - | proj_id | From template PROJECT table |
| - | clndr_id | From template PROJECT.clndr_id |

## Troubleshooting

### Issue: "Template XER not found"
- Verify the template file exists at the specified path
- Check file name matches exactly (case-sensitive on some systems)

### Issue: "Summary Excel not found"
- Verify the Excel file exists
- Ensure it has a `.xlsx` extension

### Issue: "Invalid dates" warnings
- Check date format in Excel (should be recognizable date format)
- Empty dates are acceptable but logged
- Dates like "01-May-25 A" may not parse correctly

### Issue: Import errors
- Ensure pandas and openpyxl are installed
- Run: `pip install pandas openpyxl`

## Customization

### Adding Additional Task Fields

To add more task fields, modify the `_generate_tasks()` method:

```python
task = {
    'task_id': task_id,
    'proj_id': self.proj_id,
    'wbs_id': self.root_wbs_id,
    # Add your custom fields here
    'custom_field': row['Your Excel Column'],
}
```

### Changing WBS Assignment

By default, all tasks are assigned to the root WBS. To assign to specific WBS elements, modify:

```python
'wbs_id': self.root_wbs_id,  # Change this logic
```

### Adding Logic Links (TASKPRED)

Currently TASKPRED is empty. To add predecessors:

1. Add logic data to Excel (e.g., "Predecessor" column)
2. Generate TASKPRED records in `_write_output_xer()`

## Author

Senior Python Developer & P6 Data Engineer
Date: 2026-01-20

## Related Files

- `src/ingestion/xer_parser.py` - XER parsing utilities
- `src/utils/logger.py` - Logging infrastructure
