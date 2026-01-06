#!/usr/bin/env python3
"""
Activity Data Access Object
Handles fetching and managing P6 Activity data.
"""

from typing import Optional
import pandas as pd

from src.core.definitions import ACTIVITY_FIELDS
from src.utils import logger, p6_iterator_to_list


class ActivityDAO:
    """
    Data Access Object for P6 Activities.
    
    VERIFICATION POINT 4: Resource Management
    Accepts P6Session instance to reuse the active connection.
    
    VERIFICATION POINT 3: Schema Compliance
    Uses ACTIVITY_FIELDS from definitions.py to prevent over-fetching.
    """
    
    def __init__(self, session):
        """
        Initialize ActivityDAO with an active P6 session.
        
        VERIFICATION POINT 4: Resource Management
        Reuses the active session instead of creating a new connection.
        
        Args:
            session: Active P6Session instance
        """
        if session is None or not session.is_connected():
            raise ValueError("ActivityDAO requires an active P6Session")
        
        self.session = session
        logger.info("ActivityDAO initialized")
    
    def get_activities_for_project(self, project_object_id: int, filter_expr: Optional[str] = None, order_by: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch all activities for a specific project.
        
        VERIFICATION POINT 3: Schema Compliance
        Only fetches fields defined in ACTIVITY_FIELDS.
        
        Args:
            project_object_id: Project ObjectId to filter activities
            filter_expr: Optional additional P6 filter expression
            order_by: Optional order by clause (e.g., "StartDate")
            
        Returns:
            pd.DataFrame: DataFrame containing activity data with ACTIVITY_FIELDS columns
        """
        try:
            logger.info(f"Fetching activities for project ObjectId: {project_object_id}")
            
            # Get the P6 session object
            p6_session = self.session.session
            
            # Get the ActivityManager
            # This is a global object that provides access to activity data
            from com.primavera.integration.client import ActivityManager
            
            logger.info("Accessing ActivityManager")
            
            # VERIFICATION POINT 3: Schema Compliance
            # Convert Python list to Java String array for fields
            import jpype
            java_fields = jpype.JArray(jpype.java.lang.String)(ACTIVITY_FIELDS)
            
            # Build filter expression
            # Always filter by ProjectObjectId
            base_filter = f"ProjectObjectId = {project_object_id}"
            
            if filter_expr:
                # Combine with additional filter using AND
                combined_filter = f"{base_filter} AND ({filter_expr})"
            else:
                combined_filter = base_filter
            
            java_filter = jpype.java.lang.String(combined_filter)
            java_order = jpype.java.lang.String(order_by) if order_by else None
            
            logger.info(f"Loading activities with fields: {ACTIVITY_FIELDS}")
            logger.info(f"Filter: {combined_filter}")
            if order_by:
                logger.info(f"Order by: {order_by}")
            
            # Load activities using the session's loadActivities method
            # Returns a BOIterator
            iterator = p6_session.loadActivities(java_fields, java_filter, java_order)
            
            logger.info("Activities loaded, converting to Python data structure")
            
            # VERIFICATION POINT 2: Iterator Pattern
            # Use p6_iterator_to_list which implements while iterator.hasNext()
            activities_list = p6_iterator_to_list(iterator, ACTIVITY_FIELDS)
            
            logger.info(f"Converted {len(activities_list)} activities")
            
            # VERIFICATION POINT 1: Data Conversion
            # p6_iterator_to_list already handles Java Date conversion
            # Create DataFrame from the list of dictionaries
            df = pd.DataFrame(activities_list)
            
            logger.info(f"Created DataFrame with shape: {df.shape}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch activities: {e}")
            raise RuntimeError(f"Failed to fetch activities: {e}") from e
    
    def get_all_activities(self, filter_expr: Optional[str] = None, order_by: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch all activities from P6 (across all projects).
        
        WARNING: This can return a very large dataset. Use with caution.
        
        Args:
            filter_expr: Optional P6 filter expression
            order_by: Optional order by clause
            
        Returns:
            pd.DataFrame: DataFrame containing activity data
        """
        try:
            logger.warning("Fetching ALL activities from P6 - this may be a large dataset")
            
            # Get the P6 session object
            p6_session = self.session.session
            
            # VERIFICATION POINT 3: Schema Compliance
            import jpype
            java_fields = jpype.JArray(jpype.java.lang.String)(ACTIVITY_FIELDS)
            
            java_filter = jpype.java.lang.String(filter_expr) if filter_expr else None
            java_order = jpype.java.lang.String(order_by) if order_by else None
            
            logger.info(f"Loading activities with fields: {ACTIVITY_FIELDS}")
            if filter_expr:
                logger.info(f"Filter: {filter_expr}")
            if order_by:
                logger.info(f"Order by: {order_by}")
            
            # Load activities
            iterator = p6_session.loadActivities(java_fields, java_filter, java_order)
            
            logger.info("Activities loaded, converting to Python data structure")
            
            # VERIFICATION POINT 2: Iterator Pattern
            activities_list = p6_iterator_to_list(iterator, ACTIVITY_FIELDS)
            
            logger.info(f"Converted {len(activities_list)} activities")
            
            # Create DataFrame
            df = pd.DataFrame(activities_list)
            
            logger.info(f"Created DataFrame with shape: {df.shape}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch all activities: {e}")
            raise RuntimeError(f"Failed to fetch all activities: {e}") from e
    
    def get_activity_by_id(self, activity_id: str, project_object_id: Optional[int] = None) -> Optional[pd.DataFrame]:
        """
        Fetch a single activity by its ID.
        
        Args:
            activity_id: Activity ID (user-visible ID, not ObjectId)
            project_object_id: Optional project ObjectId to narrow search
            
        Returns:
            pd.DataFrame: DataFrame with one row, or empty DataFrame if not found
        """
        try:
            logger.info(f"Fetching activity with ID: {activity_id}")
            
            # Build filter
            filter_expr = f"Id = '{activity_id}'"
            
            if project_object_id:
                df = self.get_activities_for_project(project_object_id, filter_expr=filter_expr)
            else:
                df = self.get_all_activities(filter_expr=filter_expr)
            
            if df.empty:
                logger.warning(f"Activity not found: {activity_id}")
            else:
                logger.info(f"Found activity: {activity_id}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch activity by ID: {e}")
            raise RuntimeError(f"Failed to fetch activity by ID: {e}") from e
    
    def get_activity_by_object_id(self, object_id: int) -> Optional[pd.DataFrame]:
        """
        Fetch a single activity by its ObjectId.
        
        Args:
            object_id: Activity ObjectId (internal unique identifier)
            
        Returns:
            pd.DataFrame: DataFrame with one row, or empty DataFrame if not found
        """
        try:
            logger.info(f"Fetching activity with ObjectId: {object_id}")
            
            # Use filter to get specific activity
            filter_expr = f"ObjectId = {object_id}"
            df = self.get_all_activities(filter_expr=filter_expr)
            
            if df.empty:
                logger.warning(f"Activity not found with ObjectId: {object_id}")
            else:
                logger.info(f"Found activity with ObjectId: {object_id}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch activity by ObjectId: {e}")
            raise RuntimeError(f"Failed to fetch activity by ObjectId: {e}") from e
    
    def get_activities_by_status(self, status: str, project_object_id: Optional[int] = None) -> pd.DataFrame:
        """
        Fetch activities by status.
        
        Args:
            status: Activity status (e.g., 'Not Started', 'In Progress', 'Completed')
            project_object_id: Optional project ObjectId to filter by project
            
        Returns:
            pd.DataFrame: DataFrame containing activities with the specified status
        """
        logger.info(f"Fetching activities with status: {status}")
        
        filter_expr = f"Status = '{status}'"
        
        if project_object_id:
            return self.get_activities_for_project(project_object_id, filter_expr=filter_expr)
        else:
            return self.get_all_activities(filter_expr=filter_expr)
