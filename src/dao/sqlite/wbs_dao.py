#!/usr/bin/env python3
"""
SQLite WBS DAO for P6 Professional Standalone.
"""

from typing import Optional, List, Dict, Any
import pandas as pd
from src.utils import logger

class SQLiteWBSDAO:
    """
    Data Access Object for P6 WBS (Work Breakdown Structure).
    
    Schema Mapping:
        wbs_id           -> ObjectId
        wbs_short_name   -> Code
        wbs_name         -> Name
        parent_wbs_id    -> ParentObjectId
        proj_id          -> ProjectObjectId
        seq_num          -> SequenceNumber
    """
    
    BASE_QUERY = """
        SELECT 
            wbs_id as ObjectId,
            wbs_short_name as Code,
            wbs_name as Name,
            parent_wbs_id as ParentObjectId,
            proj_id as ProjectObjectId,
            seq_num as SequenceNumber
        FROM PROJWBS
    """
    
    def __init__(self, manager):
        if manager is None or not manager.is_connected():
            raise ValueError("SQLiteWBSDAO requires a connected SQLiteManager")
        self.manager = manager
    
    def get_wbs_for_project(self, project_object_id: int) -> pd.DataFrame:
        """Fetch all WBS elements for a project."""
        try:
            logger.info(f"Fetching WBS for project {project_object_id}")
            query = self.BASE_QUERY + " WHERE proj_id = ? ORDER BY seq_num"
            
            cursor = self.manager.get_cursor()
            cursor.execute(query, (project_object_id,))
            
            rows = cursor.fetchall()
            return pd.DataFrame([dict(row) for row in rows]) if rows else pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Failed to fetch WBS: {e}")
            raise RuntimeError(f"Failed to fetch WBS: {e}") from e

    def get_wbs_hierarchy(self, project_object_id: int) -> List[Dict[str, Any]]:
        """
        Fetch WBS hierarchy as a nested tree structure.
        
        Returns:
            List of root WBS nodes with 'children' populated recursively.
        """
        df = self.get_wbs_for_project(project_object_id)
        
        if df.empty:
            return []
            
        # Convert to list of dicts for tree building
        nodes = df.to_dict('records')
        node_map = {node['ObjectId']: node for node in nodes}
        roots = []
        
        # Initialize children lists
        for node in nodes:
            node['children'] = []
            
        # Build Tree
        for node in nodes:
            parent_id = node['ParentObjectId']
            if parent_id in node_map:
                node_map[parent_id]['children'].append(node)
            else:
                # If parent not found in dataset (or None), it's a root
                roots.append(node)
                
        return roots
