"""
Tests for SQLiteProjectDAO.
"""

import pytest
import pandas as pd


@pytest.mark.integration
class TestProjectDAOBasic:
    """Basic tests for ProjectDAO."""
    
    def test_get_all_projects_returns_dataframe(self, project_dao):
        """Test that get_all_projects returns a DataFrame."""
        result = project_dao.get_all_projects()
        assert isinstance(result, pd.DataFrame)
    
    def test_get_all_projects_has_expected_columns(self, project_dao):
        """Test that result has expected columns."""
        result = project_dao.get_all_projects()
        expected_columns = ['ObjectId', 'Id', 'Name', 'ProjectFlag']
        for col in expected_columns:
            assert col in result.columns, f"Missing column: {col}"
    
    def test_get_all_projects_not_empty(self, project_dao):
        """Test that we have projects in the database."""
        result = project_dao.get_all_projects()
        assert len(result) > 0, "Expected at least one project"


@pytest.mark.integration
class TestProjectDAOFiltering:
    """Tests for ProjectDAO filtering."""
    
    def test_get_active_projects(self, project_dao):
        """Test get_active_projects returns only actual projects."""
        result = project_dao.get_active_projects()
        assert isinstance(result, pd.DataFrame)
        
        # All should have ProjectFlag = 'Y'
        if len(result) > 0:
            assert all(result['ProjectFlag'] == 'Y')
    
    def test_get_project_by_object_id(self, project_dao):
        """Test fetching a single project by ObjectId."""
        # First get all projects to find a valid ID
        all_projects = project_dao.get_all_projects()
        if len(all_projects) > 0:
            test_id = int(all_projects.iloc[0]['ObjectId'])
            result = project_dao.get_project_by_object_id(test_id)
            
            assert len(result) == 1
            assert result.iloc[0]['ObjectId'] == test_id
    
    def test_get_project_by_invalid_id_returns_empty(self, project_dao):
        """Test that invalid ObjectId returns empty DataFrame."""
        result = project_dao.get_project_by_object_id(999999999)
        assert len(result) == 0
