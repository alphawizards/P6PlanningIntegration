
import unittest
import sqlite3
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from src.dao.sqlite.bulk_writer import SQLiteBulkWriter

class TestSQLiteBulkWriter(unittest.TestCase):

    def setUp(self):
        # Create a temporary database file
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        # Close the low-level handle immediately; SQLite will open its own
        os.close(self.db_fd)
        
        # Initialize Schema
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("PRAGMA foreign_keys = ON;")
            
            # PROJECT Table
            conn.execute("""
            CREATE TABLE PROJECT (
                proj_id INTEGER PRIMARY KEY,
                proj_short_name TEXT UNIQUE
            );
            """)
            
            # PROJWBS Table
            conn.execute("""
            CREATE TABLE PROJWBS (
                wbs_id INTEGER PRIMARY KEY,
                proj_id INTEGER,
                wbs_short_name TEXT,
                wbs_name TEXT,
                FOREIGN KEY(proj_id) REFERENCES PROJECT(proj_id)
            );
            """)
            
            # TASK Table
            conn.execute("""
            CREATE TABLE TASK (
                task_id INTEGER PRIMARY KEY,
                proj_id INTEGER,
                wbs_id INTEGER,
                task_code TEXT,
                task_name TEXT,
                FOREIGN KEY(proj_id) REFERENCES PROJECT(proj_id),
                FOREIGN KEY(wbs_id) REFERENCES PROJWBS(wbs_id)
            );
            """)
            
            # Seed Data
            conn.execute("INSERT INTO PROJECT (proj_id, proj_short_name) VALUES (100, 'TEST_PROJ')")
            
            conn.execute("INSERT INTO PROJWBS (wbs_id, proj_id, wbs_short_name, wbs_name) VALUES (10, 100, 'WBS.1', 'Root')")
            conn.execute("INSERT INTO PROJWBS (wbs_id, proj_id, wbs_short_name, wbs_name) VALUES (11, 100, 'WBS.2', 'Child 1')")
            
            conn.execute("INSERT INTO TASK (task_id, proj_id, wbs_id, task_code, task_name) VALUES (1000, 100, 10, 'A100', 'Original Name 1')")
            conn.execute("INSERT INTO TASK (task_id, proj_id, wbs_id, task_code, task_name) VALUES (1001, 100, 10, 'A101', 'Original Name 2')")
            conn.execute("INSERT INTO TASK (task_id, proj_id, wbs_id, task_code, task_name) VALUES (1002, 100, 10, 'A102', 'Original Name 3')")
            
            conn.commit()
        finally:
            conn.close()

        # Patch SAFE_MODE to False for this instance
        self.patcher = patch('src.dao.sqlite.bulk_writer.SAFE_MODE', False)
        self.patcher.start()
        
        self.writer = SQLiteBulkWriter(self.db_path)

    def tearDown(self):
        # Stop patcher
        self.patcher.stop()
        
        # Force garbage collection to help release file locks
        # Force garbage collection to help release file locks
        import gc
        gc.collect()
        
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except PermissionError:
                print(f"Warning: Could not delete temp DB {self.db_path}")

    def test_update_activity_names_success(self):
        updates = {
            'A100': 'New Name 1',
            'A102': 'Updated Name 3'
        }
        count = self.writer.update_activity_names(100, updates)
        self.assertEqual(count, 2)
        
        # Verify
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT task_name FROM TASK WHERE task_code='A100'")
            self.assertEqual(cursor.fetchone()[0], 'New Name 1')
            
            # Verify untouched
            cursor.execute("SELECT task_name FROM TASK WHERE task_code='A101'")
            self.assertEqual(cursor.fetchone()[0], 'Original Name 2')

    def test_update_wbs_assignments_success(self):
        updates = {
            'A100': 'WBS.2' # Move A100 to WBS.2 (ID 11)
        }
        count = self.writer.update_wbs_assignments(100, updates)
        self.assertEqual(count, 1)
        
        # Verify
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT wbs_id FROM TASK WHERE task_code='A100'")
            self.assertEqual(cursor.fetchone()[0], 11)

    def test_fk_violation_rollback(self):
        """Test that attempting to create a relationship to non-existent WBS fails and rolls back."""
        # This is tricky because we update via ID. 
        # But let's try to manually inject a bad ID to test the _safe_connection context manager
        
        with self.assertRaises(sqlite3.IntegrityError):
            with self.writer._safe_connection() as conn:
                # Direct SQL injection of bad FK
                conn.execute("UPDATE TASK SET wbs_id = 999 WHERE task_code = 'A100'")
        
        # Verify Rollback (A100 should still be at wbs_id 10)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT wbs_id FROM TASK WHERE task_code='A100'")
            self.assertEqual(cursor.fetchone()[0], 10)

if __name__ == '__main__':
    # Disable Safe Mode for tests
    import src.config
    src.config.SAFE_MODE = False
    unittest.main()
