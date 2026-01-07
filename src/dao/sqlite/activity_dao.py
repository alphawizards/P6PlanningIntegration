#!/usr/bin/env python3
"""
SQLite Activity DAO for P6 Professional Standalone.
Read-only access to TASK table with schema-matched column aliases.

IMPORTANT: Duration fields are stored in HOURS in P6 SQLite.
This DAO divides by 8.0 to convert to DAYS for the AI Agent.
"""

from typing import Optional
import pandas as pd

from src.core.definitions import ACTIVITY_FIELDS
from src.utils import logger


class SQLiteActivityDAO:
    """
    Data Access Object for P6 Activities via SQLite.
    
    Schema Mapping (P6 SQLite -> Agent Schema):
        task_id              -> ObjectId
        task_code            -> Id
        task_name            -> Name
        status_code          -> Status
        target_drtn_hr_cnt/8 -> PlannedDuration (Hours -> Days)
        early_start_date     -> StartDate
        early_end_date       -> FinishDate
        act_start_date       -> ActualStartDate
        act_end_date         -> ActualFinishDate
        task_type            -> Type
        cstr_type            -> ConstraintType
        total_float_hr_cnt/8 -> TotalFloat (Hours -> Days)
        proj_id              -> ProjectObjectId
    
    VERIFICATION POINT: Duration Math
    P6 stores durations in Hours. We divide by 8.0 to match Agent's Days expectation.
    """
    
    # SQL query with schema-matched aliases and duration conversion
    BASE_QUERY = """
        SELECT 
            task_id as ObjectId,
            task_code as Id,
            task_name as Name,
            status_code as Status,
            COALESCE(target_drtn_hr_cnt, 0) / 8.0 as PlannedDuration,
            early_start_date as StartDate,
            early_end_date as FinishDate,
            act_start_date as ActualStartDate,
            act_end_date as ActualFinishDate,
            task_type as Type,
            cstr_type as ConstraintType,
            COALESCE(total_float_hr_cnt, 0) / 8.0 as TotalFloat,
            proj_id as ProjectObjectId
        FROM TASK
    """
    
    def __init__(self, manager):
        """
        Initialize SQLiteActivityDAO with a SQLiteManager.
        
        Args:
            manager: SQLiteManager instance (must be connected)
        """
        if manager is None or not manager.is_connected():
            raise ValueError("SQLiteActivityDAO requires a connected SQLiteManager")
        
        self.manager = manager
        logger.info("SQLiteActivityDAO initialized")
    
    def get_activities_for_project(
        self, 
        project_object_id: int, 
        filter_expr: Optional[str] = None, 
        order_by: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch all activities for a specific project.
        
        Args:
            project_object_id: Project ObjectId (proj_id)
            filter_expr: Optional additional SQL WHERE clause
            order_by: Optional ORDER BY clause
            
        Returns:
            pd.DataFrame: DataFrame with ACTIVITY_FIELDS columns
        """
        try:
            logger.info(f"Fetching activities for project ObjectId: {project_object_id}")
            
            query = self.BASE_QUERY + " WHERE proj_id = ?"
            params = [project_object_id]
            
            if filter_expr:
                query += f" AND ({filter_expr})"
                logger.info(f"Additional filter: {filter_expr}")
            
            if order_by:
                query += f" ORDER BY {order_by}"
            else:
                query += " ORDER BY task_code"  # Default ordering
            
            cursor = self.manager.get_cursor()
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            activities = [dict(row) for row in rows]
            
            logger.info(f"Fetched {len(activities)} activities")
            
            if activities:
                df = pd.DataFrame(activities)
            else:
                df = pd.DataFrame(columns=ACTIVITY_FIELDS)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch activities: {e}")
            raise RuntimeError(f"Failed to fetch activities: {e}") from e
    
    def get_all_activities(
        self, 
        filter_expr: Optional[str] = None, 
        order_by: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch all activities from the database (across all projects).
        
        WARNING: This can return a very large dataset.
        
        Args:
            filter_expr: Optional SQL WHERE clause
            order_by: Optional ORDER BY clause
            
        Returns:
            pd.DataFrame: DataFrame with ACTIVITY_FIELDS columns
        """
        try:
            logger.info("Fetching all activities from SQLite")
            
            query = self.BASE_QUERY
            
            if filter_expr:
                query += f" WHERE {filter_expr}"
            
            if order_by:
                query += f" ORDER BY {order_by}"
            else:
                query += " ORDER BY proj_id, task_code"
            
            cursor = self.manager.get_cursor()
            cursor.execute(query)
            
            rows = cursor.fetchall()
            activities = [dict(row) for row in rows]
            
            logger.info(f"Fetched {len(activities)} activities")
            
            if activities:
                df = pd.DataFrame(activities)
            else:
                df = pd.DataFrame(columns=ACTIVITY_FIELDS)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch all activities: {e}")
            raise RuntimeError(f"Failed to fetch all activities: {e}") from e
    
    def get_activity_by_id(
        self, 
        activity_id: str, 
        project_object_id: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Fetch a single activity by its user-visible ID.
        
        Args:
            activity_id: Activity ID (task_code)
            project_object_id: Optional project filter
            
        Returns:
            pd.DataFrame: DataFrame with one row, or empty if not found
        """
        try:
            logger.info(f"Fetching activity with ID: {activity_id}")
            
            query = self.BASE_QUERY + " WHERE task_code = ?"
            params = [activity_id]
            
            if project_object_id is not None:
                query += " AND proj_id = ?"
                params.append(project_object_id)
            
            cursor = self.manager.get_cursor()
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            activities = [dict(row) for row in rows]
            
            if activities:
                df = pd.DataFrame(activities)
                logger.info(f"Found activity: {activity_id}")
            else:
                df = pd.DataFrame(columns=ACTIVITY_FIELDS)
                logger.warning(f"Activity not found: {activity_id}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch activity by ID: {e}")
            raise RuntimeError(f"Failed to fetch activity by ID: {e}") from e
    
    def get_activity_by_object_id(self, object_id: int) -> pd.DataFrame:
        """
        Fetch a single activity by its ObjectId.
        
        Args:
            object_id: Activity ObjectId (task_id)
            
        Returns:
            pd.DataFrame: DataFrame with one row, or empty if not found
        """
        try:
            logger.info(f"Fetching activity with ObjectId: {object_id}")
            
            query = self.BASE_QUERY + " WHERE task_id = ?"
            
            cursor = self.manager.get_cursor()
            cursor.execute(query, (object_id,))
            
            rows = cursor.fetchall()
            activities = [dict(row) for row in rows]
            
            if activities:
                df = pd.DataFrame(activities)
                logger.info(f"Found activity with ObjectId: {object_id}")
            else:
                df = pd.DataFrame(columns=ACTIVITY_FIELDS)
                logger.warning(f"Activity not found with ObjectId: {object_id}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch activity by ObjectId: {e}")
            raise RuntimeError(f"Failed to fetch activity by ObjectId: {e}") from e
    
    def get_activities_by_status(
        self, 
        status: str, 
        project_object_id: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Fetch activities by status.
        
        Args:
            status: Activity status code
            project_object_id: Optional project filter
            
        Returns:
            pd.DataFrame: DataFrame with matching activities
        """
        filter_expr = f"status_code = '{status}'"
        
        if project_object_id is not None:
            return self.get_activities_for_project(project_object_id, filter_expr=filter_expr)
        else:
            return self.get_all_activities(filter_expr=filter_expr)
    
    def update_activity(self, object_id: int, updates_dict: dict):
        """
        Update an activity's fields.
        
        VERIFICATION POINT: Write Protection
        SQLite mode is READ-ONLY. This method always raises NotImplementedError.
        
        Args:
            object_id: Activity ObjectId
            updates_dict: Dictionary of field updates
            
        Raises:
            NotImplementedError: Always - SQLite mode is read-only
        """
        raise NotImplementedError(
            "SQLite mode is READ-ONLY. Use P6 Professional application to modify activities. "
            "Activity updates cannot be performed through this interface to prevent database corruption."
        )

    def get_critical_activities(self, project_object_id: int) -> pd.DataFrame:
        """
        Fetch critical activities (Total Float <= 0).
        
        Args:
            project_object_id: Project ObjectId
            
        Returns:
            pd.DataFrame: Critical activities
        """
        # Float stored in hours. 0 hours = 0 days.
        # Use small epsilon for float comparison safety
        return self.get_activities_for_project(
            project_object_id, 
            filter_expr="total_float_hr_cnt <= 0.01"
        )
    
    def get_near_critical_activities(
        self, 
        project_object_id: int, 
        threshold_days: float = 10.0
    ) -> pd.DataFrame:
        """
        Fetch near-critical activities (0 < Total Float <= threshold).
        
        Args:
            project_object_id: Project ObjectId
            threshold_days: Float threshold in days (default 10)
            
        Returns:
            pd.DataFrame: Near-critical activities
        """
        threshold_hours = threshold_days * 8.0
        filter_expr = f"total_float_hr_cnt > 0.01 AND total_float_hr_cnt <= {threshold_hours}"
        
        return self.get_activities_for_project(
            project_object_id, 
            filter_expr=filter_expr
        )

    def get_activities_by_float_range(
        self, 
        project_object_id: int, 
        min_float_days: float, 
        max_float_days: float
    ) -> pd.DataFrame:
        """
        Fetch activities with float within a specific range.
        
        Args:
            project_object_id: Project ObjectId
            min_float_days: Minimum float in days
            max_float_days: Maximum float in days
            
        Returns:
            pd.DataFrame: Matching activities
        """
        min_hours = min_float_days * 8.0
        max_hours = max_float_days * 8.0
        filter_expr = f"total_float_hr_cnt >= {min_hours} AND total_float_hr_cnt <= {max_hours}"
        
        return self.get_activities_for_project(
            project_object_id, 
            filter_expr=filter_expr
        )
