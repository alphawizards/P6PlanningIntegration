#!/usr/bin/env python3
"""
SQLite Relationship DAO for P6 Professional Standalone.
Read-only access to TASKPRED table with schema-matched column aliases.
"""

from typing import Optional
import pandas as pd

from src.core.definitions import RELATIONSHIP_FIELDS
from src.utils import logger


class SQLiteRelationshipDAO:
    """
    Data Access Object for P6 Task Relationships via SQLite.
    
    Schema Mapping (P6 SQLite -> Agent Schema):
        TASK_PRED_ID   -> ObjectId
        PRED_TASK_ID   -> PredecessorObjectId
        TASK_ID        -> SuccessorObjectId
        PRED_TYPE      -> Type
        LAG_HR_CNT/8   -> Lag (Hours -> Days)
    
    VERIFICATION POINT: Duration Math
    P6 stores lag in Hours. We divide by 8.0 to match Agent's Days expectation.
    """
    
    # SQL query with schema-matched aliases
    BASE_QUERY = """
        SELECT 
            TASK_PRED_ID as ObjectId,
            PRED_TASK_ID as PredecessorObjectId,
            TASK_ID as SuccessorObjectId,
            PRED_TYPE as Type,
            COALESCE(LAG_HR_CNT, 0) / 8.0 as Lag
        FROM TASKPRED
    """
    
    def __init__(self, manager):
        """
        Initialize SQLiteRelationshipDAO with a SQLiteManager.
        
        Args:
            manager: SQLiteManager instance (must be connected)
        """
        if manager is None or not manager.is_connected():
            raise ValueError("SQLiteRelationshipDAO requires a connected SQLiteManager")
        
        self.manager = manager
        logger.info("SQLiteRelationshipDAO initialized")
    
    def get_relationships(self, project_object_id: int) -> pd.DataFrame:
        """
        Fetch all relationships for activities in a project.
        
        Args:
            project_object_id: Project ObjectId
            
        Returns:
            pd.DataFrame: DataFrame with RELATIONSHIP_FIELDS columns
        """
        try:
            logger.info(f"Fetching relationships for project ObjectId: {project_object_id}")
            
            # Get relationships where the successor task belongs to the project
            query = """
                SELECT 
                    tp.TASK_PRED_ID as ObjectId,
                    tp.PRED_TASK_ID as PredecessorObjectId,
                    tp.TASK_ID as SuccessorObjectId,
                    tp.PRED_TYPE as Type,
                    COALESCE(tp.LAG_HR_CNT, 0) / 8.0 as Lag
                FROM TASKPRED tp
                INNER JOIN TASK t ON tp.TASK_ID = t.TASK_ID
                WHERE t.PROJ_ID = ?
                ORDER BY tp.TASK_ID, tp.PRED_TASK_ID
            """
            
            cursor = self.manager.get_cursor()
            cursor.execute(query, (project_object_id,))
            
            rows = cursor.fetchall()
            relationships = [dict(row) for row in rows]
            
            logger.info(f"Fetched {len(relationships)} relationships")
            
            if relationships:
                df = pd.DataFrame(relationships)
            else:
                df = pd.DataFrame(columns=RELATIONSHIP_FIELDS)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch relationships: {e}")
            raise RuntimeError(f"Failed to fetch relationships: {e}") from e
    
    def get_predecessors(self, activity_object_id: int) -> pd.DataFrame:
        """
        Get all predecessors for a specific activity.
        
        Args:
            activity_object_id: Activity ObjectId (successor)
            
        Returns:
            pd.DataFrame: DataFrame with predecessor relationships
        """
        try:
            logger.info(f"Fetching predecessors for activity ObjectId: {activity_object_id}")
            
            query = self.BASE_QUERY + " WHERE TASK_ID = ?"
            
            cursor = self.manager.get_cursor()
            cursor.execute(query, (activity_object_id,))
            
            rows = cursor.fetchall()
            relationships = [dict(row) for row in rows]
            
            logger.info(f"Found {len(relationships)} predecessors")
            
            if relationships:
                df = pd.DataFrame(relationships)
            else:
                df = pd.DataFrame(columns=RELATIONSHIP_FIELDS)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch predecessors: {e}")
            raise RuntimeError(f"Failed to fetch predecessors: {e}") from e
    
    def get_successors(self, activity_object_id: int) -> pd.DataFrame:
        """
        Get all successors for a specific activity.
        
        Args:
            activity_object_id: Activity ObjectId (predecessor)
            
        Returns:
            pd.DataFrame: DataFrame with successor relationships
        """
        try:
            logger.info(f"Fetching successors for activity ObjectId: {activity_object_id}")
            
            query = self.BASE_QUERY + " WHERE PRED_TASK_ID = ?"
            
            cursor = self.manager.get_cursor()
            cursor.execute(query, (activity_object_id,))
            
            rows = cursor.fetchall()
            relationships = [dict(row) for row in rows]
            
            logger.info(f"Found {len(relationships)} successors")
            
            if relationships:
                df = pd.DataFrame(relationships)
            else:
                df = pd.DataFrame(columns=RELATIONSHIP_FIELDS)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch successors: {e}")
            raise RuntimeError(f"Failed to fetch successors: {e}") from e
    
    def add_relationship(
        self,
        predecessor_object_id: int,
        successor_object_id: int,
        link_type: str = 'FS',
        lag: float = 0.0
    ):
        """
        Add a new relationship.
        
        VERIFICATION POINT: Write Protection
        SQLite mode is READ-ONLY. This method always raises NotImplementedError.
        
        Raises:
            NotImplementedError: Always - SQLite mode is read-only
        """
        raise NotImplementedError(
            "SQLite mode is READ-ONLY. Use P6 Professional application to add relationships. "
            "Relationship creation cannot be performed through this interface to prevent database corruption."
        )
    
    def delete_relationship(self, object_id: int):
        """
        Delete a relationship.
        
        VERIFICATION POINT: Write Protection
        SQLite mode is READ-ONLY. This method always raises NotImplementedError.
        
        Raises:
            NotImplementedError: Always - SQLite mode is read-only
        """
        raise NotImplementedError(
            "SQLite mode is READ-ONLY. Use P6 Professional application to delete relationships. "
            "Relationship deletion cannot be performed through this interface to prevent database corruption."
        )
