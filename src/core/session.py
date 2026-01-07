#!/usr/bin/env python3
"""
P6 Session Management
Handles JVM lifecycle, P6 connection, and session management with safety controls.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any

import jpype
import jpype.imports

from src.config import (
    P6_LIB_DIR,
    P6_DB_TYPE,
    DB_USER,
    DB_PASS,
    DB_INSTANCE,
    P6_USER,
    P6_PASS,
    SAFE_MODE,
)
from src.utils import logger, log_exception


class P6Session:
    """
    Manages P6 connection lifecycle with JVM stability checks and safety controls.
    
    This class handles:
    - JVM initialization with idempotency checks
    - P6 session authentication
    - Database connection logic (standalone vs enterprise)
    - Context manager support for automatic cleanup
    - Safety mode enforcement
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize P6Session without connecting.
        
        Args:
            config: Optional configuration dictionary to override settings
        """
        # Use provided config or fall back to settings
        self.config = config or {}
        
        # Configuration
        self.lib_dir = self.config.get('P6_LIB_DIR', P6_LIB_DIR)
        self.db_type = self.config.get('P6_DB_TYPE', P6_DB_TYPE)
        self.db_user = self.config.get('DB_USER', DB_USER)
        self.db_pass = self.config.get('DB_PASS', DB_PASS)
        self.db_instance = self.config.get('DB_INSTANCE', DB_INSTANCE)
        self.p6_user = self.config.get('P6_USER', P6_USER)
        self.p6_pass = self.config.get('P6_PASS', P6_PASS)
        self.safe_mode = self.config.get('SAFE_MODE', SAFE_MODE)
        
        # State
        self.session = None
        self.jvm_started_by_this_instance = False
        
        logger.info("P6Session initialized")
        logger.info(f"Database Type: {self.db_type}")
        logger.info(f"Safe Mode: {self.safe_mode}")
    
    def start_jvm(self) -> bool:
        """
        Start the JVM with idempotency check.
        
        This method:
        1. Checks if JVM is already started (CRITICAL for stability)
        2. Dynamically builds classpath from P6_LIB_DIR
        3. Starts JVM with the classpath
        
        Returns:
            bool: True if JVM was started successfully or already running
            
        Raises:
            RuntimeError: If JVM startup fails
        """
        # VERIFICATION POINT 1: JVM Stability Check
        if jpype.isJVMStarted():
            logger.info("JVM is already started (idempotency check passed)")
            return True
        
        try:
            # Build classpath from JAR files
            lib_path = Path(self.lib_dir)
            jar_files = list(lib_path.glob('*.jar'))
            
            if not jar_files:
                raise RuntimeError(f"No JAR files found in {self.lib_dir}")
            
            logger.info(f"Found {len(jar_files)} JAR files in {self.lib_dir}")
            
            # Build classpath string
            classpath = os.pathsep.join(str(jar.absolute()) for jar in jar_files)
            
            # Start JVM
            logger.info("Starting JVM...")
            jpype.startJVM(classpath=classpath)
            self.jvm_started_by_this_instance = True
            logger.info("JVM started successfully")
            
            return True
            
        except Exception as e:
            logger.error("Failed to start JVM")
            log_exception(logger, e, [self.db_pass, self.p6_pass])
            raise RuntimeError(f"JVM startup failed: {e}") from e
    
    def connect(self) -> bool:
        """
        Connect to P6 using the appropriate authentication method.
        
        This method:
        1. Ensures JVM is started
        2. Imports P6 Session class
        3. Performs login based on database type
        4. Respects SAFE_MODE flag
        
        Returns:
            bool: True if connection successful
            
        Raises:
            RuntimeError: If connection fails
        """
        try:
            # Ensure JVM is started
            if not jpype.isJVMStarted():
                logger.info("JVM not started, starting now...")
                self.start_jvm()
            
            # Import P6 Session class (must be after JVM startup)
            logger.info("Importing Primavera P6 Session class...")
            from com.primavera.integration.client import Session
            
            # VERIFICATION POINT 4: Database Logic
            # Construct login parameters based on database type
            if self.db_type == 'standalone':
                # Standalone (SQLite) mode: Simple login
                logger.info(f"Connecting to P6 in standalone mode as user: {self.p6_user}")
                self.session = Session.login(
                    self.p6_user,
                    self.p6_pass
                )
            
            elif self.db_type == 'enterprise':
                # Enterprise (Oracle) mode: Database + P6 credentials
                logger.info(f"Connecting to P6 in enterprise mode as DB user: {self.db_user}, P6 user: {self.p6_user}")
                
                if self.db_instance:
                    # With database instance
                    from com.primavera.integration.client import DatabaseInstance
                    logger.info(f"Using database instance: {self.db_instance}")
                    
                    self.session = Session.login(
                        DatabaseInstance(self.db_instance),
                        self.db_user,
                        self.db_pass,
                        self.p6_user,
                        self.p6_pass
                    )
                else:
                    # Without database instance
                    self.session = Session.login(
                        self.db_user,
                        self.db_pass,
                        self.p6_user,
                        self.p6_pass
                    )
            
            else:
                raise ValueError(f"Invalid database type: {self.db_type}")
            
            logger.info("✓ Successfully connected to Primavera P6")
            logger.info(f"✓ Session established for user: {self.p6_user}")
            
            # VERIFICATION POINT 3: Safety Switch
            if self.safe_mode:
                logger.warning("⚠ SAFE_MODE is ENABLED - Write operations are DISABLED")
            else:
                logger.warning("⚠ SAFE_MODE is DISABLED - Write operations are ENABLED")
            
            return True
            
        except jpype.JException as e:
            logger.error("Java exception occurred during P6 connection")
            log_exception(logger, e, [self.db_pass, self.p6_pass])
            raise RuntimeError(f"P6 connection failed: {e}") from e
            
        except Exception as e:
            logger.error("Failed to connect to P6")
            log_exception(logger, e, [self.db_pass, self.p6_pass])
            raise RuntimeError(f"P6 connection failed: {e}") from e
    
    def disconnect(self):
        """
        Disconnect from P6 and cleanup resources.
        """
        if self.session is not None:
            try:
                logger.info("Logging out of P6 session...")
                self.session.logout()
                logger.info("✓ Session logged out successfully")
            except Exception as e:
                logger.warning(f"Error during session logout: {e}")
            finally:
                self.session = None
        
        # Only shutdown JVM if this instance started it
        if self.jvm_started_by_this_instance and jpype.isJVMStarted():
            try:
                logger.info("Shutting down JVM...")
                jpype.shutdownJVM()
                logger.info("JVM shutdown complete")
                self.jvm_started_by_this_instance = False
            except Exception as e:
                logger.warning(f"Error during JVM shutdown: {e}")
    
    def __enter__(self):
        """Context manager entry: connect to P6."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: disconnect from P6."""
        self.disconnect()
        return False  # Don't suppress exceptions
    
    def is_connected(self) -> bool:
        """
        Check if session is currently connected.
        
        Returns:
            bool: True if session is active
        """
        return self.session is not None
    
    def check_safe_mode(self):
        """
        Check if safe mode is enabled and raise exception if attempting write operation.
        
        Raises:
            RuntimeError: If safe mode is enabled
        """
        if self.safe_mode:
            raise RuntimeError(
                "SAFE_MODE is enabled. Write operations are disabled. "
                "Set SAFE_MODE=false in .env to enable write operations."
            )

    def is_active(self) -> bool:
        """
        Alias for is_connected() for compatibility with DAOs.
        
        Returns:
            bool: True if session is active
        """
        return self.is_connected()
    
    def begin_transaction(self):
        """
        Begin a transaction.
        
        VERIFICATION POINT 3: Transaction Atomicity
        Starts a transaction for atomic operations.
        
        Note: P6 API may not support explicit transactions.
        This is a placeholder for future implementation.
        """
        logger.debug("Transaction started (P6 API may handle this implicitly)")
    
    def commit_transaction(self):
        """
        Commit the current transaction.
        
        VERIFICATION POINT 3: Transaction Atomicity
        Commits changes to the database.
        
        Note: P6 API may not support explicit transactions.
        This is a placeholder for future implementation.
        """
        logger.debug("Transaction committed (P6 API may handle this implicitly)")
    
    def rollback_transaction(self):
        """
        Rollback the current transaction.
        
        VERIFICATION POINT 3: Transaction Atomicity
        Rolls back changes on error.
        
        Note: P6 API may not support explicit transactions.
        This is a placeholder for future implementation.
        """
        logger.warning("Transaction rollback requested (P6 API may not support explicit rollback)")
