#!/usr/bin/env python3
"""
SQLite Bulk Writer for P6 Professional Standalone.
Provides SAFE write access to the P6 SQLite database for specific bulk operations.

SAFETY PROTOCOL:
1. Enforces Foreign Key Constraints (PRAGMA foreign_keys = ON)
2. Uses Atomic Transactions (Commit/Rollback)
3. Scope Validation (Project ID checks)
"""

import sqlite3
from contextlib import contextmanager
from typing import Dict, List, Tuple, Optional
from pathlib import Path

from src.config import P6_DB_PATH, SAFE_MODE
from src.utils import logger

class SQLiteBulkWriter:
    """
    Handles bulk write operations to P6 SQLite database with safety controls.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize Bulk Writer.
        
        Args:
            db_path: Path to P6 SQLite database. Defaults to config P6_DB_PATH.
        """
        self.db_path = db_path or P6_DB_PATH
        
    @contextmanager
    def _safe_connection(self):
        """
        Context manager for SAFE database connections.
        - Enforces Foreign Keys
        - Manages Transactions (Commit/Rollback)
        """
        if SAFE_MODE:
            raise RuntimeError("SAFE_MODE is enabled. Bulk writes are disabled.")
            
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            # CRITICAL: Enforce Foreign Key Constraints
            conn.execute("PRAGMA foreign_keys = ON;")
            
            yield conn
            
            # Atomic commit if no exceptions
            conn.commit()
            
        except Exception as e:
            if conn:
                logger.error(f"Rolling back transaction due to error: {e}")
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def update_activity_names(self, project_id: int, updates: Dict[str, str]) -> int:
        """
        Bulk update Activity Names.
        
        Args:
            project_id: Project ObjectId (Scope constraint)
            updates: Dictionary mapping ActivityCode (ID) -> New Name
                     Example: {'A100': 'New Name 1', 'A101': 'New Name 2'}
                     
        Returns:
            int: Number of records updated
        """
        logger.info(f"Bulk updating {len(updates)} activity names for Project {project_id}")
        
        query = """
        UPDATE TASK 
        SET task_name = ? 
        WHERE task_code = ? AND proj_id = ?
        """
        
        # Prepare data: (New Name, Activity Code, Project ID)
        data = [(name, code, project_id) for code, name in updates.items()]
        
        with self._safe_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, data)
            updated_count = cursor.rowcount
            
            logger.info(f"Successfully updated {updated_count} activities")
            return updated_count

    def update_wbs_assignments(self, project_id: int, updates: Dict[str, str]) -> int:
        """
        Bulk update Activity WBS Assignments.
        
        Args:
            project_id: Project ObjectId (Scope constraint)
            updates: Dictionary mapping ActivityCode (ID) -> New WBS Code (Short Name)
                     Example: {'A100': 'WBS.1', 'A101': 'WBS.2'}
                     
        Returns:
            int: Number of records updated
        """
        logger.info(f"Bulk updating {len(updates)} WBS assignments for Project {project_id}")
        
        # 1. Resolve WBS Codes to WBS_IDs for this project
        # We need a lookup first because TASK table uses wbs_id (FK), not wbs_code
        with self._safe_connection() as conn:
            cursor = conn.cursor()
            
            # Get all WBS for this project
            cursor.execute(
                "SELECT wbs_short_name, wbs_id FROM PROJWBS WHERE proj_id = ?", 
                (project_id,)
            )
            wbs_map = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Prepare Update Data
            update_data = []
            skipped = []
            
            for act_code, new_wbs_code in updates.items():
                if new_wbs_code in wbs_map:
                    wbs_id = wbs_map[new_wbs_code]
                    update_data.append((wbs_id, act_code, project_id))
                else:
                    skipped.append(act_code)
            
            if skipped:
                logger.warning(f"Skipping {len(skipped)} assignments - WBS Code not found in project: {skipped[:5]}...")

            if not update_data:
                logger.warning("No valid WBS assignments to update")
                return 0

            # 2. Execute Updates
            query = """
            UPDATE TASK 
            SET wbs_id = ? 
            WHERE task_code = ? AND proj_id = ?
            """
            
            cursor.executemany(query, update_data)
            updated_count = cursor.rowcount
            
            logger.info(f"Successfully moved {updated_count} activities to new WBS")
            return updated_count
