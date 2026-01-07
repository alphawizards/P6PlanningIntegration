#!/usr/bin/env python3
"""
SQLite Schema Validator for P6 Professional Standalone.
Validates that expected columns exist in the database tables.
"""

from typing import Dict, List, Set, Tuple
import sqlite3

from src.utils import logger


# Expected schema definitions (column_name -> required)
# Required=True means DAO will fail without it, False means optional/nice-to-have
EXPECTED_PROJECT_COLUMNS = {
    'PROJ_ID': True,
    'PROJ_SHORT_NAME': True,
    'PROJECT_FLAG': True,
    'PLAN_START_DATE': False,
    'PLAN_END_DATE': False,
}

EXPECTED_TASK_COLUMNS = {
    'TASK_ID': True,
    'PROJ_ID': True,
    'TASK_CODE': True,
    'TASK_NAME': True,
    'STATUS_CODE': True,
    'TARGET_DRTN_HR_CNT': True,
    'EARLY_START_DATE': False,
    'EARLY_END_DATE': False,
    'TOTAL_FLOAT_HR_CNT': False,
    'ACT_START_DATE': False,
    'ACT_END_DATE': False,
}

EXPECTED_TASKPRED_COLUMNS = {
    'TASK_PRED_ID': True,
    'TASK_ID': True,
    'PRED_TASK_ID': True,
    'PRED_TYPE': True,
    'LAG_HR_CNT': False,
}


class SchemaValidator:
    """
    Validates SQLite database schema against expected column definitions.
    
    Usage:
        validator = SchemaValidator(connection)
        is_valid, issues = validator.validate_all()
    """
    
    def __init__(self, connection: sqlite3.Connection):
        """
        Initialize schema validator.
        
        Args:
            connection: Active SQLite connection
        """
        self.connection = connection
    
    def get_table_columns(self, table_name: str) -> Set[str]:
        """
        Get all column names for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Set of column names (uppercase)
        """
        cursor = self.connection.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = {row[1].upper() for row in cursor.fetchall()}
        return columns
    
    def validate_table(
        self, 
        table_name: str, 
        expected_columns: Dict[str, bool]
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a single table against expected columns.
        
        Args:
            table_name: Name of the table to validate
            expected_columns: Dict of column_name -> required
            
        Returns:
            Tuple of (is_valid, missing_required, missing_optional)
        """
        try:
            actual_columns = self.get_table_columns(table_name)
            
            missing_required = []
            missing_optional = []
            
            for col_name, is_required in expected_columns.items():
                if col_name.upper() not in actual_columns:
                    if is_required:
                        missing_required.append(col_name)
                    else:
                        missing_optional.append(col_name)
            
            is_valid = len(missing_required) == 0
            return is_valid, missing_required, missing_optional
            
        except sqlite3.Error as e:
            logger.error(f"Failed to validate table {table_name}: {e}")
            return False, [f"TABLE_ERROR: {e}"], []
    
    def validate_all(self) -> Tuple[bool, Dict[str, dict]]:
        """
        Validate all expected tables.
        
        Returns:
            Tuple of (all_valid, results_dict)
            
            results_dict structure:
            {
                'PROJECT': {'valid': True, 'missing_required': [], 'missing_optional': []},
                'TASK': {...},
                'TASKPRED': {...}
            }
        """
        tables_to_validate = [
            ('PROJECT', EXPECTED_PROJECT_COLUMNS),
            ('TASK', EXPECTED_TASK_COLUMNS),
            ('TASKPRED', EXPECTED_TASKPRED_COLUMNS),
        ]
        
        results = {}
        all_valid = True
        
        for table_name, expected_cols in tables_to_validate:
            is_valid, missing_req, missing_opt = self.validate_table(
                table_name, expected_cols
            )
            
            results[table_name] = {
                'valid': is_valid,
                'missing_required': missing_req,
                'missing_optional': missing_opt,
            }
            
            if not is_valid:
                all_valid = False
                logger.error(
                    f"Schema validation FAILED for {table_name}: "
                    f"Missing required columns: {missing_req}"
                )
            elif missing_opt:
                logger.warning(
                    f"Schema validation WARNING for {table_name}: "
                    f"Missing optional columns: {missing_opt}"
                )
            else:
                logger.info(f"Schema validation PASSED for {table_name}")
        
        return all_valid, results


def validate_schema(connection: sqlite3.Connection) -> bool:
    """
    Convenience function to validate schema.
    
    Args:
        connection: Active SQLite connection
        
    Returns:
        True if all required columns present, False otherwise
    """
    validator = SchemaValidator(connection)
    is_valid, results = validator.validate_all()
    return is_valid
