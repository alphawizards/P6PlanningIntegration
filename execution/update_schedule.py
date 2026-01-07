#!/usr/bin/env python3
"""
Execution Script: Update Schedule
Layer: 3 (Execution)

Description:
Performs safe bulk updates to the P6 schedule using SQLiteBulkWriter.
Supports: 'activity_names', 'wbs_assignments'.
Input: JSON file containing update instructions.
"""

import sys
import json
import argparse
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.dao.sqlite.bulk_writer import SQLiteBulkWriter
from src.utils import logger

def main():
    parser = argparse.ArgumentParser(description="Bulk Update P6 Schedule")
    parser.add_argument("--input", required=True, help="Path to JSON input file")
    parser.add_argument("--type", required=True, choices=['activity_names', 'wbs_assignments'], help="Type of update")
    parser.add_argument("--project-id", required=True, type=int, help="Project ObjectId scope")
    
    args = parser.parse_args()
    
    try:
        logger.info(f"Starting execution: Update Schedule ({args.type})")
        
        # Read Input
        input_path = Path(args.input)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
            
        with open(input_path, 'r') as f:
            updates = json.load(f)
            
        if not isinstance(updates, dict):
            raise ValueError("Input JSON must be a dictionary mapping Code -> Value")
            
        # Execute Update
        writer = SQLiteBulkWriter()
        count = 0
        
        if args.type == 'activity_names':
            count = writer.update_activity_names(args.project_id, updates)
        elif args.type == 'wbs_assignments':
            count = writer.update_wbs_assignments(args.project_id, updates)
            
        # Result
        print(json.dumps({
            "success": True,
            "type": args.type,
            "updated_count": count
        }))
        logger.info(f"Execution complete. Updated {count} records.")

    except Exception as e:
        logger.error(f"Execution failed: {e}")
        print(json.dumps({
            "success": False,
            "error": str(e)
        }))
        sys.exit(1)

if __name__ == "__main__":
    main()
