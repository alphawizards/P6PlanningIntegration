"""
Tests for SQLiteWBSDAO.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock


class TestWBSDAOBasic:
    """Basic tests for WBSDAO."""
    
    def test_get_wbs_hierarchy_returns_tree(self, sqlite_manager, project_dao):
        """Test fetching WBS hierarchy as tree."""
        projects = project_dao.get_active_projects()
        if len(projects) > 0:
            project_id = int(projects.iloc[0]['ObjectId'])
            wbs_dao = sqlite_manager.get_wbs_dao()
            
            roots = wbs_dao.get_wbs_hierarchy(project_id)
            
            assert isinstance(roots, list)
            if len(roots) > 0:
                assert 'children' in roots[0]
                assert isinstance(roots[0]['children'], list)
                assert 'Code' in roots[0]
                assert 'Name' in roots[0]

    def test_tree_construction_logic(self):
        """Test tree construction with mock data."""
        # Create minimal mock DAO
        mock_manager = Mock()
        mock_manager.is_connected.return_value = True
        
        # Import inside test to avoid early import issues if file not ready
        from src.dao.sqlite.wbs_dao import SQLiteWBSDAO
        dao = SQLiteWBSDAO(mock_manager)
        
        # Mock get_wbs_for_project return
        mock_data = [
            {'ObjectId': 1, 'ParentObjectId': None, 'Code': 'Root'},
            {'ObjectId': 2, 'ParentObjectId': 1, 'Code': 'Child1'},
            {'ObjectId': 3, 'ParentObjectId': 1, 'Code': 'Child2'},
            {'ObjectId': 4, 'ParentObjectId': 2, 'Code': 'Grandchild1'},
        ]
        dao.get_wbs_for_project = Mock(return_value=pd.DataFrame(mock_data))
        
        roots = dao.get_wbs_hierarchy(101)
        
        assert len(roots) == 1
        root = roots[0]
        assert root['Code'] == 'Root'
        assert len(root['children']) == 2
        
        # Check Child1
        child1 = next(c for c in root['children'] if c['Code'] == 'Child1')
        assert len(child1['children']) == 1
        assert child1['children'][0]['Code'] == 'Grandchild1'
