"""
Tests for SQLiteActivityDAO.
"""

import pytest
import pandas as pd


@pytest.mark.integration
class TestActivityDAOBasic:
    """Basic tests for ActivityDAO."""
    
    def test_get_activities_for_project_returns_dataframe(self, activity_dao, project_dao):
        """Test that get_activities_for_project returns a DataFrame."""
        # Get a real project ID
        projects = project_dao.get_active_projects()
        if len(projects) > 0:
            project_id = int(projects.iloc[0]['ObjectId'])
            result = activity_dao.get_activities_for_project(project_id)
            assert isinstance(result, pd.DataFrame)
    
    def test_activities_have_expected_columns(self, activity_dao, project_dao):
        """Test that activities have expected columns."""
        projects = project_dao.get_active_projects()
        if len(projects) > 0:
            project_id = int(projects.iloc[0]['ObjectId'])
            result = activity_dao.get_activities_for_project(project_id)
            
            expected_columns = ['ObjectId', 'Id', 'Name', 'Status', 'PlannedDuration']
            for col in expected_columns:
                assert col in result.columns, f"Missing column: {col}"


@pytest.mark.integration
class TestActivityDAODurationConversion:
    """Tests for duration conversion (hours -> days)."""
    
    def test_duration_converted_to_days(self, activity_dao, project_dao):
        """Test that PlannedDuration is in days (divided by 8)."""
        projects = project_dao.get_active_projects()
        if len(projects) > 0:
            project_id = int(projects.iloc[0]['ObjectId'])
            activities = activity_dao.get_activities_for_project(project_id)
            
            if len(activities) > 0:
                # Duration should typically be reasonable in days
                # (not huge values like raw hours would be)
                durations = activities['PlannedDuration'].dropna()
                if len(durations) > 0:
                    # Most activities shouldn't exceed 365 days
                    assert durations.max() < 1000, "Duration seems too large - may not be converted"
    
    def test_total_float_converted_to_days(self, activity_dao, project_dao):
        """Test that TotalFloat is in days."""
        projects = project_dao.get_active_projects()
        if len(projects) > 0:
            project_id = int(projects.iloc[0]['ObjectId'])
            activities = activity_dao.get_activities_for_project(project_id)
            
            if len(activities) > 0 and 'TotalFloat' in activities.columns:
                floats = activities['TotalFloat'].dropna()
                if len(floats) > 0:
                    # Float values should be reasonable in days
                    assert floats.max() < 1000, "Float seems too large - may not be converted"
