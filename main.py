#!/usr/bin/env python3
"""
P6 Local AI Agent - Primavera P6 Integration via JPype1
Main entry point for Phase 2.5: Multi-Format File Ingestion
"""

import sys
import jpype
from pathlib import Path

from src.core import P6Session
from src.dao import ProjectDAO, ActivityDAO
from src.reporting import DataExporter, ContextGenerator
from src.ingestion import XERParser, UnifiedXMLParser, MPXParser
from src.config import print_config_summary
from src.utils import logger, log_exception


def test_file_ingestion(filepath: str):
    """
    Test file ingestion with automatic format detection.
    
    Args:
        filepath: Path to schedule file (.xer, .xml, .mpx)
    """
    print("\n" + "=" * 70)
    print("FILE INGESTION TEST")
    print("=" * 70)
    
    try:
        file_path = Path(filepath)
        
        if not file_path.exists():
            print(f"\n✗ File not found: {filepath}")
            return
        
        # Detect format by extension
        extension = file_path.suffix.lower()
        
        print(f"\nFile: {file_path.name}")
        print(f"Format: {extension}")
        print(f"Size: {file_path.stat().st_size:,} bytes")
        
        # Select parser based on extension
        if extension == '.xer':
            parser = XERParser(filepath)
            format_name = "Primavera P6 XER"
        elif extension == '.xml':
            parser = UnifiedXMLParser(filepath)
            format_name = "XML (P6 or MS Project)"
        elif extension == '.mpx':
            parser = MPXParser(filepath)
            format_name = "Microsoft Project MPX"
        else:
            print(f"\n✗ Unsupported file format: {extension}")
            print("Supported formats: .xer, .xml, .mpx")
            return
        
        print(f"Parser: {format_name}")
        print("\nParsing file...")
        
        # Parse file
        result = parser.parse()
        
        projects_df = result['projects']
        activities_df = result['activities']
        
        print(f"\n✓ Parsing complete!")
        print(f"  - Projects: {len(projects_df)}")
        print(f"  - Activities: {len(activities_df)}")
        
        # Display project data
        if not projects_df.empty:
            print("\n" + "─" * 70)
            print("PROJECTS")
            print("─" * 70)
            print(projects_df.to_string(index=False))
        
        # Display activity data preview
        if not activities_df.empty:
            print("\n" + "─" * 70)
            print("ACTIVITIES (First 10)")
            print("─" * 70)
            print(activities_df.head(10).to_string(index=False))
            
            print("\n" + "─" * 70)
            print("SCHEMA VERIFICATION")
            print("─" * 70)
            print("Columns:", list(activities_df.columns))
            print("\nData Types:")
            print(activities_df.dtypes.to_string())
            
            # Verify schema alignment
            from src.core.definitions import ACTIVITY_FIELDS
            print("\n" + "─" * 70)
            print("SCHEMA ALIGNMENT CHECK")
            print("─" * 70)
            print(f"Expected fields: {ACTIVITY_FIELDS}")
            print(f"Actual fields: {list(activities_df.columns)}")
            
            if list(activities_df.columns) == ACTIVITY_FIELDS:
                print("\n✓ Schema alignment: PASSED")
            else:
                print("\n⚠ Schema alignment: MISMATCH")
        
        print("\n" + "=" * 70)
        print("File ingestion test completed successfully")
        print("=" * 70)
        
    except Exception as e:
        logger.error(f"File ingestion test failed: {e}")
        log_exception(logger, e)
        print(f"\n✗ Error: {e}")


def test_database_connection():
    """
    Test database connection and data access (Phase 2 & 3 functionality).
    """
    print("=" * 70)
    print("P6 Local AI Agent - Database Connection Test")
    print("=" * 70)
    print()
    
    try:
        # Display configuration summary
        print_config_summary()
        print()
        
        logger.info("Starting P6 Planning Integration")
        logger.info("Testing database connection and reporting")
        
        # Initialize and connect to P6 using context manager
        logger.info("Initializing P6 session...")
        
        with P6Session() as session:
            logger.info("=" * 70)
            logger.info("✓ Database Connection Established")
            logger.info("=" * 70)
            logger.info("")
            
            # Fetch data
            logger.info("Fetching P6 data...")
            
            project_dao = ProjectDAO(session)
            projects_df = project_dao.get_all_projects()
            
            print(f"\n✓ Fetched {len(projects_df)} projects from database")
            
            if projects_df.empty:
                print("\n⚠ No projects found in database")
                return 0
            
            # Get first project for activity testing
            first_project_object_id = projects_df.iloc[0]['ObjectId']
            first_project_name = projects_df.iloc[0]['Name']
            
            activity_dao = ActivityDAO(session)
            activities_df = activity_dao.get_activities_for_project(first_project_object_id)
            
            print(f"✓ Fetched {len(activities_df)} activities for project: {first_project_name}")
            
            # Export test
            logger.info("Testing export functionality...")
            print("\n" + "=" * 70)
            print("EXPORT TEST")
            print("=" * 70)
            
            exporter = DataExporter(base_dir="reports")
            
            csv_path = exporter.to_csv(
                df=projects_df,
                filename="projects_db.csv",
                subfolder="phase2.5_test"
            )
            
            print(f"\n✓ Exported projects to CSV: {csv_path}")
            
            # Context generation test
            logger.info("Testing AI context generation...")
            print("\n" + "=" * 70)
            print("AI CONTEXT GENERATION TEST")
            print("=" * 70)
            
            context_gen = ContextGenerator(max_activities_for_ai=100)
            
            first_project_df = projects_df.head(1)
            project_summary = context_gen.generate_project_summary(
                project_df=first_project_df,
                activity_df=activities_df
            )
            
            print("\n" + "─" * 70)
            print("PROJECT SUMMARY (Markdown for AI)")
            print("─" * 70)
            print(project_summary)
        
        logger.info("P6 session closed successfully")
        logger.info("Database connection test completed successfully")
        
        print()
        print("=" * 70)
        print("Status: Database test completed successfully")
        print("=" * 70)
        
        return 0
        
    except jpype.JException as e:
        logger.error("Java exception occurred")
        log_exception(logger, e)
        print()
        print("=" * 70)
        print("Status: Failed - Java exception occurred")
        print("See logs/app.log for details")
        print("=" * 70)
        return 1
        
    except Exception as e:
        logger.error("Failed to complete database test")
        log_exception(logger, e)
        print()
        print("=" * 70)
        print("Status: Failed - See logs for details")
        print("=" * 70)
        return 1


def main():
    """
    Main entry point for P6 Planning Integration.
    
    Phase 2.5: Multi-Format File Ingestion
    - XER parser with %T and %F table structure
    - XML parser (P6 and MS Project)
    - MPX parser for legacy files
    - Schema alignment to definitions.py
    - Encoding handling (utf-8, cp1252, latin-1)
    """
    print("=" * 70)
    print("P6 Local AI Agent - Phase 2.5: Multi-Format File Ingestion")
    print("=" * 70)
    print()
    
    # Check for command-line arguments
    if len(sys.argv) > 1:
        # File ingestion mode
        filepath = sys.argv[1]
        test_file_ingestion(filepath)
    else:
        # Database connection mode (default)
        print("Usage Options:")
        print("  1. Database mode (default): python main.py")
        print("  2. File ingestion mode: python main.py <filepath>")
        print()
        print("Running in database mode...")
        print()
        
        return test_database_connection()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
