#!/usr/bin/env python3
"""
P6 Schema Definitions
Immutable constants defining the fields to retrieve from P6 entities.
This prevents over-fetching and ensures consistent data structure.
"""

from typing import List, Final

# ============================================================================
# PROJECT FIELDS
# ============================================================================

PROJECT_FIELDS: Final[List[str]] = [
    'ObjectId',       # Unique internal identifier
    'Id',             # User-visible project ID
    'Name',           # Project name
    'Status',         # Project status (e.g., Active, Completed)
    'PlanStartDate',  # Planned start date
]

# ============================================================================
# ACTIVITY FIELDS
# ============================================================================

ACTIVITY_FIELDS: Final[List[str]] = [
    'ObjectId',        # Unique internal identifier
    'Id',              # User-visible activity ID
    'Name',            # Activity name
    'Status',          # Activity status (e.g., Not Started, In Progress, Completed)
    'PlannedDuration', # Planned duration in hours
    'StartDate',       # Actual or planned start date
    'FinishDate',      # Actual or planned finish date
    'TotalFloat',      # Total float in hours (critical path indicator: <= 0 means critical)
    'ProjectObjectId', # Project reference for relationship queries
]

# ============================================================================
# RESOURCE FIELDS
# ============================================================================

RESOURCE_FIELDS: Final[List[str]] = [
    'ObjectId',        # Unique internal identifier
    'Id',              # User-visible resource ID
    'Name',            # Resource name
    'ResourceType',    # Resource type (e.g., Labor, Material, Equipment)
]

# ============================================================================
# RELATIONSHIP FIELDS
# ============================================================================

RELATIONSHIP_FIELDS: Final[List[str]] = [
    'ObjectId',                # Unique internal identifier
    'PredecessorObjectId',     # Predecessor activity reference
    'SuccessorObjectId',       # Successor activity reference
    'Type',                    # Relationship type (e.g., FS, SS, FF, SF)
    'Lag',                     # Lag time in hours
]

# ============================================================================
# FIELD VALIDATION
# ============================================================================

def validate_fields(entity_type: str, fields: List[str]) -> bool:
    """
    Validate that the requested fields are defined for the entity type.
    
    Args:
        entity_type: Type of entity (e.g., 'Project', 'Activity')
        fields: List of field names to validate
        
    Returns:
        bool: True if all fields are valid, False otherwise
    """
    valid_fields_map = {
        'Project': PROJECT_FIELDS,
        'Activity': ACTIVITY_FIELDS,
        'Resource': RESOURCE_FIELDS,
        'Relationship': RELATIONSHIP_FIELDS,
    }
    
    if entity_type not in valid_fields_map:
        return False
    
    valid_fields = set(valid_fields_map[entity_type])
    requested_fields = set(fields)
    
    return requested_fields.issubset(valid_fields)


def get_fields(entity_type: str) -> List[str]:
    """
    Get the defined fields for an entity type.
    
    Args:
        entity_type: Type of entity (e.g., 'Project', 'Activity')
        
    Returns:
        List[str]: List of field names for the entity type
        
    Raises:
        ValueError: If entity_type is not recognized
    """
    fields_map = {
        'Project': PROJECT_FIELDS,
        'Activity': ACTIVITY_FIELDS,
        'Resource': RESOURCE_FIELDS,
        'Relationship': RELATIONSHIP_FIELDS,
    }
    
    if entity_type not in fields_map:
        raise ValueError(f"Unknown entity type: {entity_type}")
    
    return fields_map[entity_type]
