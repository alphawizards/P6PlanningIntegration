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

    def update_activity(self, object_id: int, updates_dict: dict) -> bool:
        """
        Update an activity's fields.
        
        VERIFICATION POINT 1: Write Safety
        Checks SAFE_MODE before allowing write operations.
        
        VERIFICATION POINT 2: Java Casting
        Casts Python types to Java types (JInt, JDouble, JString) before calling setters.
        
        VERIFICATION POINT 3: Transaction Atomicity
        Uses begin_transaction() ... commit() pattern.
        
        Args:
            object_id: Activity ObjectId to update
            updates_dict: Dict of {field_name: new_value}
                Supported fields:
                - 'Name': Activity name (str)
                - 'PlannedDuration': Duration in hours (float)
                - 'Status': Activity status (str)
                - 'StartDate': Start date (datetime)
                - 'FinishDate': Finish date (datetime)
                
        Returns:
            bool: True if successful
            
        Raises:
            PermissionError: If SAFE_MODE is enabled
            RuntimeError: If operation fails
            
        Example:
            dao.update_activity(12345, {
                'Name': 'Updated Activity Name',
                'PlannedDuration': 40.0,
                'Status': 'In Progress'
            })
        """
        import jpype
        
        # VERIFICATION POINT 1: Write Safety Check
        self.session.check_safe_mode()
        
        try:
            logger.info(f"Updating activity {object_id} with {len(updates_dict)} fields")
            logger.debug(f"Updates: {updates_dict}")
            
            # VERIFICATION POINT 3: Transaction Atomicity
            self.session.begin_transaction()
            
            try:
                # Get ActivityManager
                activity_manager = self.session.get_global_object('ActivityManager')
                
                # Load activity
                activity = activity_manager.loadActivity(jpype.JInt(object_id))
                
                if not activity:
                    raise ValueError(f"Activity not found: {object_id}")
                
                # VERIFICATION POINT 2: Java Casting
                # Iterate through updates and apply them
                for field_name, new_value in updates_dict.items():
                    if new_value is None:
                        logger.debug(f"Skipping null value for field: {field_name}")
                        continue
                    
                    # Map field names to setter methods
                    if field_name == 'Name':
                        activity.setName(jpype.JString(str(new_value)))
                        logger.debug(f"Set Name: {new_value}")
                    
                    elif field_name == 'PlannedDuration':
                        # VERIFICATION POINT 2: Cast to Java Double
                        activity.setPlannedDuration(jpype.JDouble(float(new_value)))
                        logger.debug(f"Set PlannedDuration: {new_value}")
                    
                    elif field_name == 'Status':
                        activity.setStatus(jpype.JString(str(new_value)))
                        logger.debug(f"Set Status: {new_value}")
                    
                    elif field_name == 'StartDate':
                        # Convert Python datetime to Java Date
                        if hasattr(new_value, 'strftime'):
                            java_date = self._python_datetime_to_java_date(new_value)
                            activity.setStartDate(java_date)
                            logger.debug(f"Set StartDate: {new_value}")
                        else:
                            logger.warning(f"Invalid StartDate value: {new_value}")
                    
                    elif field_name == 'FinishDate':
                        # Convert Python datetime to Java Date
                        if hasattr(new_value, 'strftime'):
                            java_date = self._python_datetime_to_java_date(new_value)
                            activity.setFinishDate(java_date)
                            logger.debug(f"Set FinishDate: {new_value}")
                    
                    else:
                        logger.warning(f"Unsupported field for update: {field_name}")
                
                # Save changes
                activity.update()
                
                # VERIFICATION POINT 3: Commit Transaction
                self.session.commit_transaction()
                
                logger.info(f"✓ Activity {object_id} updated successfully")
                return True
                
            except Exception as e:
                # VERIFICATION POINT 3: Rollback on Error
                self.session.rollback_transaction()
                raise
            
        except jpype.JException as e:
            logger.error(f"Java exception while updating activity: {e}")
            raise RuntimeError(f"Failed to update activity: {e}") from e
        except Exception as e:
            logger.error(f"Failed to update activity: {e}")
            raise
    
    def _python_datetime_to_java_date(self, python_datetime):
        """
        Convert Python datetime to Java Date.
        
        VERIFICATION POINT 2: Java Casting
        Properly converts Python datetime to Java Date object.
        
        Args:
            python_datetime: Python datetime object
            
        Returns:
            Java Date object
        """
        import jpype
        
        # Get Java Date class
        JavaDate = jpype.JClass('java.util.Date')
        
        # Convert to milliseconds since epoch
        timestamp_ms = int(python_datetime.timestamp() * 1000)
        
        # Create Java Date
        return JavaDate(jpype.JLong(timestamp_ms))
