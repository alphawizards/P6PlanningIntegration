"""
Tests for ScheduleAnalyzer.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock
from src.analyzers.schedule_analyzer import ScheduleAnalyzer

@pytest.fixture
def mock_dao_manager():
    """Create a mock SQLiteManager with mock DAOs."""
    manager = Mock()
    manager.get_activity_dao.return_value = Mock()
    manager.get_relationship_dao.return_value = Mock()
    return manager

@pytest.fixture
def analyzer(mock_dao_manager):
    """Create analyzer instance with mock manager."""
    return ScheduleAnalyzer(mock_dao_manager)

def create_mock_activities(data):
    """Helper to create activities DataFrame."""
    # Ensure all required columns are present
    columns = [
        'ObjectId', 'Id', 'Name', 'Status', 'PlannedDuration', 
        'StartDate', 'FinishDate', 'ActualStartDate', 'ActualFinishDate',
        'Type', 'ConstraintType', 'TotalFloat', 'ProjectObjectId'
    ]
    df = pd.DataFrame(data)
    for col in columns:
        if col not in df.columns:
            df[col] = None 
    return df

def create_mock_relationships(data):
    """Helper to create relationships DataFrame."""
    columns = ['ObjectId', 'PredecessorObjectId', 'SuccessorObjectId', 'Type', 'Lag']
    df = pd.DataFrame(data)
    for col in columns:
        if col not in df.columns:
            df[col] = None
    return df

class TestScheduleAnalyzerOpenEnds:
    """Tests for Open End checks."""
    
    def test_detects_open_start(self, analyzer):
        """Test open start detection (no predecessor)."""
        # Activity 1: Normal Task, No Predecessor -> Open Start
        # Activity 2: Start Milestone, No Predecessor -> Allowed
        activities = create_mock_activities([
            {'ObjectId': 1, 'Id': 'A1', 'Type': 'TT_Task'},
            {'ObjectId': 2, 'Id': 'A2', 'Type': 'TT_StartMile'},
        ])
        
        # No relationships
        relationships = create_mock_relationships([])
        
        analyzer.activity_dao.get_activities_for_project.return_value = activities
        analyzer.relationship_dao.get_relationships.return_value = relationships
        
        results = analyzer.run_health_check(101)
        
        open_ends = results['checks']['open_ends']
        assert open_ends['open_start_count'] == 1
        assert 'A1' in open_ends['open_start_ids']
        assert 'A2' not in open_ends['open_start_ids'] # Start Mile excluded
        
    def test_detects_open_finish(self, analyzer):
        """Test open finish detection (no successor)."""
        # Activity 1: Normal Task, No Successor -> Open Finish
        # Activity 2: Fin Milestone, No Successor -> Allowed
        activities = create_mock_activities([
            {'ObjectId': 1, 'Id': 'A1', 'Type': 'TT_Task'},
            {'ObjectId': 2, 'Id': 'A2', 'Type': 'TT_FinMile'},
        ])
        relationships = create_mock_relationships([])
        
        analyzer.activity_dao.get_activities_for_project.return_value = activities
        analyzer.relationship_dao.get_relationships.return_value = relationships
        
        results = analyzer.run_health_check(101)
        
        open_ends = results['checks']['open_ends']
        assert open_ends['open_finish_count'] == 1
        assert 'A1' in open_ends['open_finish_ids']
        assert 'A2' not in open_ends['open_finish_ids']

class TestScheduleAnalyzerConstraints:
    """Tests for Hard Constraint checks."""
    
    def test_detects_hard_constraints(self, analyzer):
        activities = create_mock_activities([
            {'ObjectId': 1, 'Id': 'A1', 'ConstraintType': 'CS_MEO'},   # Hard
            {'ObjectId': 2, 'Id': 'A2', 'ConstraintType': 'CS_MEOA'},  # Hard
            {'ObjectId': 3, 'Id': 'A3', 'ConstraintType': 'CS_ALAP'},  # Soft
            {'ObjectId': 4, 'Id': 'A4', 'ConstraintType': None},       # None
        ])
        relationships = create_mock_relationships([])
        
        analyzer.activity_dao.get_activities_for_project.return_value = activities
        analyzer.relationship_dao.get_relationships.return_value = relationships
        
        results = analyzer.run_health_check(101)
        
        constraints = results['checks']['constraints']
        assert constraints['hard_constraint_count'] == 2
        assert 'A1' in constraints['hard_constraint_ids']
        assert 'A2' in constraints['hard_constraint_ids']

class TestScheduleAnalyzerFloat:
    """Tests for Float checks."""
    
    def test_detects_negative_float(self, analyzer):
        activities = create_mock_activities([
            {'ObjectId': 1, 'Id': 'A1', 'TotalFloat': -10.0},
            {'ObjectId': 2, 'Id': 'A2', 'TotalFloat': 0.0},
            {'ObjectId': 3, 'Id': 'A3', 'TotalFloat': 10.0},
        ])
        relationships = create_mock_relationships([])
        
        analyzer.activity_dao.get_activities_for_project.return_value = activities
        analyzer.relationship_dao.get_relationships.return_value = relationships
        
        results = analyzer.run_health_check(101)
        
        float_check = results['checks']['float']
        assert float_check['negative_float_count'] == 1
        assert 'A1' in float_check['negative_float_ids']
        assert float_check['min_float'] == -10.0

class TestScheduleAnalyzerProgress:
    """Tests for Progress Integrity checks."""
    
    def test_detects_missing_actuals(self, analyzer):
        activities = create_mock_activities([
            # Error: In Progress but no Actual Start
            {'ObjectId': 1, 'Id': 'A1', 'Status': 'TK_Active', 'ActualStartDate': None},
            # Valid: In Progress with Actual Start
            {'ObjectId': 2, 'Id': 'A2', 'Status': 'TK_Active', 'ActualStartDate': '2023-01-01'},
            # Error: Completed but no Actual Finish
            {'ObjectId': 3, 'Id': 'A3', 'Status': 'TK_Done', 'ActualFinishDate': None},
        ])
        relationships = create_mock_relationships([])
        
        analyzer.activity_dao.get_activities_for_project.return_value = activities
        analyzer.relationship_dao.get_relationships.return_value = relationships
        
        results = analyzer.run_health_check(101)
        
        progress = results['checks']['progress']
        assert progress['missing_actual_start_count'] == 1
        assert 'A1' in progress['ids_missing_start']
        assert progress['missing_actual_finish_count'] == 1
        assert 'A3' in progress['ids_missing_finish']
