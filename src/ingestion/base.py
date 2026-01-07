#!/usr/bin/env python3
"""
Base Parser Interface
Abstract base class for schedule file parsers.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional
import pandas as pd

from src.utils import logger


class ScheduleParser(ABC):
    """
    Abstract base class for schedule file parsers.
    
    All parsers must:
    1. Parse file into standardized DataFrame schema
    2. Return dict with 'projects' and 'activities' keys
    3. Align with definitions.py field names
    4. Handle encoding issues gracefully
    """
    
    def __init__(self, filepath: str, encoding: Optional[str] = None):
        """
        Initialize parser.
        
        Args:
            filepath: Path to schedule file
            encoding: File encoding (default: auto-detect)
        """
        self.filepath = Path(filepath)
        self.encoding = encoding
        
        if not self.filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        logger.info(f"Initialized {self.__class__.__name__} for: {self.filepath}")
    
    @abstractmethod
    def parse(self) -> Dict[str, pd.DataFrame]:
        """
        Parse schedule file into standardized DataFrames.
        
        VERIFICATION POINT 1: Schema Alignment
        Must map file-specific columns to standard schema defined in definitions.py.
        
        Returns:
            Dict with keys:
                - 'projects': DataFrame with PROJECT_FIELDS columns
                - 'activities': DataFrame with ACTIVITY_FIELDS columns
                - 'relationships': DataFrame with RELATIONSHIP_FIELDS columns
        """
        pass
    
    def _read_file_with_encoding(self, encodings: list = None) -> str:
        """
        Read file with encoding fallback.
        
        VERIFICATION POINT 4: Encoding
        Tries multiple encodings to handle legacy files.
        
        Args:
            encodings: List of encodings to try (default: ['utf-8', 'cp1252', 'latin-1'])
            
        Returns:
            str: File content
            
        Raises:
            RuntimeError: If all encodings fail
        """
        if encodings is None:
            # Common encodings for schedule files
            if self.encoding:
                encodings = [self.encoding]
            else:
                encodings = ['utf-8', 'cp1252', 'latin-1', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                logger.debug(f"Trying encoding: {encoding}")
                content = self.filepath.read_text(encoding=encoding)
                logger.info(f"Successfully read file with encoding: {encoding}")
                return content
            except (UnicodeDecodeError, LookupError) as e:
                logger.debug(f"Failed with encoding {encoding}: {e}")
                continue
        
        raise RuntimeError(
            f"Failed to read file with any encoding. Tried: {encodings}"
        )
    
    def _standardize_project_dataframe(self, df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
        """
        Standardize project DataFrame to match PROJECT_FIELDS schema.
        
        VERIFICATION POINT 1: Schema Alignment
        Maps file-specific columns to standard schema.
        
        Args:
            df: Raw DataFrame from file
            mapping: Dict mapping {file_column: standard_column}
            
        Returns:
            pd.DataFrame: Standardized DataFrame
        """
        from src.core.definitions import PROJECT_FIELDS
        
        # Rename columns according to mapping
        df = df.rename(columns=mapping)
        
        # Ensure all required fields exist (fill with None if missing)
        for field in PROJECT_FIELDS:
            if field not in df.columns:
                df[field] = None
        
        # Select only standard fields
        df = df[PROJECT_FIELDS]
        
        logger.debug(f"Standardized project DataFrame: {df.shape}")
        return df
    
    def _standardize_activity_dataframe(self, df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
        """
        Standardize activity DataFrame to match ACTIVITY_FIELDS schema.
        
        VERIFICATION POINT 1: Schema Alignment
        Maps file-specific columns to standard schema.
        
        Args:
            df: Raw DataFrame from file
            mapping: Dict mapping {file_column: standard_column}
            
        Returns:
            pd.DataFrame: Standardized DataFrame
        """
        from src.core.definitions import ACTIVITY_FIELDS
        
        # Rename columns according to mapping
        df = df.rename(columns=mapping)
        
        # Ensure all required fields exist (fill with None if missing)
        for field in ACTIVITY_FIELDS:
            if field not in df.columns:
                df[field] = None
        
        # Select only standard fields
        df = df[ACTIVITY_FIELDS]
        
        logger.debug(f"Standardized activity DataFrame: {df.shape}")
        return df
    
    def _standardize_relationship_dataframe(self, df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
        """
        Standardize relationship DataFrame to match RELATIONSHIP_FIELDS schema.
        
        VERIFICATION POINT 1: Schema Alignment
        Maps file-specific columns to standard schema.
        
        Args:
            df: Raw DataFrame from file
            mapping: Dict mapping {file_column: standard_column}
            
        Returns:
            pd.DataFrame: Standardized DataFrame
        """
        from src.core.definitions import RELATIONSHIP_FIELDS
        
        # Rename columns according to mapping
        df = df.rename(columns=mapping)
        
        # Ensure all required fields exist (fill with None if missing)
        for field in RELATIONSHIP_FIELDS:
            if field not in df.columns:
                df[field] = None
        
        # Select only standard fields
        df = df[RELATIONSHIP_FIELDS]
        
        logger.debug(f"Standardized relationship DataFrame: {df.shape}")
        return df
    
    def validate_result(self, result: Dict[str, pd.DataFrame]) -> bool:
        """
        Validate parser result.
        
        Args:
            result: Parser result dict
            
        Returns:
            bool: True if valid
        """
        if not isinstance(result, dict):
            logger.error("Result must be a dictionary")
            return False
        
        required_keys = ['projects', 'activities', 'relationships']
        for key in required_keys:
            if key not in result:
                logger.error(f"Result must contain '{key}' key")
                return False
            
            if not isinstance(result[key], pd.DataFrame):
                logger.error(f"'{key}' must be a DataFrame")
                return False
        
        logger.info(
            f"Validation passed: {len(result['projects'])} projects, "
            f"{len(result['activities'])} activities, "
            f"{len(result['relationships'])} relationships"
        )
        return True
