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


class TestScheduleAnalyzerDurationLag:
    """Tests for Duration and Lag checks."""

    def test_detects_high_duration(self, analyzer):
        """Test detection of high duration activities."""
        activities = create_mock_activities([
            {'ObjectId': 1, 'Id': 'A1', 'PlannedDuration': 5.0},   # Normal
            {'ObjectId': 2, 'Id': 'A2', 'PlannedDuration': 25.0},  # High (>20)
            {'ObjectId': 3, 'Id': 'A3', 'PlannedDuration': 50.0},  # High
        ])
        relationships = create_mock_relationships([])

        analyzer.activity_dao.get_activities_for_project.return_value = activities
        analyzer.relationship_dao.get_relationships.return_value = relationships

        results = analyzer.run_health_check(101)

        dur_lag = results['checks']['duration_lag']
        assert dur_lag['high_duration_count'] == 2
        assert 'A2' in dur_lag['high_duration_ids']
        assert 'A3' in dur_lag['high_duration_ids']
        assert 'A1' not in dur_lag['high_duration_ids']

    def test_detects_high_lag(self, analyzer):
        """Test detection of high lag relationships."""
        activities = create_mock_activities([
            {'ObjectId': 1, 'Id': 'A1', 'Type': 'TT_Task'},
            {'ObjectId': 2, 'Id': 'A2', 'Type': 'TT_Task'},
        ])
        relationships = create_mock_relationships([
            {'ObjectId': 1, 'PredecessorObjectId': 1, 'SuccessorObjectId': 2, 'Lag': 5},   # Normal
            {'ObjectId': 2, 'PredecessorObjectId': 1, 'SuccessorObjectId': 2, 'Lag': 15},  # High (>10)
        ])

        analyzer.activity_dao.get_activities_for_project.return_value = activities
        analyzer.relationship_dao.get_relationships.return_value = relationships

        results = analyzer.run_health_check(101)

        dur_lag = results['checks']['duration_lag']
        assert dur_lag['high_lag_count'] == 1

    def test_detects_negative_lag(self, analyzer):
        """Test detection of negative lag (leads)."""
        activities = create_mock_activities([
            {'ObjectId': 1, 'Id': 'A1', 'Type': 'TT_Task'},
            {'ObjectId': 2, 'Id': 'A2', 'Type': 'TT_Task'},
        ])
        relationships = create_mock_relationships([
            {'ObjectId': 1, 'PredecessorObjectId': 1, 'SuccessorObjectId': 2, 'Lag': -5},  # Negative (lead)
            {'ObjectId': 2, 'PredecessorObjectId': 1, 'SuccessorObjectId': 2, 'Lag': 0},   # Zero
        ])

        analyzer.activity_dao.get_activities_for_project.return_value = activities
        analyzer.relationship_dao.get_relationships.return_value = relationships

        results = analyzer.run_health_check(101)

        dur_lag = results['checks']['duration_lag']
        assert dur_lag['negative_lag_count'] == 1


class TestScheduleAnalyzerEdgeCases:
    """Edge case tests for ScheduleAnalyzer."""

    def test_empty_activities(self, analyzer):
        """Test handling of empty activities DataFrame."""
        activities = pd.DataFrame()
        relationships = create_mock_relationships([])

        analyzer.activity_dao.get_activities_for_project.return_value = activities
        analyzer.relationship_dao.get_relationships.return_value = relationships

        results = analyzer.run_health_check(101)

        assert results['status'] == 'error'
        assert 'No activities found' in results['message']

    def test_empty_relationships(self, analyzer):
        """Test handling of activities with no relationships."""
        activities = create_mock_activities([
            {'ObjectId': 1, 'Id': 'A1', 'Type': 'TT_Task', 'TotalFloat': 10.0},
        ])
        relationships = pd.DataFrame()

        analyzer.activity_dao.get_activities_for_project.return_value = activities
        analyzer.relationship_dao.get_relationships.return_value = relationships

        results = analyzer.run_health_check(101)

        # Should still work, just with open ends
        assert results['total_activities'] == 1
        assert results['total_relationships'] == 0

    def test_loe_activities_excluded_from_open_ends(self, analyzer):
        """Test LOE activities are excluded from open end checks."""
        activities = create_mock_activities([
            {'ObjectId': 1, 'Id': 'A1', 'Type': 'TT_LOE'},  # LOE - should be excluded
        ])
        relationships = create_mock_relationships([])

        analyzer.activity_dao.get_activities_for_project.return_value = activities
        analyzer.relationship_dao.get_relationships.return_value = relationships

        results = analyzer.run_health_check(101)

        open_ends = results['checks']['open_ends']
        assert open_ends['open_start_count'] == 0
        assert open_ends['open_finish_count'] == 0

    def test_properly_linked_activities(self, analyzer):
        """Test activities with proper predecessor/successor links."""
        activities = create_mock_activities([
            {'ObjectId': 1, 'Id': 'A1', 'Type': 'TT_Task'},
            {'ObjectId': 2, 'Id': 'A2', 'Type': 'TT_Task'},
            {'ObjectId': 3, 'Id': 'A3', 'Type': 'TT_Task'},
        ])
        # A1 -> A2 -> A3 (fully linked)
        relationships = create_mock_relationships([
            {'ObjectId': 1, 'PredecessorObjectId': 1, 'SuccessorObjectId': 2, 'Lag': 0},
            {'ObjectId': 2, 'PredecessorObjectId': 2, 'SuccessorObjectId': 3, 'Lag': 0},
        ])

        analyzer.activity_dao.get_activities_for_project.return_value = activities
        analyzer.relationship_dao.get_relationships.return_value = relationships

        results = analyzer.run_health_check(101)

        open_ends = results['checks']['open_ends']
        # Only A1 has open start, only A3 has open finish
        assert open_ends['open_start_count'] == 1
        assert 'A1' in open_ends['open_start_ids']
        assert open_ends['open_finish_count'] == 1
        assert 'A3' in open_ends['open_finish_ids']

    def test_all_zero_float(self, analyzer):
        """Test activities with all zero float (fully critical)."""
        activities = create_mock_activities([
            {'ObjectId': 1, 'Id': 'A1', 'TotalFloat': 0.0},
            {'ObjectId': 2, 'Id': 'A2', 'TotalFloat': 0.0},
            {'ObjectId': 3, 'Id': 'A3', 'TotalFloat': 0.0},
        ])
        relationships = create_mock_relationships([])

        analyzer.activity_dao.get_activities_for_project.return_value = activities
        analyzer.relationship_dao.get_relationships.return_value = relationships

        results = analyzer.run_health_check(101)

        # Zero float is not negative float
        float_check = results['checks']['float']
        assert float_check['negative_float_count'] == 0
        assert float_check['min_float'] == 0.0


class TestScheduleAnalyzerHealthScore:
    """Tests for health score calculation."""

    def test_perfect_score(self, analyzer):
        """Test perfect health score with no issues."""
        activities = create_mock_activities([
            {'ObjectId': 1, 'Id': 'A1', 'Type': 'TT_Task', 'TotalFloat': 10.0,
             'ConstraintType': None, 'Status': 'TK_NotStart'},
            {'ObjectId': 2, 'Id': 'A2', 'Type': 'TT_Task', 'TotalFloat': 5.0,
             'ConstraintType': None, 'Status': 'TK_NotStart'},
        ])
        # Properly linked
        relationships = create_mock_relationships([
            {'ObjectId': 1, 'PredecessorObjectId': 1, 'SuccessorObjectId': 2, 'Lag': 0},
        ])

        analyzer.activity_dao.get_activities_for_project.return_value = activities
        analyzer.relationship_dao.get_relationships.return_value = relationships

        results = analyzer.run_health_check(101)

        # Should have high score (may not be 100 due to open start/finish)
        assert results['health_score'] >= 90

    def test_score_reduces_for_negative_float(self, analyzer):
        """Test score reduces for negative float."""
        activities = create_mock_activities([
            {'ObjectId': 1, 'Id': 'A1', 'Type': 'TT_Task', 'TotalFloat': -10.0},
            {'ObjectId': 2, 'Id': 'A2', 'Type': 'TT_Task', 'TotalFloat': -5.0},
        ])
        relationships = create_mock_relationships([
            {'ObjectId': 1, 'PredecessorObjectId': 1, 'SuccessorObjectId': 2, 'Lag': 0},
        ])

        analyzer.activity_dao.get_activities_for_project.return_value = activities
        analyzer.relationship_dao.get_relationships.return_value = relationships

        results = analyzer.run_health_check(101)

        # Score should be reduced significantly (5 points per negative float)
        assert results['health_score'] < 100

    def test_score_reduces_for_constraints(self, analyzer):
        """Test score reduces for hard constraints."""
        activities = create_mock_activities([
            {'ObjectId': 1, 'Id': 'A1', 'Type': 'TT_Task', 'TotalFloat': 10.0,
             'ConstraintType': 'CS_MEO'},
            {'ObjectId': 2, 'Id': 'A2', 'Type': 'TT_Task', 'TotalFloat': 10.0,
             'ConstraintType': 'CS_MEOA'},
        ])
        relationships = create_mock_relationships([
            {'ObjectId': 1, 'PredecessorObjectId': 1, 'SuccessorObjectId': 2, 'Lag': 0},
        ])

        analyzer.activity_dao.get_activities_for_project.return_value = activities
        analyzer.relationship_dao.get_relationships.return_value = relationships

        results = analyzer.run_health_check(101)

        # Score should be reduced (3 points per constraint)
        assert results['health_score'] < 100

    def test_score_minimum_zero(self, analyzer):
        """Test score doesn't go below zero."""
        # Create many issues to drive score below zero
        activities = create_mock_activities([
            {'ObjectId': i, 'Id': f'A{i}', 'Type': 'TT_Task',
             'TotalFloat': -100.0, 'ConstraintType': 'CS_MEO'}
            for i in range(1, 51)
        ])
        relationships = create_mock_relationships([])

        analyzer.activity_dao.get_activities_for_project.return_value = activities
        analyzer.relationship_dao.get_relationships.return_value = relationships

        results = analyzer.run_health_check(101)

        # Score should be capped at 0
        assert results['health_score'] >= 0


class TestScheduleAnalyzerResultsStructure:
    """Tests for health check results structure."""

    def test_results_contain_timestamp(self, analyzer):
        """Test results contain timestamp."""
        activities = create_mock_activities([
            {'ObjectId': 1, 'Id': 'A1', 'Type': 'TT_Task'},
        ])
        relationships = create_mock_relationships([])

        analyzer.activity_dao.get_activities_for_project.return_value = activities
        analyzer.relationship_dao.get_relationships.return_value = relationships

        results = analyzer.run_health_check(101)

        assert 'timestamp' in results
        assert results['timestamp'] is not None

    def test_results_contain_project_id(self, analyzer):
        """Test results contain project ID."""
        activities = create_mock_activities([
            {'ObjectId': 1, 'Id': 'A1', 'Type': 'TT_Task'},
        ])
        relationships = create_mock_relationships([])

        analyzer.activity_dao.get_activities_for_project.return_value = activities
        analyzer.relationship_dao.get_relationships.return_value = relationships

        results = analyzer.run_health_check(project_id=999)

        assert results['project_id'] == 999

    def test_results_contain_all_check_sections(self, analyzer):
        """Test results contain all check sections."""
        activities = create_mock_activities([
            {'ObjectId': 1, 'Id': 'A1', 'Type': 'TT_Task'},
        ])
        relationships = create_mock_relationships([])

        analyzer.activity_dao.get_activities_for_project.return_value = activities
        analyzer.relationship_dao.get_relationships.return_value = relationships

        results = analyzer.run_health_check(101)

        expected_checks = ['open_ends', 'constraints', 'float', 'duration_lag', 'progress']
        for check in expected_checks:
            assert check in results['checks'], f"Missing check: {check}"
