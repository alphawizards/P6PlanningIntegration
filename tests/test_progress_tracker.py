"""
Tests for ProgressTracker.
"""

import pytest
import pandas as pd
from unittest.mock import Mock
from src.analyzers.progress_tracker import ProgressTracker

@pytest.fixture
def mock_dao_manager():
    """Create a mock SQLiteManager."""
    manager = Mock()
    manager.get_activity_dao.return_value = Mock()
    return manager

@pytest.fixture
def tracker(mock_dao_manager):
    """Create tracker instance."""
    return ProgressTracker(mock_dao_manager)

def create_mock_activities(data):
    """Helper to create activities DataFrame."""
    columns = ['ObjectId', 'Id', 'Status']
    df = pd.DataFrame(data)
    for col in columns:
        if col not in df.columns:
            df[col] = None 
    return df

class TestProgressTracker:
    """Tests for Progress Tracker."""
    
    def test_counts_status_correctly(self, tracker):
        """Test counting of status types."""
        activities = create_mock_activities([
            {'ObjectId': 1, 'Id': 'A1', 'Status': 'TK_NotStart'},
            {'ObjectId': 2, 'Id': 'A2', 'Status': 'TK_Active'},
            {'ObjectId': 3, 'Id': 'A3', 'Status': 'TK_Done'},
            {'ObjectId': 4, 'Id': 'A4', 'Status': 'TK_Done'},
        ])
        
        tracker.activity_dao.get_activities_for_project.return_value = activities
        
        report = tracker.get_progress_report(101)
        
        counts = report['status_counts']
        assert counts['not_started'] == 1
        assert counts['in_progress'] == 1
        assert counts['completed'] == 2
        assert report['total_activities'] == 4
        assert report['percent_complete_count_based'] == 50.0

    def test_handles_empty_project(self, tracker):
        """Test reporting on empty project."""
        tracker.activity_dao.get_activities_for_project.return_value = pd.DataFrame()
        
        report = tracker.get_progress_report(101)
        
        assert report['status'] == 'error'
