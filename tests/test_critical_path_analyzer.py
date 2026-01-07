"""
Tests for CriticalPathAnalyzer.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock
from src.analyzers.critical_path_analyzer import CriticalPathAnalyzer

@pytest.fixture
def mock_dao_manager():
    """Create a mock SQLiteManager."""
    manager = Mock()
    manager.get_activity_dao.return_value = Mock()
    return manager

@pytest.fixture
def analyzer(mock_dao_manager):
    """Create analyzer instance."""
    return CriticalPathAnalyzer(mock_dao_manager)

def create_mock_activities(data):
    """Helper to create activities DataFrame."""
    columns = ['ObjectId', 'Id', 'TotalFloat', 'PlannedDuration']
    df = pd.DataFrame(data)
    for col in columns:
        if col not in df.columns:
            df[col] = None 
    return df

class TestCriticalPathAnalyzer:
    """Tests for Critical Path Analysis."""
    
    def test_identifies_critical_activities(self, analyzer):
        """Test detection of critical activities (Float <= 0)."""
        activities = create_mock_activities([
            {'ObjectId': 1, 'Id': 'A1', 'TotalFloat': 0.0, 'PlannedDuration': 5},
            {'ObjectId': 2, 'Id': 'A2', 'TotalFloat': -2.0, 'PlannedDuration': 5}, # Critical
            {'ObjectId': 3, 'Id': 'A3', 'TotalFloat': 10.0, 'PlannedDuration': 5}, # Not Critical
        ])
        
        analyzer.activity_dao.get_activities_for_project.return_value = activities
        
        results = analyzer.analyze_critical_path(101)
        
        assert results['critical_activity_count'] == 2
        assert 'A1' in results['critical_activity_ids']
        assert 'A2' in results['critical_activity_ids']
        assert 'A3' not in results['critical_activity_ids']
        
    def test_identifies_near_critical_activities(self, analyzer):
        """Test detection of near-critical activities (0 < Float <= 10)."""
        activities = create_mock_activities([
            {'ObjectId': 1, 'Id': 'A1', 'TotalFloat': 0.0}, # Critical (not near)
            {'ObjectId': 2, 'Id': 'A2', 'TotalFloat': 5.0}, # Near Critical
            {'ObjectId': 3, 'Id': 'A3', 'TotalFloat': 10.0}, # Near Critical (boundary)
            {'ObjectId': 4, 'Id': 'A4', 'TotalFloat': 15.0}, # Non Critical
        ])
        
        analyzer.activity_dao.get_activities_for_project.return_value = activities
        
        results = analyzer.analyze_critical_path(101)
        
        assert results['near_critical_activity_count'] == 2
        assert 'A2' in results['near_critical_activity_ids']
        assert 'A3' in results['near_critical_activity_ids']
        
    def test_calculates_float_statistics(self, analyzer):
        """Test calculation of float statistics."""
        activities = create_mock_activities([
            {'ObjectId': 1, 'TotalFloat': 0.0},
            {'ObjectId': 2, 'TotalFloat': 10.0},
            {'ObjectId': 3, 'TotalFloat': 20.0},
        ])
        
        analyzer.activity_dao.get_activities_for_project.return_value = activities
        
        results = analyzer.analyze_critical_path(101)
        stats = results['float_statistics']
        
        assert stats['min'] == 0.0
        assert stats['max'] == 20.0
        assert stats['mean'] == 10.0
        assert stats['median'] == 10.0
