#!/usr/bin/env python3
"""
Execution Script: List Projects
Layer: 3 (Execution)

Description:
Lists all projects in the P6 database using the P6 DAO layer.
Output is written to .tmp/projects_list.json
"""

import sys
import json
import os
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.dao.sqlite import SQLiteManager
from src.utils import logger

OUTPUT_FILE = ".tmp/projects_list.json"

def main():
    try:
        logger.info("Starting execution: List Projects")
        
        # Ensure .tmp exists
        os.makedirs(".tmp", exist_ok=True)
        
        with SQLiteManager() as manager:
            project_dao = manager.get_project_dao()
            projects_df = project_dao.get_all_projects()
            
            result = {
                "success": True,
                "count": len(projects_df),
                "projects": projects_df.to_dict('records')
            }
            
            # Serialize dates
            for p in result["projects"]:
                for k, v in p.items():
                    if hasattr(v, 'isoformat'):
                        p[k] = v.isoformat()
            
            # Write Output
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(result, f, indent=2)
                
            logger.info(f"Successfully listed {len(projects_df)} projects to {OUTPUT_FILE}")
            print(f"OUTPUT_FILE: {OUTPUT_FILE}")

    except Exception as e:
        logger.error(f"Execution failed: {e}")
        error_result = {"success": False, "error": str(e)}
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(error_result, f)
        sys.exit(1)

if __name__ == "__main__":
    main()
