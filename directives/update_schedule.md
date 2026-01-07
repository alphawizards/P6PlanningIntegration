# Directive: Update Schedule

## Goal
Modify project data in bulk using safe, transactional SQL operations.

## Inputs
- `PROJECT_ID`: The unique ObjectId of the project.
- `UPDATE_TYPE`: One of `activity_names`, `wbs_assignments`.
- `CHANGES`: Dictionary identifying target codes and new values.
  - For `activity_names`: `{ "ActivityCode": "New Name" }`
  - For `wbs_assignments`: `{ "ActivityCode": "New WBS Short Name" }`

## Execution Steps
1. **Prepare Input File**
   - Save the `CHANGES` dictionary to `.tmp/updates.json`

2. **Run Update Script**
   - Tool: `execution/update_schedule.py`
   - Command: `python execution/update_schedule.py --input .tmp/updates.json --type [UPDATE_TYPE] --project-id [PROJECT_ID]`

## Output
- Console JSON: `{ "success": true, "updated_count": N }`

## Safety
- This tool enforces Foreign Key constraints.
- Will fail and rollback if target WBS codes do not exist in the project scope.
