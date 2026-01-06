#!/usr/bin/env python3
"""
Data Conversion Utilities
Handles conversion between Java types and Python types for P6 data.
"""

from datetime import datetime
from typing import Any, List, Dict, Optional
import jpype

from src.utils import logger


def java_date_to_python(java_date: Any) -> Optional[datetime]:
    """
    Convert Java Date to Python datetime.
    
    VERIFICATION POINT 1: Data Conversion
    This function handles java.util.Date conversion to prevent serialization errors.
    
    Args:
        java_date: Java Date object or None
        
    Returns:
        datetime: Python datetime object, or None if input is None/null
    """
    if java_date is None:
        return None
    
    try:
        # Check if it's a Java null
        if jpype.JObject(java_date, jpype.java.lang.Object) is None:
            return None
        
        # Convert Java Date to Python datetime
        # Java Date.getTime() returns milliseconds since epoch
        timestamp_ms = java_date.getTime()
        timestamp_sec = timestamp_ms / 1000.0
        return datetime.fromtimestamp(timestamp_sec)
        
    except Exception as e:
        logger.warning(f"Failed to convert Java date to Python datetime: {e}")
        return None


def java_value_to_python(value: Any) -> Any:
    """
    Convert Java value to appropriate Python type.
    
    Handles:
    - java.util.Date -> datetime
    - Java null -> None
    - Java primitives -> Python equivalents
    - Java strings -> Python strings
    
    Args:
        value: Java value of any type
        
    Returns:
        Python-compatible value
    """
    if value is None:
        return None
    
    try:
        # Check for Java null
        if jpype.JObject(value, jpype.java.lang.Object) is None:
            return None
        
        # Check if it's a Java Date
        if isinstance(value, jpype.java.util.Date):
            return java_date_to_python(value)
        
        # Check if it's a Java String
        if isinstance(value, jpype.java.lang.String):
            return str(value)
        
        # Check if it's a Java Number
        if isinstance(value, (jpype.java.lang.Integer, jpype.java.lang.Long)):
            return int(value)
        
        if isinstance(value, (jpype.java.lang.Double, jpype.java.lang.Float)):
            return float(value)
        
        # Check if it's a Java Boolean
        if isinstance(value, jpype.java.lang.Boolean):
            return bool(value)
        
        # For other types, try to convert to string
        return str(value)
        
    except Exception as e:
        logger.warning(f"Failed to convert Java value to Python: {e}")
        return None


def p6_iterator_to_list(iterator: Any, fields: List[str]) -> List[Dict[str, Any]]:
    """
    Convert P6 BOIterator to list of dictionaries.
    
    VERIFICATION POINT 2: Iterator Pattern
    Uses while iterator.hasNext() loop (direct casting to list will fail).
    
    VERIFICATION POINT 3: Schema Compliance
    Only fetches fields specified in the schema to prevent over-fetching.
    
    Args:
        iterator: P6 BOIterator object
        fields: List of field names to extract (from definitions.py)
        
    Returns:
        List of dictionaries, each representing one P6 object
    """
    results = []
    
    if iterator is None:
        logger.warning("Received None iterator")
        return results
    
    try:
        # VERIFICATION POINT 2: Iterator Pattern
        # Use hasNext() loop instead of direct list conversion
        while iterator.hasNext():
            obj = iterator.next()
            
            # Extract fields dynamically
            record = {}
            for field_name in fields:
                try:
                    # Get value using getValue() method
                    java_value = obj.getValue(field_name)
                    
                    # VERIFICATION POINT 1: Data Conversion
                    # Convert Java types to Python types
                    python_value = java_value_to_python(java_value)
                    
                    record[field_name] = python_value
                    
                except Exception as e:
                    logger.warning(f"Failed to get field '{field_name}': {e}")
                    record[field_name] = None
            
            results.append(record)
        
        logger.info(f"Converted {len(results)} objects from iterator")
        
    except Exception as e:
        logger.error(f"Error iterating through P6 objects: {e}")
    
    return results


def p6_objects_to_dict_list(objects: Any, fields: List[str]) -> List[Dict[str, Any]]:
    """
    Convert P6 objects (from iterator or collection) to list of dictionaries.
    
    This is a convenience wrapper that handles both iterators and direct object lists.
    
    Args:
        objects: P6 BOIterator or collection of P6 objects
        fields: List of field names to extract
        
    Returns:
        List of dictionaries
    """
    # Check if it's an iterator
    try:
        if hasattr(objects, 'hasNext'):
            return p6_iterator_to_list(objects, fields)
    except Exception:
        pass
    
    # If it's a list or collection, convert each object
    results = []
    try:
        for obj in objects:
            record = {}
            for field_name in fields:
                try:
                    java_value = obj.getValue(field_name)
                    python_value = java_value_to_python(java_value)
                    record[field_name] = python_value
                except Exception as e:
                    logger.warning(f"Failed to get field '{field_name}': {e}")
                    record[field_name] = None
            results.append(record)
    except Exception as e:
        logger.error(f"Error converting P6 objects: {e}")
    
    return results
