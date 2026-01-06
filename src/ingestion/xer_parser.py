#!/usr/bin/env python3
"""
XER Parser
Parses Primavera P6 XER (export) files.
"""

from typing import Dict, List
import pandas as pd
from datetime import datetime

from src.ingestion.base import ScheduleParser
from src.utils import logger


class XERParser(ScheduleParser):
    """
    Parser for Primavera P6 XER files.
    
    XER Format:
    - Tab-separated values
    - Table structure with %T (table name) and %F (field names)
    - Tables: PROJECT, TASK, TASKPRED, etc.
    
    VERIFICATION POINT 2: XER Parsing
    Correctly handles %T and %F markers to extract tables.
    """
    
    def parse(self) -> Dict[str, pd.DataFrame]:
        """
        Parse XER file into standardized DataFrames.
        
        VERIFICATION POINT 2: XER Parsing
        Extracts PROJECT and TASK tables using %T and %F markers.
        
        Returns:
            Dict with 'projects' and 'activities' DataFrames
        """
        try:
            logger.info(f"Parsing XER file: {self.filepath}")
            
            # Read file with encoding fallback
            content = self._read_file_with_encoding()
            lines = content.split('\n')
            
            # Extract tables
            tables = self._extract_tables(lines)
            
            logger.info(f"Extracted {len(tables)} tables from XER file")
            logger.debug(f"Available tables: {list(tables.keys())}")
            
            # Parse projects
            projects_df = self._parse_projects(tables)
            
            # Parse activities (tasks)
            activities_df = self._parse_activities(tables)
            
            result = {
                'projects': projects_df,
                'activities': activities_df
            }
            
            self.validate_result(result)
            
            logger.info(f"✓ XER parsing complete: {len(projects_df)} projects, {len(activities_df)} activities")
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse XER file: {e}")
            raise RuntimeError(f"XER parsing failed: {e}") from e
    
    def _extract_tables(self, lines: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Extract tables from XER file.
        
        VERIFICATION POINT 2: XER Parsing
        Parses %T (table name) and %F (field names) markers.
        
        Args:
            lines: File lines
            
        Returns:
            Dict of {table_name: DataFrame}
        """
        tables = {}
        current_table = None
        current_fields = []
        current_data = []
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            # VERIFICATION POINT 2: Table marker
            if line.startswith('%T'):
                # Save previous table
                if current_table and current_fields and current_data:
                    tables[current_table] = pd.DataFrame(
                        current_data,
                        columns=current_fields
                    )
                    logger.debug(f"Extracted table '{current_table}': {len(current_data)} rows")
                
                # Start new table
                current_table = line.split('\t')[1] if '\t' in line else line[2:].strip()
                current_fields = []
                current_data = []
            
            # VERIFICATION POINT 2: Field marker
            elif line.startswith('%F'):
                # Extract field names (tab-separated)
                parts = line.split('\t')
                current_fields = [p.strip() for p in parts[1:] if p.strip()]
            
            # Data row
            elif line.startswith('%R'):
                # Extract data values (tab-separated)
                parts = line.split('\t')
                values = parts[1:]  # Skip %R marker
                
                # Pad or trim to match field count
                if len(values) < len(current_fields):
                    values.extend([None] * (len(current_fields) - len(values)))
                elif len(values) > len(current_fields):
                    values = values[:len(current_fields)]
                
                current_data.append(values)
        
        # Save last table
        if current_table and current_fields and current_data:
            tables[current_table] = pd.DataFrame(
                current_data,
                columns=current_fields
            )
            logger.debug(f"Extracted table '{current_table}': {len(current_data)} rows")
        
        return tables
    
    def _parse_projects(self, tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Parse PROJECT table into standardized DataFrame.
        
        VERIFICATION POINT 1: Schema Alignment
        Maps XER columns to standard PROJECT_FIELDS.
        
        Args:
            tables: Extracted XER tables
            
        Returns:
            pd.DataFrame: Standardized projects DataFrame
        """
        if 'PROJECT' not in tables:
            logger.warning("PROJECT table not found in XER file")
            return pd.DataFrame(columns=['ObjectId', 'Id', 'Name', 'Status', 'PlanStartDate'])
        
        project_table = tables['PROJECT']
        
        # XER to standard field mapping
        mapping = {
            'proj_id': 'ObjectId',
            'proj_short_name': 'Id',
            'proj_name': 'Name',
            # XER doesn't have direct Status field, use other indicators
        }
        
        # Add computed fields
        if 'proj_short_name' in project_table.columns and 'Id' not in project_table.columns:
            project_table['Id'] = project_table['proj_short_name']
        
        # Status determination (XER doesn't have direct status)
        project_table['Status'] = 'Active'  # Default
        
        # Parse dates
        if 'plan_start_date' in project_table.columns:
            project_table['PlanStartDate'] = pd.to_datetime(
                project_table['plan_start_date'],
                errors='coerce'
            )
        
        # Standardize
        standardized = self._standardize_project_dataframe(project_table, mapping)
        
        logger.info(f"Parsed {len(standardized)} projects from XER")
        return standardized
    
    def _parse_activities(self, tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Parse TASK table into standardized DataFrame.
        
        VERIFICATION POINT 1: Schema Alignment
        Maps XER columns (task_code, task_name, target_drtn_hr_cnt) to standard ACTIVITY_FIELDS.
        
        Args:
            tables: Extracted XER tables
            
        Returns:
            pd.DataFrame: Standardized activities DataFrame
        """
        if 'TASK' not in tables:
            logger.warning("TASK table not found in XER file")
            return pd.DataFrame(columns=['ObjectId', 'Id', 'Name', 'Status', 'PlannedDuration', 'StartDate', 'FinishDate'])
        
        task_table = tables['TASK']
        
        # VERIFICATION POINT 1: Schema Alignment
        # XER to standard field mapping
        mapping = {
            'task_id': 'ObjectId',
            'task_code': 'Id',
            'task_name': 'Name',
            'status_code': 'Status',
            'act_start_date': 'StartDate',
            'act_end_date': 'FinishDate',
        }
        
        # Handle duration conversion (hours to hours, not days)
        # Note: User mentioned converting to days/8.0, but ACTIVITY_FIELDS expects hours
        if 'target_drtn_hr_cnt' in task_table.columns:
            task_table['PlannedDuration'] = pd.to_numeric(
                task_table['target_drtn_hr_cnt'],
                errors='coerce'
            )
        
        # Parse dates
        date_fields = ['act_start_date', 'act_end_date', 'target_start_date', 'target_end_date']
        for field in date_fields:
            if field in task_table.columns:
                task_table[field] = pd.to_datetime(
                    task_table[field],
                    errors='coerce'
                )
        
        # Use target dates if actual dates not available
        if 'StartDate' not in task_table.columns or task_table['StartDate'].isna().all():
            if 'target_start_date' in task_table.columns:
                task_table['StartDate'] = task_table['target_start_date']
        
        if 'FinishDate' not in task_table.columns or task_table['FinishDate'].isna().all():
            if 'target_end_date' in task_table.columns:
                task_table['FinishDate'] = task_table['target_end_date']
        
        # Map status codes to readable names
        if 'status_code' in task_table.columns:
            status_map = {
                'TK_NotStart': 'Not Started',
                'TK_Active': 'In Progress',
                'TK_Complete': 'Completed',
            }
            task_table['Status'] = task_table['status_code'].map(status_map).fillna(task_table['status_code'])
        
        # Standardize
        standardized = self._standardize_activity_dataframe(task_table, mapping)
        
        logger.info(f"Parsed {len(standardized)} activities from XER")
        return standardized
