# SQLite DAO Layer Documentation

## Overview

The SQLite DAO layer provides **read-only** access to Primavera P6 Professional Standalone databases. It uses SQLite's **immutable mode** to safely read from databases located in protected directories (e.g., `C:\Program Files\`).

---

## Configuration

### Environment Variables

```env
P6_CONNECTION_MODE=SQLITE
P6_DB_PATH=C:\Program Files\Oracle\Primavera P6\P6 Professional\20.12.0\Data\S32DB001.db
SAFE_MODE=true
```

### Immutable Mode

The connection uses `?immutable=1` URI parameter which:
- Prevents any write operations
- Avoids creating lock files in the database directory
- Allows reading from protected folders without special permissions

---

## Schema Mapping

### PROJECT Table → ProjectDAO

| SQLite Column | DAO Field | Description |
|---------------|-----------|-------------|
| `PROJ_ID` | `ObjectId` | Internal primary key |
| `PROJ_SHORT_NAME` | `Id`, `Name` | Project short name |
| `PROJECT_FLAG` | `ProjectFlag` | 'Y' = project, 'N' = EPS node |
| `PLAN_START_DATE` | `PlanStartDate` | Planned start date |
| `PLAN_END_DATE` | `PlanEndDate` | Planned end date |

### TASK Table → ActivityDAO

| SQLite Column | DAO Field | Conversion |
|---------------|-----------|------------|
| `TASK_ID` | `ObjectId` | - |
| `TASK_CODE` | `Id` | - |
| `TASK_NAME` | `Name` | - |
| `STATUS_CODE` | `Status` | - |
| `TARGET_DRTN_HR_CNT` | `PlannedDuration` | **÷ 8 (hours→days)** |
| `EARLY_START_DATE` | `StartDate` | - |
| `EARLY_END_DATE` | `FinishDate` | - |
| `TOTAL_FLOAT_HR_CNT` | `TotalFloat` | **÷ 8 (hours→days)** |
| `PROJ_ID` | `ProjectObjectId` | - |

### TASKPRED Table → RelationshipDAO

| SQLite Column | DAO Field | Conversion |
|---------------|-----------|------------|
| `TASK_PRED_ID` | `ObjectId` | - |
| `PRED_TASK_ID` | `PredecessorObjectId` | - |
| `TASK_ID` | `SuccessorObjectId` | - |
| `PRED_TYPE` | `Type` | FS, FF, SS, SF |
| `LAG_HR_CNT` | `Lag` | **÷ 8 (hours→days)** |

---

## Usage

```python
from src.dao.sqlite import SQLiteManager

# Context manager (recommended)
with SQLiteManager() as manager:
    # Get DAOs
    project_dao = manager.get_project_dao()
    activity_dao = manager.get_activity_dao()
    relationship_dao = manager.get_relationship_dao()
    
    # Query projects
    projects = project_dao.get_all_projects()
    active_projects = project_dao.get_active_projects()
    
    # Query activities
    activities = activity_dao.get_activities_for_project(project_id)
    
    # Query relationships
    relationships = relationship_dao.get_relationships(project_id)

# Check connection info
print(f"Connected at: {manager.get_connection_timestamp()}")
print(f"Schema valid: {manager.is_schema_valid()}")
```

---

## Data Freshness

Due to **immutable mode**, the application reads a snapshot of the database at connection time. To get updated data after P6 modifies the database:

```python
# Refresh to get latest data
manager.refresh_connection()
```

---

## Running Tests

```powershell
# Run all tests
pytest tests/ -v

# Run with coverage
pip install pytest-cov
pytest tests/ --cov=src/dao/sqlite --cov-report=term-missing
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "unable to open database file" | Use immutable mode or copy database locally |
| "no such column" | P6 version mismatch - check schema validation logs |
| Schema validation warnings | Non-critical - some optional columns missing |
| Stale data | Call `manager.refresh_connection()` |

---

## Known Limitations

1. **Read-only**: Cannot modify P6 data through this interface
2. **Point-in-time snapshot**: Data is frozen at connection time
3. **No concurrent P6 access**: If P6 Professional has exclusive lock, may need to close P6 first
