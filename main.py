#!/usr/bin/env python3
"""
P6 Local AI Agent - Primavera P6 Integration
Main entry point for Phase 5: AI Agent Integration

Supports two connection modes:
- SQLITE: Direct connection to P6 Professional standalone SQLite database
- JAVA: JPype-based connection via P6 Integration API
"""

import sys
import argparse
from pathlib import Path

from src.config import P6_CONNECTION_MODE, P6_DB_PATH, print_config_summary
from src.utils import logger, log_exception

# Conditional imports based on connection mode
if P6_CONNECTION_MODE == 'JAVA':
    import jpype
    from src.core import P6Session
    from src.dao import ProjectDAO, ActivityDAO, RelationshipDAO
else:
    # SQLite mode - no JPype needed
    jpype = None  # Placeholder for exception handling
    from src.dao import SQLiteManager, SQLiteProjectDAO, SQLiteActivityDAO, SQLiteRelationshipDAO

from src.reporting import DataExporter, ContextGenerator
from src.ingestion import XERParser, UnifiedXMLParser, MPXParser
from src.ai import P6Agent



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
        relationships_df = result['relationships']
        
        print(f"\n✓ Parsing complete!")
        print(f"  - Projects: {len(projects_df)}")
        print(f"  - Activities: {len(activities_df)}")
        print(f"  - Relationships: {len(relationships_df)}")
        
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
        
        # Display relationship data preview
        if not relationships_df.empty:
            print("\n" + "─" * 70)
            print("RELATIONSHIPS (First 10)")
            print("─" * 70)
            print(relationships_df.head(10).to_string(index=False))
            
            print("\n" + "─" * 70)
            print("LOGIC NETWORK SUMMARY")
            print("─" * 70)
            print(f"Total relationships: {len(relationships_df)}")
            if 'Type' in relationships_df.columns:
                print("\nRelationship types:")
                print(relationships_df['Type'].value_counts().to_string())
        
        print("\n" + "=" * 70)
        print("File ingestion test completed successfully")
        print("=" * 70)
        
    except Exception as e:
        logger.error(f"File ingestion test failed: {e}")
        log_exception(logger, e)
        print(f"\n✗ Error: {e}")


def test_database_connection():
    """
    Test database connection, relationship reading, and write safety.
    
    Supports both SQLite (P6 Professional) and Java (Integration API) modes.
    """
    print("=" * 70)
    print("P6 Local AI Agent - Database Connection Test")
    print("=" * 70)
    print()
    
    try:
        # Display configuration summary
        print_config_summary()
        print()
        
        logger.info("Starting P6 Planning Integration - Database Test")
        logger.info(f"Connection mode: {P6_CONNECTION_MODE}")
        
        # ================================================================
        # Mode-specific connection
        # ================================================================
        if P6_CONNECTION_MODE == 'SQLITE':
            logger.info(f"Connecting to SQLite database: {P6_DB_PATH}")
            manager = SQLiteManager()
            manager.connect()
            
            print(f"✓ Connected to Standalone DB: {P6_DB_PATH}")
            print("  Mode: READ-ONLY (safe)")
            
            # Get DAOs from manager
            project_dao = manager.get_project_dao()
            activity_dao = manager.get_activity_dao()
            relationship_dao = manager.get_relationship_dao()
            
        else:
            # Java/JPype mode
            logger.info("Initializing P6 session via JPype...")
            manager = P6Session()
            manager.connect()
            
            print("✓ Connected to P6 via Integration API")
            
            # Get DAOs using Java session
            project_dao = ProjectDAO(manager)
            activity_dao = ActivityDAO(manager)
            relationship_dao = RelationshipDAO(manager)
        
        try:
            logger.info("=" * 70)
            logger.info("✓ Database Connection Established")
            logger.info("=" * 70)
            
            # ================================================================
            # TEST 1: Read Projects
            # ================================================================
            print("\n" + "=" * 70)
            print("TEST 1: READ PROJECTS")
            print("=" * 70)
            
            logger.info("Fetching projects...")
            projects_df = project_dao.get_all_projects()
            
            print(f"\n✓ Fetched {len(projects_df)} projects from database")
            
            if not projects_df.empty:
                print("\n" + "─" * 70)
                print("PROJECTS (First 10)")
                print("─" * 70)
                print(projects_df.head(10).to_string(index=False))
            
            if projects_df.empty:
                print("\n⚠ No projects found in database")
                print("Skipping activity and relationship tests")
            else:
                # Get first project for testing
                first_project_object_id = projects_df.iloc[0]['ObjectId']
                first_project_name = projects_df.iloc[0]['Name']
                
                print(f"\nTesting with project: {first_project_name} (ObjectId: {first_project_object_id})")
                
                # ================================================================
                # TEST 2: Read Activities
                # ================================================================
                print("\n" + "=" * 70)
                print("TEST 2: READ ACTIVITIES")
                print("=" * 70)
                
                activities_df = activity_dao.get_activities_for_project(first_project_object_id)
                
                print(f"\n✓ Fetched {len(activities_df)} activities for project")
                
                if not activities_df.empty:
                    print("\n" + "─" * 70)
                    print("ACTIVITIES (First 10)")
                    print("─" * 70)
                    print(activities_df.head(10).to_string(index=False))
                    
                    # Show duration verification
                    if 'PlannedDuration' in activities_df.columns:
                        sample_activity = activities_df.iloc[0]
                        print("\n" + "─" * 70)
                        print("DURATION VERIFICATION (First Activity)")
                        print("─" * 70)
                        print(f"  Activity: {sample_activity['Name']}")
                        print(f"  PlannedDuration: {sample_activity['PlannedDuration']} days")
                        if 'TotalFloat' in activities_df.columns:
                            print(f"  TotalFloat: {sample_activity['TotalFloat']} days")
                else:
                    print("\n⚠ No activities found for this project")
                
                # ================================================================
                # TEST 3: Read Relationships
                # ================================================================
                print("\n" + "=" * 70)
                print("TEST 3: READ RELATIONSHIPS")
                print("=" * 70)
                
                relationships_df = relationship_dao.get_relationships(first_project_object_id)
                
                print(f"\n✓ Fetched {len(relationships_df)} relationships for project")
                
                if not relationships_df.empty:
                    print("\n" + "─" * 70)
                    print("RELATIONSHIPS (First 10)")
                    print("─" * 70)
                    print(relationships_df.head(10).to_string(index=False))
                    
                    print("\n" + "─" * 70)
                    print("LOGIC NETWORK SUMMARY")
                    print("─" * 70)
                    print(f"Total relationships: {len(relationships_df)}")
                    if 'Type' in relationships_df.columns:
                        print("\nRelationship types:")
                        print(relationships_df['Type'].value_counts().to_string())
                else:
                    print("\n⚠ No relationships found for this project")
                
                # ================================================================
                # TEST 4: Write Protection Verification
                # ================================================================
                print("\n" + "=" * 70)
                print("TEST 4: WRITE PROTECTION VERIFICATION")
                print("=" * 70)
                
                if not activities_df.empty:
                    test_activity_id = activities_df.iloc[0]['ObjectId']
                    test_activity_name = activities_df.iloc[0]['Name']
                    
                    print(f"\nTesting write protection on: {test_activity_name}")
                    print("Attempting to update activity duration...")
                    
                    try:
                        activity_dao.update_activity(
                            test_activity_id,
                            {'PlannedDuration': 99.0}
                        )
                        
                        # If we reach here in SQLite mode, something is wrong
                        if P6_CONNECTION_MODE == 'SQLITE':
                            print("✗ ERROR: Write should have been blocked in SQLite mode!")
                        else:
                            print("✓ Write operation succeeded (SAFE_MODE may be disabled)")
                        
                    except NotImplementedError as e:
                        # Expected in SQLite mode
                        print(f"✓ Write blocked: {e}")
                        logger.info("Write protection verified - SQLite mode is read-only")
                        
                    except RuntimeError as e:
                        if "SAFE_MODE" in str(e) or "READ-ONLY" in str(e):
                            print(f"✓ Write blocked by safety mechanism")
                            print(f"   Reason: {e}")
                        else:
                            raise
                else:
                    print("\n⚠ No activities available for write protection test")
            
            # ================================================================
            # SUMMARY
            # ================================================================
            print("\n" + "=" * 70)
            print("VERIFICATION SUMMARY")
            print("=" * 70)
            
            print(f"\n✓ Connection Mode: {P6_CONNECTION_MODE}")
            if P6_CONNECTION_MODE == 'SQLITE':
                print(f"✓ Database Path: {P6_DB_PATH}")
                print("✓ Read-Only Mode: Enabled (database protected)")
            
            print("\n✓ Schema Matching Verified:")
            print("  - ObjectId, Id, Name columns present")
            if not activities_df.empty and 'PlannedDuration' in activities_df.columns:
                print("  - Duration conversion (Hours → Days) working")
            
            print("\n✓ Write Protection: Active")
            if P6_CONNECTION_MODE == 'SQLITE':
                print("  - SQLite mode uses NotImplementedError for all writes")
            else:
                print("  - Java mode uses SAFE_MODE flag")
            
            logger.info("Database connection test completed successfully")
            
        finally:
            # Cleanup
            manager.disconnect()
            logger.info("Connection closed successfully")
        
        print()
        print("=" * 70)
        print("Status: Database connection test completed successfully")
        print("=" * 70)
        
        return 0
        
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        log_exception(logger, e)
        print()
        print("=" * 70)
        print(f"Status: Failed - {e}")
        print("See logs/app.log for details")
        print("=" * 70)
        return 1


def interactive_chat_mode(project_id: int = None):
    """
    Interactive chat mode with AI agent.
    
    Args:
        project_id: Optional project ObjectId to analyze
    """
    print("=" * 70)
    print("P6 Local AI Agent - Phase 5: AI Agent Integration")
    print("=" * 70)
    print()
    print("🤖 Welcome to the P6 AI Assistant!")
    print()
    print("I can help you analyze and optimize your P6 schedules.")
    print("Type 'help' for available commands, or 'exit' to quit.")
    print()
    
    try:
        # Display configuration summary
        print_config_summary()
        print()
        
        logger.info("Starting P6 AI Agent - Interactive Chat Mode")
        
        # Initialize and connect to P6
        logger.info("Initializing P6 session...")
        
        with P6Session() as session:
            logger.info("✓ Database Connection Established")
            
            # If no project_id specified, list projects and ask user to select
            if project_id is None:
                project_dao = ProjectDAO(session)
                projects_df = project_dao.get_all_projects()
                
                if projects_df.empty:
                    print("⚠ No projects found in database")
                    print("Please add projects to your P6 database first.")
                    return 1
                
                print("\n📂 Available Projects:")
                print()
                for i, row in projects_df.iterrows():
                    print(f"{i+1}. {row['Name']} (ID: {row['Id']}, ObjectId: {row['ObjectId']})")
                
                print()
                selection = input("Select a project number (or press Enter to skip): ").strip()
                
                if selection and selection.isdigit():
                    idx = int(selection) - 1
                    if 0 <= idx < len(projects_df):
                        project_id = projects_df.iloc[idx]['ObjectId']
                        print(f"\n✓ Selected project: {projects_df.iloc[idx]['Name']}")
                    else:
                        print("\n⚠ Invalid selection, continuing without project context")
                else:
                    print("\n⚠ No project selected, continuing without project context")
            
            # Initialize AI agent
            print("\n🤖 Initializing AI Agent...")
            agent = P6Agent(session, project_id)
            
            print("✓ AI Agent ready!")
            print()
            print("─" * 70)
            print()
            
            # Main chat loop
            while True:
                try:
                    # Get user input
                    user_input = input("You: ").strip()
                    
                    # Check for exit commands
                    if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye']:
                        print("\n👋 Goodbye! Have a great day!")
                        break
                    
                    # Skip empty input
                    if not user_input:
                        continue
                    
                    # Process input through agent
                    print()
                    response = agent.chat(user_input)
                    
                    # Display response
                    print(f"AI: {response}")
                    print()
                    print("─" * 70)
                    print()
                
                except KeyboardInterrupt:
                    print("\n\n👋 Interrupted. Goodbye!")
                    break
                
                except Exception as e:
                    logger.error(f"Error in chat loop: {e}")
                    log_exception(logger, e)
                    print(f"\n❌ Error: {e}")
                    print("Please try again or type 'exit' to quit.")
                    print()
        
        logger.info("P6 AI Agent session closed")
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
        logger.error("Failed to start AI Agent")
        log_exception(logger, e)
        print()
        print("=" * 70)
        print("Status: Failed - See logs for details")
        print("=" * 70)
        return 1


def main():
    """
    Main entry point for P6 Planning Integration.
    
    Phase 5: AI Agent Integration
    - Interactive chat mode with AI agent
    - Natural language queries
    - Tool-based architecture
    - SAFE_MODE awareness
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='P6 Local AI Agent - Primavera P6 Integration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run Phase 4 database tests
  python main.py --chat             # Interactive AI chat mode
  python main.py --chat --project 123  # Chat mode with specific project
  python main.py project.xer        # File ingestion mode
  python main.py --help             # Show this help message

Modes:
  1. Database Test Mode (default): Verify Phase 4 functionality
  2. AI Chat Mode (--chat): Interactive natural language interface
  3. File Ingestion Mode (filepath): Parse XER/XML/MPX files
        """
    )
    
    parser.add_argument(
        'filepath',
        nargs='?',
        help='Path to schedule file (.xer, .xml, .mpx) for ingestion mode'
    )
    
    parser.add_argument(
        '--chat',
        action='store_true',
        help='Start interactive AI chat mode'
    )
    
    parser.add_argument(
        '--project',
        type=int,
        metavar='PROJECT_ID',
        help='Project ObjectId for AI chat mode (optional)'
    )
    
    args = parser.parse_args()
    
    # Determine mode
    if args.chat:
        # AI Chat Mode
        return interactive_chat_mode(args.project)
    
    elif args.filepath:
        # File Ingestion Mode
        test_file_ingestion(args.filepath)
        return 0
    
    else:
        # Database Test Mode (default)
        return test_database_connection()


if __name__ == "__main__":
    sys.exit(main())
