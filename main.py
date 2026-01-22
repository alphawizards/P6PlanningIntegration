#!/usr/bin/env python3
"""
P6 Planning Integration - Command Line Interface

Comprehensive CLI for Primavera P6 Professional automation and reporting.

Modes:
- Database test (default): Verify database connection
- List projects: Show available projects
- Report generation: Create PDF reports
- Schedule analysis: Run health checks
- File ingestion: Parse XER/XML/MPX files
- AI chat: Interactive natural language interface

Supports two connection modes:
- SQLITE: Direct connection to P6 Professional standalone SQLite database
- JAVA: JPype-based connection via P6 Integration API
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

from src.config import P6_CONNECTION_MODE, P6_DB_PATH, print_config_summary
from src.utils import logger, log_exception

# Conditional imports based on connection mode
if P6_CONNECTION_MODE == 'JAVA':
    import jpype
    from src.core import P6Session
    from src.dao import ProjectDAO, ActivityDAO, RelationshipDAO
else:
    # SQLite mode - no JPype needed
    jpype = None
    from src.dao import SQLiteManager, SQLiteProjectDAO, SQLiteActivityDAO, SQLiteRelationshipDAO

from src.reporting import DataExporter, ContextGenerator, PDFGenerator
from src.ingestion import XERParser, UnifiedXMLParser, MPXParser
from src.analyzers.schedule_analyzer import ScheduleAnalyzer


# =============================================================================
# List Projects Mode
# =============================================================================

def list_projects_mode(verbose: bool = False):
    """
    List all available projects in the database.

    Args:
        verbose: Show additional project details
    """
    print("=" * 70)
    print("P6 Planning Integration - Project List")
    print("=" * 70)
    print()

    try:
        if P6_CONNECTION_MODE == 'SQLITE':
            manager = SQLiteManager()
            manager.connect()
            project_dao = manager.get_project_dao()
        else:
            manager = P6Session()
            manager.connect()
            project_dao = ProjectDAO(manager)

        try:
            projects_df = project_dao.get_active_projects()

            if projects_df.empty:
                print("No projects found in database.")
                return 0

            print(f"Found {len(projects_df)} project(s):\n")

            if verbose:
                # Detailed view
                for i, row in projects_df.iterrows():
                    print(f"  [{row['ObjectId']}] {row['Name']}")
                    print(f"       ID: {row['Id']}")
                    if 'PlanStartDate' in row and row['PlanStartDate']:
                        print(f"       Start: {str(row['PlanStartDate'])[:10]}")
                    if 'PlanEndDate' in row and row['PlanEndDate']:
                        print(f"       End: {str(row['PlanEndDate'])[:10]}")
                    print()
            else:
                # Simple table view
                print(f"{'ObjectId':<12} {'ID':<20} {'Name':<40}")
                print("-" * 70)
                for _, row in projects_df.iterrows():
                    name = str(row['Name'])[:38]
                    print(f"{row['ObjectId']:<12} {row['Id']:<20} {name:<40}")

            print()
            print("Use --project <ObjectId> with other commands to specify a project.")

        finally:
            manager.disconnect()

        return 0

    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        log_exception(logger, e)
        print(f"\nError: {e}")
        return 1


# =============================================================================
# Report Generation Mode
# =============================================================================

def generate_report_mode(
    project_id: int,
    report_type: str = 'summary',
    output: str = None,
    landscape: bool = False,
):
    """
    Generate PDF report for a project.

    Args:
        project_id: Project ObjectId
        report_type: Type of report (summary, critical, health, comprehensive)
        output: Optional output filename
        landscape: Use landscape orientation
    """
    print("=" * 70)
    print("P6 Planning Integration - PDF Report Generator")
    print("=" * 70)
    print()

    valid_types = ['summary', 'critical', 'health', 'comprehensive']
    if report_type not in valid_types:
        print(f"Error: Invalid report type '{report_type}'")
        print(f"Valid types: {', '.join(valid_types)}")
        return 1

    try:
        if P6_CONNECTION_MODE == 'SQLITE':
            manager = SQLiteManager()
            manager.connect()
        else:
            manager = P6Session()
            manager.connect()

        try:
            # Verify project exists
            project_dao = manager.get_project_dao()
            project_df = project_dao.get_project_by_object_id(project_id)

            if project_df.empty:
                print(f"Error: Project with ObjectId {project_id} not found.")
                print("Use --list-projects to see available projects.")
                return 1

            project_name = project_df.iloc[0]['Name']
            print(f"Project: {project_name} (ObjectId: {project_id})")
            print(f"Report Type: {report_type}")
            print()

            # Generate report
            pdf_gen = PDFGenerator(landscape_mode=landscape)
            pdf_gen.set_manager(manager)

            print("Generating report...")

            if report_type == 'summary':
                output_path = pdf_gen.generate_schedule_summary(
                    project_id, output_filename=output
                )
            elif report_type == 'critical':
                output_path = pdf_gen.generate_critical_path_report(
                    project_id, output_filename=output
                )
            elif report_type == 'health':
                output_path = pdf_gen.generate_health_check_report(
                    project_id, output_filename=output
                )
            elif report_type == 'comprehensive':
                output_path = pdf_gen.generate_comprehensive_report(
                    project_id, output_filename=output
                )

            file_size = output_path.stat().st_size / 1024

            print()
            print(f"Report generated successfully!")
            print(f"  File: {output_path}")
            print(f"  Size: {file_size:.1f} KB")

        finally:
            manager.disconnect()

        return 0

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        log_exception(logger, e)
        print(f"\nError: {e}")
        return 1


# =============================================================================
# Schedule Analysis Mode
# =============================================================================

def analyze_schedule_mode(project_id: int, export_json: bool = False):
    """
    Run schedule health check analysis.

    Args:
        project_id: Project ObjectId
        export_json: Export results to JSON file
    """
    print("=" * 70)
    print("P6 Planning Integration - Schedule Analysis")
    print("=" * 70)
    print()

    try:
        if P6_CONNECTION_MODE == 'SQLITE':
            manager = SQLiteManager()
            manager.connect()
        else:
            manager = P6Session()
            manager.connect()

        try:
            # Verify project exists
            project_dao = manager.get_project_dao()
            project_df = project_dao.get_project_by_object_id(project_id)

            if project_df.empty:
                print(f"Error: Project with ObjectId {project_id} not found.")
                return 1

            project_name = project_df.iloc[0]['Name']
            print(f"Project: {project_name}")
            print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()

            # Run analysis
            analyzer = ScheduleAnalyzer(manager)
            results = analyzer.run_health_check(project_id)

            # Display results
            print("=" * 70)
            print("HEALTH CHECK RESULTS")
            print("=" * 70)

            score = results.get('health_score', 0)
            total_activities = results.get('total_activities', 0)
            total_relationships = results.get('total_relationships', 0)

            # Score with rating
            if score >= 90:
                rating = "Excellent"
                indicator = "[OK]"
            elif score >= 75:
                rating = "Good"
                indicator = "[OK]"
            elif score >= 50:
                rating = "Fair"
                indicator = "[!!]"
            else:
                rating = "Needs Improvement"
                indicator = "[XX]"

            print(f"\n{indicator} Overall Score: {score:.0f}/100 ({rating})")
            print(f"    Total Activities: {total_activities}")
            print(f"    Total Relationships: {total_relationships}")

            logic_density = (
                total_relationships / total_activities
                if total_activities > 0 else 0
            )
            density_status = "[OK]" if logic_density >= 1.8 else "[!!]"
            print(f"    {density_status} Logic Density: {logic_density:.2f} (target: >= 1.8)")

            # Individual checks
            checks = results.get('checks', {})

            print("\n" + "-" * 70)
            print("CHECK DETAILS")
            print("-" * 70)

            # Open Ends
            open_ends = checks.get('open_ends', {})
            open_start = open_ends.get('open_start_count', 0)
            open_finish = open_ends.get('open_finish_count', 0)
            status = "[OK]" if (open_start == 0 and open_finish == 0) else "[!!]"
            print(f"\n{status} Open Ends:")
            print(f"    Open Start: {open_start}")
            print(f"    Open Finish: {open_finish}")

            # Constraints
            constraints = checks.get('constraints', {})
            hard_count = constraints.get('hard_constraint_count', 0)
            status = "[OK]" if hard_count == 0 else "[!!]"
            print(f"\n{status} Hard Constraints: {hard_count}")

            # Float
            float_check = checks.get('float', {})
            neg_float = float_check.get('negative_float_count', 0)
            min_float = float_check.get('min_float', 0)
            status = "[OK]" if neg_float == 0 else "[XX]"
            print(f"\n{status} Negative Float:")
            print(f"    Count: {neg_float}")
            print(f"    Min Float: {min_float:.1f} days")

            # Duration/Lag
            dur_lag = checks.get('duration_lag', {})
            high_dur = dur_lag.get('high_duration_count', 0)
            neg_lag = dur_lag.get('negative_lag_count', 0)
            status = "[OK]" if high_dur == 0 else "[!!]"
            print(f"\n{status} High Duration (>20 days): {high_dur}")
            status = "[OK]" if neg_lag == 0 else "[!!]"
            print(f"{status} Negative Lag (leads): {neg_lag}")

            # Progress
            progress = checks.get('progress', {})
            missing_start = progress.get('missing_actual_start_count', 0)
            missing_finish = progress.get('missing_actual_finish_count', 0)
            status = "[OK]" if (missing_start == 0 and missing_finish == 0) else "[!!]"
            print(f"\n{status} Progress Integrity:")
            print(f"    Missing Actual Start: {missing_start}")
            print(f"    Missing Actual Finish: {missing_finish}")

            # Export to JSON if requested
            if export_json:
                import json
                output_path = Path("reports") / f"analysis_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json.dumps(results, indent=2, default=str))
                print(f"\n\nResults exported to: {output_path}")

            print("\n" + "=" * 70)

        finally:
            manager.disconnect()

        return 0

    except Exception as e:
        logger.error(f"Schedule analysis failed: {e}")
        log_exception(logger, e)
        print(f"\nError: {e}")
        return 1


# =============================================================================
# File Ingestion Mode
# =============================================================================

def test_file_ingestion(filepath: str):
    """
    Test file ingestion with automatic format detection.

    Args:
        filepath: Path to schedule file (.xer, .xml, .mpx)
    """
    print("\n" + "=" * 70)
    print("P6 Planning Integration - File Ingestion")
    print("=" * 70)

    try:
        file_path = Path(filepath)

        if not file_path.exists():
            print(f"\nError: File not found: {filepath}")
            return 1

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
            print(f"\nError: Unsupported file format: {extension}")
            print("Supported formats: .xer, .xml, .mpx")
            return 1

        print(f"Parser: {format_name}")
        print("\nParsing file...")

        # Parse file
        result = parser.parse()

        projects_df = result['projects']
        activities_df = result['activities']
        relationships_df = result['relationships']

        print(f"\nParsing complete!")
        print(f"  - Projects: {len(projects_df)}")
        print(f"  - Activities: {len(activities_df)}")
        print(f"  - Relationships: {len(relationships_df)}")

        # Display project data
        if not projects_df.empty:
            print("\n" + "-" * 70)
            print("PROJECTS")
            print("-" * 70)
            print(projects_df.to_string(index=False))

        # Display activity data preview
        if not activities_df.empty:
            print("\n" + "-" * 70)
            print("ACTIVITIES (First 10)")
            print("-" * 70)
            print(activities_df.head(10).to_string(index=False))

        # Display relationship data preview
        if not relationships_df.empty:
            print("\n" + "-" * 70)
            print("RELATIONSHIPS (First 10)")
            print("-" * 70)
            print(relationships_df.head(10).to_string(index=False))

            print("\n" + "-" * 70)
            print("LOGIC NETWORK SUMMARY")
            print("-" * 70)
            print(f"Total relationships: {len(relationships_df)}")
            if 'Type' in relationships_df.columns:
                print("\nRelationship types:")
                print(relationships_df['Type'].value_counts().to_string())

        print("\n" + "=" * 70)
        print("File ingestion completed successfully")
        print("=" * 70)

        return 0

    except Exception as e:
        logger.error(f"File ingestion failed: {e}")
        log_exception(logger, e)
        print(f"\nError: {e}")
        return 1


# =============================================================================
# Database Test Mode
# =============================================================================

def test_database_connection():
    """
    Test database connection and basic operations.
    """
    print("=" * 70)
    print("P6 Planning Integration - Database Connection Test")
    print("=" * 70)
    print()

    try:
        print_config_summary()
        print()

        logger.info(f"Starting database test (mode: {P6_CONNECTION_MODE})")

        if P6_CONNECTION_MODE == 'SQLITE':
            manager = SQLiteManager()
            manager.connect()
            print(f"Connected to: {P6_DB_PATH}")
            print("Mode: READ-ONLY")

            project_dao = manager.get_project_dao()
            activity_dao = manager.get_activity_dao()
            relationship_dao = manager.get_relationship_dao()
        else:
            manager = P6Session()
            manager.connect()
            print("Connected via Integration API")

            project_dao = ProjectDAO(manager)
            activity_dao = ActivityDAO(manager)
            relationship_dao = RelationshipDAO(manager)

        try:
            # Test 1: Projects
            print("\n" + "-" * 70)
            print("TEST 1: Read Projects")
            print("-" * 70)

            projects_df = project_dao.get_all_projects()
            print(f"Found {len(projects_df)} projects")

            if not projects_df.empty:
                print(projects_df.head(5).to_string(index=False))

            # Test 2: Activities
            if not projects_df.empty:
                print("\n" + "-" * 70)
                print("TEST 2: Read Activities")
                print("-" * 70)

                test_project_id = projects_df.iloc[0]['ObjectId']
                activities_df = activity_dao.get_activities_for_project(test_project_id)
                print(f"Found {len(activities_df)} activities for first project")

                # Test 3: Relationships
                print("\n" + "-" * 70)
                print("TEST 3: Read Relationships")
                print("-" * 70)

                relationships_df = relationship_dao.get_relationships(test_project_id)
                print(f"Found {len(relationships_df)} relationships")

            print("\n" + "=" * 70)
            print("Database connection test: PASSED")
            print("=" * 70)

        finally:
            manager.disconnect()

        return 0

    except Exception as e:
        logger.error(f"Database test failed: {e}")
        log_exception(logger, e)
        print(f"\nError: {e}")
        print("\n" + "=" * 70)
        print("Database connection test: FAILED")
        print("=" * 70)
        return 1


# =============================================================================
# Interactive Chat Mode (AI Agent)
# =============================================================================

def interactive_chat_mode(project_id: int = None):
    """
    Interactive chat mode with AI agent.

    Args:
        project_id: Optional project ObjectId to analyze
    """
    # Only available in JAVA mode
    if P6_CONNECTION_MODE != 'JAVA':
        print("Error: AI Chat mode requires JAVA connection mode.")
        print("Set P6_CONNECTION_MODE=JAVA in your .env file.")
        return 1

    from src.ai import P6Agent

    print("=" * 70)
    print("P6 Planning Integration - AI Chat Mode")
    print("=" * 70)
    print()
    print("Type 'help' for available commands, or 'exit' to quit.")
    print()

    try:
        print_config_summary()
        print()

        with P6Session() as session:
            if project_id is None:
                project_dao = ProjectDAO(session)
                projects_df = project_dao.get_all_projects()

                if projects_df.empty:
                    print("No projects found in database.")
                    return 1

                print("Available Projects:")
                for i, row in projects_df.iterrows():
                    print(f"  {i+1}. {row['Name']} (ObjectId: {row['ObjectId']})")

                print()
                selection = input("Select project number (or Enter to skip): ").strip()

                if selection and selection.isdigit():
                    idx = int(selection) - 1
                    if 0 <= idx < len(projects_df):
                        project_id = projects_df.iloc[idx]['ObjectId']
                        print(f"\nSelected: {projects_df.iloc[idx]['Name']}")

            agent = P6Agent(session, project_id)
            print("\nAI Agent ready!")
            print("-" * 70)

            while True:
                try:
                    user_input = input("\nYou: ").strip()

                    if user_input.lower() in ['exit', 'quit', 'bye']:
                        print("\nGoodbye!")
                        break

                    if not user_input:
                        continue

                    response = agent.chat(user_input)
                    print(f"\nAI: {response}")

                except KeyboardInterrupt:
                    print("\n\nInterrupted. Goodbye!")
                    break

        return 0

    except Exception as e:
        logger.error(f"Chat mode failed: {e}")
        log_exception(logger, e)
        print(f"\nError: {e}")
        return 1


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """
    Main entry point for P6 Planning Integration CLI.
    """
    parser = argparse.ArgumentParser(
        description='P6 Planning Integration - Command Line Interface',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all projects
  python main.py --list-projects
  python main.py --list-projects --verbose

  # Generate PDF reports
  python main.py --report summary --project 123
  python main.py --report critical --project 123 --output my_report.pdf
  python main.py --report health --project 123
  python main.py --report comprehensive --project 123 --landscape

  # Run schedule analysis
  python main.py --analyze --project 123
  python main.py --analyze --project 123 --export-json

  # Parse schedule files
  python main.py schedule.xer
  python main.py project.xml

  # Test database connection
  python main.py --test

  # AI chat mode (requires JAVA mode)
  python main.py --chat
  python main.py --chat --project 123

Report Types:
  summary        Executive-level schedule overview
  critical       Critical path analysis with float distribution
  health         Schedule quality validation (DCMA/AACE)
  comprehensive  Multi-section combined report
        """
    )

    # Positional argument for file ingestion
    parser.add_argument(
        'filepath',
        nargs='?',
        help='Path to schedule file (.xer, .xml, .mpx) for ingestion'
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()

    mode_group.add_argument(
        '--list-projects', '-l',
        action='store_true',
        help='List all available projects'
    )

    mode_group.add_argument(
        '--report', '-r',
        choices=['summary', 'critical', 'health', 'comprehensive'],
        metavar='TYPE',
        help='Generate PDF report (summary, critical, health, comprehensive)'
    )

    mode_group.add_argument(
        '--analyze', '-a',
        action='store_true',
        help='Run schedule health check analysis'
    )

    mode_group.add_argument(
        '--test', '-t',
        action='store_true',
        help='Test database connection'
    )

    mode_group.add_argument(
        '--chat', '-c',
        action='store_true',
        help='Start interactive AI chat mode'
    )

    # Common options
    parser.add_argument(
        '--project', '-p',
        type=int,
        metavar='ID',
        help='Project ObjectId for report/analyze/chat commands'
    )

    parser.add_argument(
        '--output', '-o',
        metavar='FILE',
        help='Output filename for report generation'
    )

    parser.add_argument(
        '--landscape',
        action='store_true',
        help='Use landscape orientation for PDF reports'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show verbose output'
    )

    parser.add_argument(
        '--export-json',
        action='store_true',
        help='Export analysis results to JSON file'
    )

    args = parser.parse_args()

    # Determine mode and execute
    if args.list_projects:
        return list_projects_mode(verbose=args.verbose)

    elif args.report:
        if args.project is None:
            parser.error("--report requires --project <ID>")
        return generate_report_mode(
            project_id=args.project,
            report_type=args.report,
            output=args.output,
            landscape=args.landscape,
        )

    elif args.analyze:
        if args.project is None:
            parser.error("--analyze requires --project <ID>")
        return analyze_schedule_mode(
            project_id=args.project,
            export_json=args.export_json,
        )

    elif args.chat:
        return interactive_chat_mode(args.project)

    elif args.filepath:
        return test_file_ingestion(args.filepath)

    elif args.test:
        return test_database_connection()

    else:
        # Default: show help if no arguments
        if len(sys.argv) == 1:
            parser.print_help()
            return 0
        else:
            return test_database_connection()


if __name__ == "__main__":
    sys.exit(main())
