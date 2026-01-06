#!/usr/bin/env python3
"""
Project Data Access Object
Handles fetching and managing P6 Project data.
"""

from typing import Optional
import pandas as pd

from src.core.definitions import PROJECT_FIELDS
from src.utils import logger, p6_iterator_to_list


class ProjectDAO:
    """
    Data Access Object for P6 Projects.
    
    VERIFICATION POINT 4: Resource Management
    Accepts P6Session instance to reuse the active connection.
    
    VERIFICATION POINT 3: Schema Compliance
    Uses PROJECT_FIELDS from definitions.py to prevent over-fetching.
    """
    
    def __init__(self, session):
        """
        Initialize ProjectDAO with an active P6 session.
        
        VERIFICATION POINT 4: Resource Management
        Reuses the active session instead of creating a new connection.
        
        Args:
            session: Active P6Session instance
        """
        if session is None or not session.is_connected():
            raise ValueError("ProjectDAO requires an active P6Session")
        
        self.session = session
        logger.info("ProjectDAO initialized")
    
    def get_all_projects(self, filter_expr: Optional[str] = None, order_by: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch all projects from P6.
        
        VERIFICATION POINT 3: Schema Compliance
        Only fetches fields defined in PROJECT_FIELDS.
        
        Args:
            filter_expr: Optional P6 filter expression (e.g., "Status = 'Active'")
            order_by: Optional order by clause (e.g., "Name")
            
        Returns:
            pd.DataFrame: DataFrame containing project data with PROJECT_FIELDS columns
        """
        try:
            logger.info("Fetching all projects from P6")
            
            # Get the P6 session object
            p6_session = self.session.session
            
            # Get the EnterpriseLoadManager
            # This is a global object that provides access to project data
            from com.primavera.integration.client import EnterpriseLoadManager
            
            logger.info("Accessing EnterpriseLoadManager")
            
            # VERIFICATION POINT 3: Schema Compliance
            # Convert Python list to Java String array for fields
            import jpype
            java_fields = jpype.JArray(jpype.java.lang.String)(PROJECT_FIELDS)
            
            # Prepare filter and order parameters
            java_filter = jpype.java.lang.String(filter_expr) if filter_expr else None
            java_order = jpype.java.lang.String(order_by) if order_by else None
            
            logger.info(f"Loading projects with fields: {PROJECT_FIELDS}")
            if filter_expr:
                logger.info(f"Filter: {filter_expr}")
            if order_by:
                logger.info(f"Order by: {order_by}")
            
            # Load projects using the session's loadProjects method
            # Returns a BOIterator
            iterator = p6_session.loadProjects(java_fields, java_filter, java_order)
            
            logger.info("Projects loaded, converting to Python data structure")
            
            # VERIFICATION POINT 2: Iterator Pattern
            # Use p6_iterator_to_list which implements while iterator.hasNext()
            projects_list = p6_iterator_to_list(iterator, PROJECT_FIELDS)
            
            logger.info(f"Converted {len(projects_list)} projects")
            
            # VERIFICATION POINT 1: Data Conversion
            # p6_iterator_to_list already handles Java Date conversion
            # Create DataFrame from the list of dictionaries
            df = pd.DataFrame(projects_list)
            
            logger.info(f"Created DataFrame with shape: {df.shape}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch projects: {e}")
            raise RuntimeError(f"Failed to fetch projects: {e}") from e
    
    def get_project_by_id(self, project_id: str) -> Optional[pd.DataFrame]:
        """
        Fetch a single project by its ID.
        
        Args:
            project_id: Project ID (user-visible ID, not ObjectId)
            
        Returns:
            pd.DataFrame: DataFrame with one row, or empty DataFrame if not found
        """
        try:
            logger.info(f"Fetching project with ID: {project_id}")
            
            # Use filter to get specific project
            filter_expr = f"Id = '{project_id}'"
            df = self.get_all_projects(filter_expr=filter_expr)
            
            if df.empty:
                logger.warning(f"Project not found: {project_id}")
            else:
                logger.info(f"Found project: {project_id}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch project by ID: {e}")
            raise RuntimeError(f"Failed to fetch project by ID: {e}") from e
    
    def get_project_by_object_id(self, object_id: int) -> Optional[pd.DataFrame]:
        """
        Fetch a single project by its ObjectId.
        
        Args:
            object_id: Project ObjectId (internal unique identifier)
            
        Returns:
            pd.DataFrame: DataFrame with one row, or empty DataFrame if not found
        """
        try:
            logger.info(f"Fetching project with ObjectId: {object_id}")
            
            # Use filter to get specific project
            filter_expr = f"ObjectId = {object_id}"
            df = self.get_all_projects(filter_expr=filter_expr)
            
            if df.empty:
                logger.warning(f"Project not found with ObjectId: {object_id}")
            else:
                logger.info(f"Found project with ObjectId: {object_id}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch project by ObjectId: {e}")
            raise RuntimeError(f"Failed to fetch project by ObjectId: {e}") from e
    
    def get_active_projects(self) -> pd.DataFrame:
        """
        Fetch all active projects.
        
        Returns:
            pd.DataFrame: DataFrame containing active projects
        """
        logger.info("Fetching active projects")
        return self.get_all_projects(filter_expr="Status = 'Active'")
