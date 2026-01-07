#!/usr/bin/env python3
"""
Progress Tracker for P6 Professional.
"""

from typing import Dict, List, Any, Optional
import pandas as pd
from datetime import datetime

from src.utils import logger
from src.dao.sqlite import SQLiteManager


class ProgressTracker:
    """
    Tracks project progress and status.
    """
    
    def __init__(self, manager: SQLiteManager):
        self.manager = manager
        self.activity_dao = manager.get_activity_dao()
    
    def get_progress_report(self, project_id: int) -> Dict[str, Any]:
        """
        Generate progress report.
        """
        logger.info(f"Generating progress report for project {project_id}")
        
        activities = self.activity_dao.get_activities_for_project(project_id)
        
        if activities.empty:
            return {'status': 'error', 'message': 'No activities found'}
            
        # Status counts
        total = len(activities)
        # Status codes: TK_NotStart, TK_Active, TK_Done
        not_started = activities[activities['Status'] == 'TK_NotStart']
        in_progress = activities[activities['Status'] == 'TK_Active']
        completed = activities[activities['Status'] == 'TK_Done']
        
        # Calculate Percent Complete (Count based)
        pct_complete = (len(completed) / total * 100) if total > 0 else 0
        
        # Look Ahead (Not Started, Start Date <= Today + 30 days)
        # Note: SQLite stores dates as strings 'YYYY-MM-DD HH:MM:SS'
        # Would need date parsing for accurate lookahead
        
        return {
            'project_id': project_id,
            'total_activities': total,
            'status_counts': {
                'not_started': len(not_started),
                'in_progress': len(in_progress),
                'completed': len(completed)
            },
            'percent_complete_count_based': round(pct_complete, 2),
            'in_progress_activity_ids': in_progress['Id'].tolist() if not in_progress.empty else [],
            # Placeholder for data date until we fetch it from PROJECT table
            'data_date': None 
        }
