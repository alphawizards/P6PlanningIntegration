#!/usr/bin/env python3
"""
MPX Parser
Parses legacy Microsoft Project MPX files.
"""

from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime

from src.ingestion.base import ScheduleParser
from src.utils import logger


class MPXParser(ScheduleParser):
    """
    Parser for Microsoft Project MPX files.
    
    MPX Format:
    - Record-based text format
    - Each line starts with a record number
    - Record 30: Task definition
    - Record 0: Project header
    - Comma-separated values
    
    VERIFICATION POINT 4: Encoding
    Handles legacy encodings (cp1252, latin-1) common in old MPX files.
    """
    
    def parse(self) -> Dict[str, pd.DataFrame]:
        """
        Parse MPX file into standardized DataFrames.
        
        Returns:
            Dict with 'projects' and 'activities' DataFrames
        """
        try:
            logger.info(f"Parsing MPX file: {self.filepath}")
            
            # VERIFICATION POINT 4: Read with encoding fallback
            content = self._read_file_with_encoding(['cp1252', 'latin-1', 'utf-8'])
            lines = content.split('\n')
            
            # Parse records
            project_data = self._parse_project_record(lines)
            activities_data = self._parse_task_records(lines)
            
            # Create DataFrames
            projects_df = pd.DataFrame([project_data])
            activities_df = pd.DataFrame(activities_data) if activities_data else pd.DataFrame(
                columns=['ObjectId', 'Id', 'Name', 'Status', 'PlannedDuration', 'StartDate', 'FinishDate']
            )
            
            # MPX format doesn't typically include relationship data in the standard format
            relationships_df = pd.DataFrame(columns=['ObjectId', 'PredecessorObjectId', 'SuccessorObjectId', 'Type', 'Lag'])
            
            result = {
                'projects': projects_df,
                'activities': activities_df,
                'relationships': relationships_df
            }
            
            self.validate_result(result)
            
            logger.info(f"✓ MPX parsing complete: {len(projects_df)} projects, {len(activities_data)} activities")
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse MPX file: {e}")
            raise RuntimeError(f"MPX parsing failed: {e}") from e
    
    def _parse_project_record(self, lines: List[str]) -> Dict:
        """
        Parse project header from MPX file.
        
        Record 0 contains project metadata.
        
        Args:
            lines: File lines
            
        Returns:
            Dict: Project data
        """
        project_data = {
            'ObjectId': 1,
            'Id': '1',
            'Name': 'Imported Project',
            'Status': 'Active',
            'PlanStartDate': None,
        }
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Record 0: Project header
            if line.startswith('0,'):
                parts = self._split_mpx_line(line)
                if len(parts) > 1:
                    # Field 1: Project name
                    if len(parts) > 1 and parts[1]:
                        project_data['Name'] = parts[1]
                    # Field 2: Company
                    # Field 3: Manager
                    # ... (MPX has many fields)
                break
        
        logger.debug(f"Parsed project: {project_data['Name']}")
        return project_data
    
    def _parse_task_records(self, lines: List[str]) -> List[Dict]:
        """
        Parse task records from MPX file.
        
        Record 30: Task definition
        
        VERIFICATION POINT 1: Schema Alignment
        Maps MPX fields to standard ACTIVITY_FIELDS.
        
        Args:
            lines: File lines
            
        Returns:
            List[Dict]: Activity data
        """
        activities = []
        task_id_counter = 1
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Record 30: Task
            if line.startswith('30,'):
                parts = self._split_mpx_line(line)
                
                # MPX Task fields (approximate, varies by version):
                # 0: Record number (30)
                # 1: Task ID
                # 2: Task Name
                # 3: WBS
                # 4: Outline Level
                # 5: Duration (minutes)
                # 6: Start Date
                # 7: Finish Date
                # 8: Percent Complete
                # ... many more fields
                
                try:
                    task_id = parts[1] if len(parts) > 1 and parts[1] else str(task_id_counter)
                    task_name = parts[2] if len(parts) > 2 else f"Task {task_id}"
                    
                    # Duration (in minutes, convert to hours)
                    duration_minutes = float(parts[5]) if len(parts) > 5 and parts[5] else 0
                    duration_hours = duration_minutes / 60 if duration_minutes > 0 else None
                    
                    # Dates
                    start_date = self._parse_mpx_date(parts[6]) if len(parts) > 6 else None
                    finish_date = self._parse_mpx_date(parts[7]) if len(parts) > 7 else None
                    
                    # Percent complete
                    percent_complete = int(parts[8]) if len(parts) > 8 and parts[8] else 0
                    
                    # Map status
                    if percent_complete == 0:
                        status = 'Not Started'
                    elif percent_complete == 100:
                        status = 'Completed'
                    else:
                        status = 'In Progress'
                    
                    activity_data = {
                        'ObjectId': task_id_counter,
                        'Id': task_id,
                        'Name': task_name,
                        'Status': status,
                        'PlannedDuration': duration_hours,
                        'StartDate': start_date,
                        'FinishDate': finish_date,
                    }
                    
                    activities.append(activity_data)
                    task_id_counter += 1
                    
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse task record: {e}")
                    continue
        
        logger.info(f"Parsed {len(activities)} tasks from MPX")
        return activities
    
    def _split_mpx_line(self, line: str) -> List[str]:
        """
        Split MPX line into fields.
        
        MPX uses comma-separated values, but fields can be quoted.
        
        Args:
            line: MPX line
            
        Returns:
            List[str]: Fields
        """
        import csv
        import io
        
        # Use CSV reader to handle quoted fields
        reader = csv.reader(io.StringIO(line))
        try:
            return next(reader)
        except StopIteration:
            return []
    
    def _parse_mpx_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse MPX date string.
        
        MPX dates can be in various formats:
        - YYYY-MM-DD
        - DD/MM/YYYY
        - MM/DD/YYYY
        
        Args:
            date_str: Date string
            
        Returns:
            datetime or None
        """
        if not date_str or date_str.strip() == '':
            return None
        
        # Try common date formats
        formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%d-%m-%Y',
            '%m-%d-%Y',
            '%Y/%m/%d',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        # Try pandas parser as fallback
        try:
            return pd.to_datetime(date_str)
        except Exception:
            logger.warning(f"Could not parse date: {date_str}")
            return None
