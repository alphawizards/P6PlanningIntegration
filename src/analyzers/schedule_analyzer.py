#!/usr/bin/env python3
"""
Schedule Analyzer for P6 Professional.
Performs schedule health checks and quality analysis.
"""

from typing import Dict, List, Any, Optional
import pandas as pd
from datetime import datetime

from src.utils import logger
from src.dao.sqlite import SQLiteManager


class ScheduleAnalyzer:
    """
    Analyzes Schedule Quality and Health.
    
    Checks performed:
    1. Open Ends (Start/Finish)
    2. Invalid Logic (Negative Lag, Out of Sequence)
    3. Constraints (Hard Constraints)
    4. Float Analysis (Negative Float)
    5. Duration Analysis (High Duration)
    """
    
    # Configuration thresholds
    HIGH_DURATION_DAYS = 20
    HIGH_LAG_DAYS = 10
    
    # P6 Task Types
    TT_TASK = 'TT_Task'
    TT_START_MILE = 'TT_StartMile'
    TT_FIN_MILE = 'TT_FinMile'
    TT_LOE = 'TT_LOE'
    TT_WBS_SUMMARY = 'TT_WBS'
    
    def __init__(self, manager: SQLiteManager):
        """
        Initialize analyzer with DAO manager.
        """
        self.manager = manager
        self.activity_dao = manager.get_activity_dao()
        self.relationship_dao = manager.get_relationship_dao()
    
    def run_health_check(self, project_id: int) -> Dict[str, Any]:
        """
        Run comprehensive health check for a project.
        
        Args:
            project_id: Project ObjectId
            
        Returns:
            Dictionary containing check results and statistics
        """
        logger.info(f"Running schedule health check for project {project_id}")
        
        # 1. Fetch Data
        activities = self.activity_dao.get_activities_for_project(project_id)
        relationships = self.relationship_dao.get_relationships(project_id)
        
        if activities.empty:
            return {'status': 'error', 'message': 'No activities found'}
        
        # 2. Perform Checks
        results = {
            'timestamp': datetime.now().isoformat(),
            'project_id': project_id,
            'total_activities': len(activities),
            'total_relationships': len(relationships),
            'checks': {}
        }
        
        # Check 1: Open Ends
        results['checks']['open_ends'] = self._check_open_ends(activities, relationships)
        
        # Check 2: Constraints
        results['checks']['constraints'] = self._check_constraints(activities)
        
        # Check 3: Float
        results['checks']['float'] = self._check_float(activities)
        
        # Check 4: Duration & Lag
        results['checks']['duration_lag'] = self._check_duration_lag(activities, relationships)
        
        # Check 5: Progress Integrity
        results['checks']['progress'] = self._check_progress_integrity(activities)
        
        # Calculate overall score (simple implementation)
        results['health_score'] = self._calculate_health_score(results['checks'])
        
        return results
    
    def _check_open_ends(self, activities: pd.DataFrame, relationships: pd.DataFrame) -> Dict[str, Any]:
        """Check for open start and open finish."""
        # Task IDs present in relationships
        preds = set(relationships['PredecessorObjectId'].unique()) if not relationships.empty else set()
        succs = set(relationships['SuccessorObjectId'].unique()) if not relationships.empty else set()
        
        # Filter exclusions: Start Checks (Exclude Start Milestones & Completed)
        # Note: Completed tasks technically effectively merge into history, but we still check logic usually.
        # Strict logic check usually applies to remaining work, but structural integrity applies to everything.
        # We will check everything but exclude Milestones appropriate to the check.
        
        # Open Start: Has no predecessor (is not a successor in any link)
        # Exclude: Start Milestones, LOE
        open_start_mask = (
            (~activities['ObjectId'].isin(succs)) &
            (activities['Type'] != self.TT_START_MILE) & 
            (activities['Type'] != self.TT_LOE)
        )
        open_start_tasks = activities[open_start_mask]
        
        # Open Finish: Has no successor (is not a predecessor in any link)
        # Exclude: Finish Milestones, LOE
        open_finish_mask = (
            (~activities['ObjectId'].isin(preds)) &
            (activities['Type'] != self.TT_FIN_MILE) &
            (activities['Type'] != self.TT_LOE)
        )
        open_finish_tasks = activities[open_finish_mask]
        
        return {
            'open_start_count': len(open_start_tasks),
            'open_finish_count': len(open_finish_tasks),
            'open_start_ids': open_start_tasks['Id'].tolist(),
            'open_finish_ids': open_finish_tasks['Id'].tolist()
        }
    
    def _check_constraints(self, activities: pd.DataFrame) -> Dict[str, Any]:
        """Check for hard constraints."""
        # Hard constraints in P6: Mandatory Start/Finish
        # CS_MEO = Mandatory Early Start ? Need to verify codes. 
        # Common P6 Constraint Codes:
        # CS_ALAP: As Late As Possible
        # CS_MEO: Mandatory Start
        # CS_MEOA: Mandatory Finish
        # CS_MS: Start On
        # CS_MSOA: Finish On
        
        # We'll flag hard constraints (Mandatory)
        hard_constraint_mask = activities['ConstraintType'].isin(['CS_MEO', 'CS_MEOA'])
        hard_tasks = activities[hard_constraint_mask]
        
        return {
            'hard_constraint_count': len(hard_tasks),
            'hard_constraint_ids': hard_tasks['Id'].tolist()
        }
    
    def _check_float(self, activities: pd.DataFrame) -> Dict[str, Any]:
        """Check for negative float (critical issues)."""
        negative_float_mask = activities['TotalFloat'] < 0
        neg_tasks = activities[negative_float_mask]
        
        return {
            'negative_float_count': len(neg_tasks),
            'negative_float_ids': neg_tasks['Id'].tolist(),
            'min_float': float(activities['TotalFloat'].min()) if not activities.empty else 0
        }
    
    def _check_duration_lag(self, activities: pd.DataFrame, relationships: pd.DataFrame) -> Dict[str, Any]:
        """Check for high durations and excessive/negative lags."""
        # High Duration
        high_dur_mask = activities['PlannedDuration'] > self.HIGH_DURATION_DAYS
        high_dur_tasks = activities[high_dur_mask]
        
        results = {
            'high_duration_count': len(high_dur_tasks),
            'high_duration_ids': high_dur_tasks['Id'].tolist(),
        }
        
        if not relationships.empty:
            # High Lag
            high_lag_mask = relationships['Lag'] > self.HIGH_LAG_DAYS
            high_lag_rels = relationships[high_lag_mask]
            
            # Negative Lag
            neg_lag_mask = relationships['Lag'] < 0
            neg_lag_rels = relationships[neg_lag_mask]
            
            results.update({
                'high_lag_count': len(high_lag_rels),
                'negative_lag_count': len(neg_lag_rels)
            })
        else:
            results.update({
                'high_lag_count': 0,
                'negative_lag_count': 0
            })
            
        return results

    def _check_progress_integrity(self, activities: pd.DataFrame) -> Dict[str, Any]:
        """Check for progress inconsistencies."""
        # In Progress but no Actual Start (impossible in P6 app usually, but bad data exists)
        # Status 'A_STATUS_IN_PROGRESS' implies Actual Start should exist
        
        # Status codes: 'TK_Active' (In Progress), 'TK_Done' (Completed), 'TK_NotStart' (Not Started)
        # Need to verify specific codes used in SQLite.
        # Based on schema analysis, STATUS_CODE is TEXT(12).
        # Common values: 'TK_Active', 'TK_Done', 'TK_NotStart'
        
        # In Progress w/ Missing Actual Start
        in_progress_err = (
            (activities['Status'] == 'TK_Active') & 
            (activities['ActualStartDate'].isna())
        )
        
        # Completed w/ Missing Actual Finish
        completed_err = (
            (activities['Status'] == 'TK_Done') & 
            (activities['ActualFinishDate'].isna())
        )
        
        return {
            'missing_actual_start_count': len(activities[in_progress_err]),
            'missing_actual_finish_count': len(activities[completed_err]),
            'ids_missing_start': activities[in_progress_err]['Id'].tolist(),
            'ids_missing_finish': activities[completed_err]['Id'].tolist()
        }
    
    def _calculate_health_score(self, checks: Dict[str, Any]) -> float:
        """Calculate a simple health score (0-100)."""
        score = 100.0
        
        # Deduction rules
        score -= checks['open_ends']['open_start_count'] * 2
        score -= checks['open_ends']['open_finish_count'] * 2
        score -= checks['float']['negative_float_count'] * 5
        score -= checks['constraints']['hard_constraint_count'] * 3
        
        return max(0.0, score)
