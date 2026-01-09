"""
Tests for SQLiteRelationshipDAO.
"""

import pytest
import pandas as pd


@pytest.mark.integration
class TestRelationshipDAOBasic:
    """Basic tests for RelationshipDAO."""
    
    def test_get_relationships_returns_dataframe(self, relationship_dao, project_dao):
        """Test that get_relationships returns a DataFrame."""
        projects = project_dao.get_active_projects()
        if len(projects) > 0:
            project_id = int(projects.iloc[0]['ObjectId'])
            result = relationship_dao.get_relationships(project_id)
            assert isinstance(result, pd.DataFrame)
    
    def test_relationships_have_expected_columns(self, relationship_dao, project_dao):
        """Test that relationships have expected columns."""
        projects = project_dao.get_active_projects()
        if len(projects) > 0:
            project_id = int(projects.iloc[0]['ObjectId'])
            result = relationship_dao.get_relationships(project_id)
            
            expected_columns = ['ObjectId', 'PredecessorObjectId', 'SuccessorObjectId', 'Type', 'Lag']
            for col in expected_columns:
                assert col in result.columns, f"Missing column: {col}"


@pytest.mark.integration
class TestRelationshipDAOLagConversion:
    """Tests for lag conversion (hours -> days)."""
    
    def test_lag_converted_to_days(self, relationship_dao, project_dao):
        """Test that Lag is in days (divided by 8)."""
        projects = project_dao.get_active_projects()
        
        for _, project in projects.head(5).iterrows():
            project_id = int(project['ObjectId'])
            relationships = relationship_dao.get_relationships(project_id)
            
            if len(relationships) > 0:
                lags = relationships['Lag'].dropna()
                if len(lags) > 0:
                    # Lag values should be reasonable in days (typically < 100)
                    assert lags.abs().max() < 500, "Lag seems too large - may not be converted"
                return  # Found relationships, test passed
        
        # If no relationships found in any project, skip
        pytest.skip("No relationships found in test projects")


@pytest.mark.integration
class TestRelationshipDAOWriteProtection:
    """Tests for write protection."""
    
    def test_add_relationship_raises_not_implemented(self, relationship_dao):
        """Test that add_relationship raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            relationship_dao.add_relationship(1, 2, 'FS', 0)
    
    def test_delete_relationship_raises_not_implemented(self, relationship_dao):
        """Test that delete_relationship raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            relationship_dao.delete_relationship(1)
