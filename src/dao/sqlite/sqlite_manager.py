#!/usr/bin/env python3
"""
SQLite Database Manager for P6 Professional Standalone.
Provides read-only access to the P6 SQLite database.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.config import P6_DB_PATH, SAFE_MODE
from src.utils import logger
from .schema_validator import validate_schema


class SQLiteManager:
    """
    SQLite connection manager for P6 Professional Standalone databases.
    
    SAFETY: Opens database in READ-ONLY mode to prevent accidental corruption.
    
    Usage:
        with SQLiteManager() as manager:
            project_dao = manager.get_project_dao()
            projects = project_dao.get_all_projects()
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize SQLite manager.
        
        Args:
            db_path: Optional path to SQLite database. Defaults to P6_DB_PATH from config.
        """
        self.db_path = db_path or P6_DB_PATH
        self.connection: Optional[sqlite3.Connection] = None
        self.safe_mode = SAFE_MODE
        self._connection_timestamp: Optional[datetime] = None
        self._schema_valid: bool = False
        self._project_dao = None
        self._activity_dao = None
        self._relationship_dao = None
        self._wbs_dao = None
        
        logger.info(f"SQLiteManager initialized with db_path: {self.db_path}")
    
    def connect(self) -> bool:
        """
        Connect to the SQLite database in READ-ONLY mode.
        
        Returns:
            bool: True if connection successful
            
        Raises:
            RuntimeError: If connection fails
        """
        try:
            if self.connection is not None:
                logger.warning("Already connected to SQLite database")
                return True
            
            # Validate path exists
            db_path = Path(self.db_path)
            if not db_path.exists():
                raise RuntimeError(f"SQLite database not found: {self.db_path}")
            
            # Connect in IMMUTABLE mode using URI syntax
            # This prevents writes AND avoids needing lock files in the directory
            # Perfect for reading from protected folders like Program Files
            uri = f"file:{self.db_path}?immutable=1"
            self.connection = sqlite3.connect(uri, uri=True)
            
            # Enable row factory for dictionary-like access
            self.connection.row_factory = sqlite3.Row
            
            logger.info(f"Connected to Standalone DB: {self.db_path}")
            logger.info("Database opened in IMMUTABLE mode (read-only, no lock files)")
            
            # Track connection timestamp for data freshness
            self._connection_timestamp = datetime.now()
            
            # Validate schema on connect
            self._schema_valid = validate_schema(self.connection)
            if not self._schema_valid:
                logger.warning("Schema validation failed - some features may not work")
            
            return True
            
        except sqlite3.Error as e:
            logger.error(f"SQLite connection error: {e}")
            raise RuntimeError(f"Failed to connect to SQLite database: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error connecting to SQLite: {e}")
            raise RuntimeError(f"Failed to connect to SQLite database: {e}") from e
    
    def disconnect(self) -> None:
        """Disconnect from the SQLite database."""
        if self.connection is not None:
            try:
                self.connection.close()
                logger.info("SQLite connection closed")
            except Exception as e:
                logger.error(f"Error closing SQLite connection: {e}")
            finally:
                self.connection = None
                self._project_dao = None
                self._activity_dao = None
                self._relationship_dao = None
    
    def is_connected(self) -> bool:
        """Check if connected to the database."""
        return self.connection is not None
    
    def is_active(self) -> bool:
        """Alias for is_connected() for compatibility with P6Session interface."""
        return self.is_connected()
    
    def get_connection_timestamp(self) -> Optional[datetime]:
        """
        Get the timestamp when the connection was established.
        
        Useful for tracking data freshness with immutable mode.
        
        Returns:
            datetime when connected, or None if not connected
        """
        return self._connection_timestamp
    
    def is_schema_valid(self) -> bool:
        """
        Check if the schema validation passed.
        
        Returns:
            True if all required columns are present
        """
        return self._schema_valid
    
    def refresh_connection(self) -> bool:
        """
        Close and reopen the database connection.
        
        Use this to get fresh data when database has been modified.
        Note: This will invalidate any cached DAOs.
        
        Returns:
            True if reconnection successful
        """
        logger.info("Refreshing SQLite connection...")
        self.disconnect()
        return self.connect()
    
    def __enter__(self):
        """Context manager entry: connect to database."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: disconnect from database."""
        self.disconnect()
        return False
    
    def get_cursor(self) -> sqlite3.Cursor:
        """
        Get a cursor for executing SQL queries.
        
        Returns:
            sqlite3.Cursor: Database cursor
            
        Raises:
            RuntimeError: If not connected
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to SQLite database")
        return self.connection.cursor()
    
    def get_project_dao(self):
        """
        Get the Project DAO instance.
        
        Returns:
            SQLiteProjectDAO: Project data access object
        """
        if self._project_dao is None:
            from .project_dao import SQLiteProjectDAO
            self._project_dao = SQLiteProjectDAO(self)
        return self._project_dao
    
    def get_activity_dao(self):
        """
        Get the Activity DAO instance.
        
        Returns:
            SQLiteActivityDAO: Activity data access object
        """
        if self._activity_dao is None:
            from .activity_dao import SQLiteActivityDAO
            self._activity_dao = SQLiteActivityDAO(self)
        return self._activity_dao
    
    def get_relationship_dao(self):
        """
        Get the Relationship DAO instance.
        
        Returns:
            SQLiteRelationshipDAO: Relationship data access object
        """
        if self._relationship_dao is None:
            from .relationship_dao import SQLiteRelationshipDAO
            self._relationship_dao = SQLiteRelationshipDAO(self)
        return self._relationship_dao

    def get_wbs_dao(self):
        """
        Get the WBS DAO instance.
        
        Returns:
            SQLiteWBSDAO: WBS data access object
        """
        if self._wbs_dao is None:
            from .wbs_dao import SQLiteWBSDAO
            self._wbs_dao = SQLiteWBSDAO(self)
        return self._wbs_dao
    
    def check_safe_mode(self) -> None:
        """
        Check if safe mode is enabled.
        
        Note: SQLite mode is always read-only, but this provides
        compatibility with P6Session interface.
        
        Raises:
            RuntimeError: If safe mode is enabled
        """
        if self.safe_mode:
            raise RuntimeError(
                "SAFE_MODE is enabled. Write operations are blocked. "
                "Set SAFE_MODE=false in .env to enable writes."
            )
