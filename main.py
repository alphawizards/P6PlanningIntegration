#!/usr/bin/env python3
"""
P6 Local AI Agent - Primavera P6 Integration via JPype1
Main module for connecting to local Primavera P6 using JPype1.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import jpype
import jpype.imports


def connect_to_p6():
    """
    Connect to Primavera P6 using JPype1.
    
    This function:
    1. Starts the JVM
    2. Dynamically builds the classpath from all JAR files in P6_LIB_DIR
    3. Imports the P6 Session class
    4. Attempts to login to P6
    5. Shuts down the JVM
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    # Load environment variables
    load_dotenv()
    
    # Get configuration from environment
    p6_lib_dir = os.getenv('P6_LIB_DIR', '').strip()
    db_user = os.getenv('DB_USER', '').strip()
    db_pass = os.getenv('DB_PASS', '')
    p6_user = os.getenv('P6_USER', '').strip()
    p6_pass = os.getenv('P6_PASS', '')
    
    # Validate required environment variables
    if not all([p6_lib_dir, db_user, db_pass, p6_user, p6_pass]):
        print("Error: Missing required environment variables.")
        print("Please ensure P6_LIB_DIR, DB_USER, DB_PASS, P6_USER, and P6_PASS are set.")
        return False
    
    # Validate credentials are not empty after stripping whitespace
    if not db_user or not p6_user:
        print("Error: Username fields cannot be empty or whitespace only.")
        return False
    
    # Validate P6 library directory exists
    lib_path = Path(p6_lib_dir)
    if not lib_path.exists() or not lib_path.is_dir():
        print(f"Error: P6 library directory not found: {p6_lib_dir}")
        return False
    
    session = None
    try:
        # Dynamically build classpath from all JAR files in P6_LIB_DIR
        jar_files = list(lib_path.glob('*.jar'))
        
        if not jar_files:
            print(f"Error: No JAR files found in {p6_lib_dir}")
            return False
        
        print(f"Found {len(jar_files)} JAR files in {p6_lib_dir}")
        
        # Build classpath string
        classpath = os.pathsep.join(str(jar.absolute()) for jar in jar_files)
        
        # Start JVM with the dynamically built classpath
        print("Starting JVM...")
        jpype.startJVM(classpath=classpath)
        print("JVM started successfully")
        
        # Import Primavera P6 Session class
        # NOTE: This import must occur after JVM startup (JPype1 requirement)
        print("Importing Primavera P6 Session class...")
        from com.primavera.integration.client import Session
        
        # Attempt to login to P6
        print(f"Attempting to login to P6 as user: {p6_user}")
        session = Session.login(
            db_user,
            db_pass,
            p6_user,
            p6_pass
        )
        
        print("✓ Successfully connected to Primavera P6!")
        print(f"✓ Session established for user: {p6_user}")
        
        return True
        
    except jpype.JException as e:
        print(f"Error: Java exception occurred during P6 connection:")
        # Sanitize exception message to avoid exposing sensitive details
        error_msg = str(e)
        # Remove potential credential information from error messages
        if db_pass and db_pass in error_msg:
            error_msg = error_msg.replace(db_pass, "***")
        if p6_pass and p6_pass in error_msg:
            error_msg = error_msg.replace(p6_pass, "***")
        print(f"  {type(e).__name__}: {error_msg}")
        return False
        
    except Exception as e:
        print(f"Error: Failed to connect to P6:")
        # Sanitize exception message to avoid exposing sensitive details
        error_msg = str(e)
        # Remove potential credential information from error messages
        if db_pass and db_pass in error_msg:
            error_msg = error_msg.replace(db_pass, "***")
        if p6_pass and p6_pass in error_msg:
            error_msg = error_msg.replace(p6_pass, "***")
        print(f"  {type(e).__name__}: {error_msg}")
        return False
        
    finally:
        # Close the session if it was created
        if session is not None:
            try:
                session.logout()
                print("✓ Session logged out successfully")
            except Exception as e:
                print(f"Warning: Error during session logout: {e}")
        
        # Shutdown JVM
        if jpype.isJVMStarted():
            print("Shutting down JVM...")
            jpype.shutdownJVM()
            print("JVM shutdown complete")


def main():
    """Main entry point for the P6 Local AI Agent."""
    print("=" * 60)
    print("P6 Local AI Agent - Primavera P6 Integration")
    print("=" * 60)
    print()
    
    success = connect_to_p6()
    
    print()
    print("=" * 60)
    if success:
        print("Status: Connection test completed successfully")
        sys.exit(0)
    else:
        print("Status: Connection test failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
