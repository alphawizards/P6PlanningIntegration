#!/usr/bin/env python3
"""
Relationship Data Access Object
Handles CRUD operations for P6 Relationships (logic network).
"""

import jpype
import pandas as pd
from typing import Optional

from src.core.definitions import RELATIONSHIP_FIELDS
from src.utils import logger, p6_iterator_to_list


class RelationshipDAO:
    """
    Data Access Object for P6 Relationships.
    
    Provides methods to read and write relationship (predecessor/successor) data.
    """
    
    def __init__(self, session):
        """
        Initialize RelationshipDAO.
        
        Args:
            session: Active P6Session instance
            
        Raises:
            ValueError: If session is not active
        """
        if not session or not session.is_active():
            raise ValueError("RelationshipDAO requires an active P6Session")
        
        self.session = session
        logger.info("RelationshipDAO initialized")
    
    def get_relationships(self, project_object_id: Optional[int] = None) -> pd.DataFrame:
        """
        Get relationships (logic network) for a project.
        
        Args:
            project_object_id: Project ObjectId to filter by (None for all)
            
        Returns:
            pd.DataFrame: Relationships with RELATIONSHIP_FIELDS columns
        """
        try:
            logger.info(f"Fetching relationships for project: {project_object_id or 'all'}")
            
            # Get RelationshipManager
            rel_manager = self.session.get_global_object('RelationshipManager')
            
            # Build filter
            if project_object_id:
                filter_str = f"PredecessorActivity.ProjectObjectId = {project_object_id}"
            else:
                filter_str = None
            
            # Load relationships
            logger.debug(f"Loading relationships with filter: {filter_str}")
            
            # Create field array for JPype
            fields_array = jpype.JArray(jpype.JString)(RELATIONSHIP_FIELDS)
            
            if filter_str:
                relationships_iterator = rel_manager.loadRelationships(
                    fields_array,
                    filter_str,
                    None  # No ordering
                )
            else:
                relationships_iterator = rel_manager.loadAllRelationships(fields_array)
            
            # Convert to list of dicts
            relationships_list = p6_iterator_to_list(relationships_iterator, RELATIONSHIP_FIELDS)
            
            # Create DataFrame
            df = pd.DataFrame(relationships_list)
            
            if df.empty:
                logger.warning("No relationships found")
                return pd.DataFrame(columns=RELATIONSHIP_FIELDS)
            
            logger.info(f"✓ Fetched {len(df)} relationships")
            return df
            
        except jpype.JException as e:
            logger.error(f"Java exception while fetching relationships: {e}")
            raise RuntimeError(f"Failed to fetch relationships: {e}") from e
        except Exception as e:
            logger.error(f"Failed to fetch relationships: {e}")
            raise
    
    def add_relationship(
        self,
        predecessor_object_id: int,
        successor_object_id: int,
        link_type: str = 'FS',
        lag: float = 0.0
    ) -> bool:
        """
        Add a new relationship (logic link) between activities.
        
        VERIFICATION POINT 1: Write Safety
        Checks SAFE_MODE before allowing write operations.
        
        Args:
            predecessor_object_id: Predecessor activity ObjectId
            successor_object_id: Successor activity ObjectId
            link_type: Relationship type ('FS', 'SS', 'FF', 'SF')
            lag: Lag time in hours
            
        Returns:
            bool: True if successful
            
        Raises:
            PermissionError: If SAFE_MODE is enabled
            RuntimeError: If operation fails
        """
        # VERIFICATION POINT 1: Write Safety Check
        self.session.check_safe_mode()
        
        try:
            logger.info(
                f"Adding relationship: {predecessor_object_id} -> {successor_object_id} "
                f"(Type: {link_type}, Lag: {lag})"
            )
            
            # VERIFICATION POINT 3: Transaction Atomicity
            self.session.begin_transaction()
            
            try:
                # Get ActivityManager
                activity_manager = self.session.get_global_object('ActivityManager')
                
                # Load predecessor and successor activities
                pred_activity = activity_manager.loadActivity(jpype.JInt(predecessor_object_id))
                succ_activity = activity_manager.loadActivity(jpype.JInt(successor_object_id))
                
                if not pred_activity or not succ_activity:
                    raise ValueError("Could not load predecessor or successor activity")
                
                # Create relationship
                relationship = succ_activity.createPredecessor(pred_activity)
                
                # VERIFICATION POINT 2: Java Casting
                # Set relationship type
                relationship.setType(jpype.JString(link_type))
                
                # Set lag (convert to Java Double)
                relationship.setLag(jpype.JDouble(lag))
                
                # Save relationship
                relationship.update()
                
                # VERIFICATION POINT 3: Commit Transaction
                self.session.commit_transaction()
                
                logger.info(f"✓ Relationship added successfully")
                return True
                
            except Exception as e:
                # VERIFICATION POINT 3: Rollback on Error
                self.session.rollback_transaction()
                raise
            
        except jpype.JException as e:
            logger.error(f"Java exception while adding relationship: {e}")
            raise RuntimeError(f"Failed to add relationship: {e}") from e
        except Exception as e:
            logger.error(f"Failed to add relationship: {e}")
            raise
    
    def delete_relationship(self, relationship_object_id: int) -> bool:
        """
        Delete a relationship.
        
        VERIFICATION POINT 1: Write Safety
        Checks SAFE_MODE before allowing write operations.
        
        Args:
            relationship_object_id: Relationship ObjectId to delete
            
        Returns:
            bool: True if successful
            
        Raises:
            PermissionError: If SAFE_MODE is enabled
            RuntimeError: If operation fails
        """
        # VERIFICATION POINT 1: Write Safety Check
        self.session.check_safe_mode()
        
        try:
            logger.info(f"Deleting relationship: {relationship_object_id}")
            
            # VERIFICATION POINT 3: Transaction Atomicity
            self.session.begin_transaction()
            
            try:
                # Get RelationshipManager
                rel_manager = self.session.get_global_object('RelationshipManager')
                
                # Load relationship
                relationship = rel_manager.loadRelationship(jpype.JInt(relationship_object_id))
                
                if not relationship:
                    raise ValueError(f"Relationship not found: {relationship_object_id}")
                
                # Delete relationship
                relationship.delete()
                
                # VERIFICATION POINT 3: Commit Transaction
                self.session.commit_transaction()
                
                logger.info(f"✓ Relationship deleted successfully")
                return True
                
            except Exception as e:
                # VERIFICATION POINT 3: Rollback on Error
                self.session.rollback_transaction()
                raise
            
        except jpype.JException as e:
            logger.error(f"Java exception while deleting relationship: {e}")
            raise RuntimeError(f"Failed to delete relationship: {e}") from e
        except Exception as e:
            logger.error(f"Failed to delete relationship: {e}")
            raise
