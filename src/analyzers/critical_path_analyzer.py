#!/usr/bin/env python3
"""
Critical Path Analyzer for P6 Professional.
"""

from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

from src.utils import logger
from src.dao.sqlite import SQLiteManager


class CriticalPathAnalyzer:
    """
    Analyzes Critical Path and Float Distribution.
    """
    
    def __init__(self, manager: SQLiteManager):
        self.manager = manager
        self.activity_dao = manager.get_activity_dao()
    
    def analyze_critical_path(self, project_id: int) -> Dict[str, Any]:
        """
        Perform critical path analysis.
        """
        logger.info(f"Analyzing critical path for project {project_id}")
        
        # 1. Fetch activities
        activities = self.activity_dao.get_activities_for_project(project_id)
        
        if activities.empty:
            return {'status': 'error', 'message': 'No activities found'}
            
        # 2. Critical Activities (Float <= 0)
        critical_mask = activities['TotalFloat'] <= 0.01  # Epsilon for float
        critical_activities = activities[critical_mask]
        
        # 3. Near Critical (0 < Float <= 10 days)
        near_critical_mask = (activities['TotalFloat'] > 0.01) & (activities['TotalFloat'] <= 10.0)
        near_critical_activities = activities[near_critical_mask]
        
        # 4. Longest Path (Approximate by Duration on Critical Path)
        # Real longest path requires graph traversal, but we can sum critical duration.
        critical_duration = critical_activities['PlannedDuration'].sum()
        
        # 5. Float Distribution
        float_stats = self._calculate_float_stats(activities)
        
        return {
            'project_id': project_id,
            'total_activities': len(activities),
            'critical_activity_count': len(critical_activities),
            'critical_activity_ids': critical_activities['Id'].tolist(),
            'near_critical_activity_count': len(near_critical_activities),
            'near_critical_activity_ids': near_critical_activities['Id'].tolist(),
            'total_critical_duration': float(critical_duration),
            'float_statistics': float_stats
        }
        
    def _calculate_float_stats(self, activities: pd.DataFrame) -> Dict[str, float]:
        """Calculate float statistics."""
        floats = activities['TotalFloat'].dropna()
        
        if floats.empty:
            return {}
            
        return {
            'min': float(floats.min()),
            'max': float(floats.max()),
            'mean': float(floats.mean()),
            'median': float(floats.median()),
            'std': float(floats.std()) if len(floats) > 1 else 0.0,
            # Percentiles
            'p25': float(np.percentile(floats, 25)),
            'p75': float(np.percentile(floats, 75))
        }
