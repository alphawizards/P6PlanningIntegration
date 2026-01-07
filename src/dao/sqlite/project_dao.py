#!/usr/bin/env python3
"""
SQLite Project DAO for P6 Professional Standalone.
Read-only access to PROJECT table with schema-matched column aliases.
"""

from typing import Optional
import pandas as pd

from src.core.definitions import PROJECT_FIELDS
from src.utils import logger


class SQLiteProjectDAO:
    """
    Data Access Object for P6 Projects via SQLite.
    
    Schema Mapping (P6 SQLite -> Agent Schema):
        proj_id         -> ObjectId
        proj_short_name -> Id
        proj_short_name -> Name (P6 uses same field for both)
        project_flag    -> ProjectFlag (Y = project, N = EPS node)
        plan_start_date -> PlanStartDate
        plan_end_date   -> PlanEndDate
        
    Note: SQLite schema differs from API - no status_code column.
    Projects are identified by project_flag='Y' (vs EPS nodes = 'N').
    """
    
    # SQL query with schema-matched aliases
    BASE_QUERY = """
        SELECT 
            proj_id as ObjectId,
            proj_short_name as Id,
            proj_short_name as Name,
            project_flag as ProjectFlag,
            plan_start_date as PlanStartDate,
            plan_end_date as PlanEndDate
        FROM PROJECT
    """
    
    def __init__(self, manager):
        """
        Initialize SQLiteProjectDAO with a SQLiteManager.
        
        Args:
            manager: SQLiteManager instance (must be connected)
        """
        if manager is None or not manager.is_connected():
            raise ValueError("SQLiteProjectDAO requires a connected SQLiteManager")
        
        self.manager = manager
        logger.info("SQLiteProjectDAO initialized")
    
    def get_all_projects(self, filter_expr: Optional[str] = None, order_by: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch all projects from the SQLite database.
        
        Args:
            filter_expr: Optional SQL WHERE clause (without 'WHERE')
            order_by: Optional ORDER BY clause (without 'ORDER BY')
            
        Returns:
            pd.DataFrame: DataFrame with PROJECT_FIELDS columns
        """
        try:
            logger.info("Fetching all projects from SQLite")
            
            query = self.BASE_QUERY
            params = []
            
            if filter_expr:
                query += f" WHERE {filter_expr}"
                logger.info(f"Filter: {filter_expr}")
            
            if order_by:
                query += f" ORDER BY {order_by}"
                logger.info(f"Order by: {order_by}")
            
            cursor = self.manager.get_cursor()
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            
            # Convert to list of dicts
            projects = [dict(row) for row in rows]
            
            logger.info(f"Fetched {len(projects)} projects")
            
            # Create DataFrame
            if projects:
                df = pd.DataFrame(projects)
            else:
                # Empty DataFrame with correct columns
                df = pd.DataFrame(columns=PROJECT_FIELDS)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch projects: {e}")
            raise RuntimeError(f"Failed to fetch projects: {e}") from e
    
    def get_project_by_id(self, project_id: str) -> pd.DataFrame:
        """
        Fetch a single project by its user-visible ID.
        
        Args:
            project_id: Project ID (proj_short_name)
            
        Returns:
            pd.DataFrame: DataFrame with one row, or empty if not found
        """
        try:
            logger.info(f"Fetching project with ID: {project_id}")
            
            query = self.BASE_QUERY + " WHERE proj_short_name = ?"
            
            cursor = self.manager.get_cursor()
            cursor.execute(query, (project_id,))
            
            rows = cursor.fetchall()
            projects = [dict(row) for row in rows]
            
            if projects:
                df = pd.DataFrame(projects)
                logger.info(f"Found project: {project_id}")
            else:
                df = pd.DataFrame(columns=PROJECT_FIELDS)
                logger.warning(f"Project not found: {project_id}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch project by ID: {e}")
            raise RuntimeError(f"Failed to fetch project by ID: {e}") from e
    
    def get_project_by_object_id(self, object_id: int) -> pd.DataFrame:
        """
        Fetch a single project by its ObjectId.
        
        Args:
            object_id: Project ObjectId (proj_id)
            
        Returns:
            pd.DataFrame: DataFrame with one row, or empty if not found
        """
        try:
            logger.info(f"Fetching project with ObjectId: {object_id}")
            
            query = self.BASE_QUERY + " WHERE proj_id = ?"
            
            cursor = self.manager.get_cursor()
            cursor.execute(query, (object_id,))
            
            rows = cursor.fetchall()
            projects = [dict(row) for row in rows]
            
            if projects:
                df = pd.DataFrame(projects)
                logger.info(f"Found project with ObjectId: {object_id}")
            else:
                df = pd.DataFrame(columns=PROJECT_FIELDS)
                logger.warning(f"Project not found with ObjectId: {object_id}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch project by ObjectId: {e}")
            raise RuntimeError(f"Failed to fetch project by ObjectId: {e}") from e
    
    def get_active_projects(self) -> pd.DataFrame:
        """
        Fetch all actual projects (not EPS nodes).
        
        Note: SQLite schema doesn't have status_code. Projects are identified
        by project_flag='Y' (vs EPS nodes which have 'N').
        
        Returns:
            pd.DataFrame: DataFrame containing actual projects
        """
        logger.info("Fetching projects (project_flag='Y')")
        return self.get_all_projects(filter_expr="project_flag = 'Y'")
