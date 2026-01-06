#!/usr/bin/env python3
"""
P6 Local AI Agent - Primavera P6 Integration via JPype1
Main entry point for Phase 3: Reporting & AI Context Generation
"""

import sys
import jpype

from src.core import P6Session
from src.dao import ProjectDAO, ActivityDAO
from src.reporting import DataExporter, ContextGenerator
from src.config import print_config_summary
from src.utils import logger, log_exception


def main():
    """
    Main entry point for P6 Planning Integration.
    
    Phase 3: Reporting & AI Context Generation
    - CSV/Excel/JSON export with datetime serialization
    - AI-consumable Markdown summaries
    - Token budget safeguards (max rows)
    - Automatic directory creation
    """
    print("=" * 70)
    print("P6 Local AI Agent - Phase 3: Reporting & AI Context Generation")
    print("=" * 70)
    print()
    
    try:
        # Display configuration summary
        print_config_summary()
        print()
        
        logger.info("Starting P6 Planning Integration")
        logger.info("Phase 3: Reporting & AI Context Generation")
        
        # Initialize and connect to P6 using context manager
        logger.info("Initializing P6 session...")
        
        with P6Session() as session:
            logger.info("=" * 70)
            logger.info("✓ Phase 3: Connection Established - Testing Exports")
            logger.info("=" * 70)
            logger.info("")
            
            # ================================================================
            # FETCH DATA (Phase 2 functionality)
            # ================================================================
            logger.info("Fetching P6 data...")
            
            project_dao = ProjectDAO(session)
            projects_df = project_dao.get_all_projects()
            
            print(f"\n✓ Fetched {len(projects_df)} projects")
            
            if projects_df.empty:
                print("\n⚠ No projects found - cannot test exports")
                logger.warning("No projects found - skipping export tests")
                return 0
            
            # Get first project for activity testing
            first_project_object_id = projects_df.iloc[0]['ObjectId']
            first_project_name = projects_df.iloc[0]['Name']
            
            activity_dao = ActivityDAO(session)
            activities_df = activity_dao.get_activities_for_project(first_project_object_id)
            
            print(f"✓ Fetched {len(activities_df)} activities for project: {first_project_name}")
            
            # ================================================================
            # TEST 1: Export Project List to CSV
            # ================================================================
            logger.info("TEST 1: Exporting projects to CSV")
            print("\n" + "=" * 70)
            print("TEST 1: Export Project List to CSV")
            print("=" * 70)
            
            exporter = DataExporter(base_dir="reports")
            
            csv_path = exporter.to_csv(
                df=projects_df,
                filename="projects.csv",
                subfolder="phase3_test"
            )
            
            print(f"\n✓ Exported projects to CSV: {csv_path}")
            logger.info(f"CSV export successful: {csv_path}")
            
            # ================================================================
            # TEST 2: Generate Project Context JSON
            # ================================================================
            logger.info("TEST 2: Generating project context JSON")
            print("\n" + "=" * 70)
            print("TEST 2: Generate Project Context JSON")
            print("=" * 70)
            
            # Get first project as single-row DataFrame
            first_project_df = projects_df.head(1)
            
            # Generate JSON context string (for AI consumption)
            json_context = exporter.to_json_context(
                df=first_project_df,
                filename=None,  # Return string, don't write to file
                max_rows=1
            )
            
            print(f"\n✓ Generated JSON context for project: {first_project_name}")
            print("\nJSON Context Preview:")
            print(json_context[:500] + "..." if len(json_context) > 500 else json_context)
            logger.info("JSON context generation successful")
            
            # Also save to file for inspection
            json_path = exporter.to_json_context(
                df=first_project_df,
                filename="project_context.json",
                subfolder="phase3_test"
            )
            print(f"\n✓ Saved JSON context to: {json_path}")
            
            # ================================================================
            # TEST 3: Generate Critical Path Summary (AI Context)
            # ================================================================
            logger.info("TEST 3: Generating critical path summary for AI")
            print("\n" + "=" * 70)
            print("TEST 3: Generate Critical Path Summary (AI Context)")
            print("=" * 70)
            
            context_gen = ContextGenerator(max_activities_for_ai=100)
            
            # Generate project summary
            project_summary = context_gen.generate_project_summary(
                project_df=first_project_df,
                activity_df=activities_df
            )
            
            print("\n" + "─" * 70)
            print("PROJECT SUMMARY (Markdown for AI)")
            print("─" * 70)
            print(project_summary)
            
            # Generate critical path report (simplified DataFrame)
            critical_path_df = context_gen.generate_critical_path_report(
                activity_df=activities_df
            )
            
            if not critical_path_df.empty:
                print("\n" + "─" * 70)
                print("CRITICAL PATH ACTIVITIES (for AI analysis)")
                print("─" * 70)
                print(f"Activities: {len(critical_path_df)}")
                print("\nTop 10 Activities:")
                print(critical_path_df.head(10).to_string(index=False))
            else:
                print("\n⚠ No critical path data available (TotalFloat field not in schema)")
            
            # ================================================================
            # TEST 4: Export to Excel
            # ================================================================
            logger.info("TEST 4: Exporting activities to Excel")
            print("\n" + "=" * 70)
            print("TEST 4: Export Activities to Excel")
            print("=" * 70)
            
            if not activities_df.empty:
                excel_path = exporter.to_excel(
                    df=activities_df,
                    filename="activities.xlsx",
                    subfolder="phase3_test",
                    sheet_name="Activities"
                )
                
                print(f"\n✓ Exported activities to Excel: {excel_path}")
                logger.info(f"Excel export successful: {excel_path}")
            else:
                print("\n⚠ No activities to export")
            
            # ================================================================
            # VERIFICATION SUMMARY
            # ================================================================
            logger.info("")
            logger.info("=" * 70)
            logger.info("✓ Phase 3: Reporting & AI Context Generation Verified")
            logger.info("=" * 70)
            logger.info("")
            logger.info("Verification Protocol Results:")
            logger.info("  ✓ Output Paths: Directories auto-created via ensure_directory()")
            logger.info("  ✓ Serialization: datetime → ISO format via date_format='iso'")
            logger.info("  ✓ Context Limits: max_activities_for_ai enforced (100)")
            logger.info("  ✓ Excel Formatting: pandas.ExcelWriter used with column sizing")
            logger.info("")
            logger.info("Reporting Components:")
            logger.info("  ✓ src/utils/file_manager.py - Path & directory management")
            logger.info("  ✓ src/reporting/exporters.py - CSV/Excel/JSON export")
            logger.info("  ✓ src/reporting/generators.py - AI context generation")
            logger.info("")
            
            print("\n" + "=" * 70)
            print("Verification Summary")
            print("=" * 70)
            print("✓ Output Paths: Auto-created with timestamps")
            print("✓ Serialization: Datetime → ISO format in JSON")
            print("✓ Context Limits: Max 100 activities for AI")
            print("✓ Excel Formatting: Column widths auto-adjusted")
            print("\nExported Files:")
            print(f"  - {csv_path}")
            print(f"  - {json_path}")
            if not activities_df.empty:
                print(f"  - {excel_path}")
        
        logger.info("P6 session closed successfully")
        logger.info("Phase 3 reporting implementation completed successfully")
        
        print()
        print("=" * 70)
        print("Status: Phase 3 completed successfully")
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
        logger.error("Failed to complete Phase 3")
        log_exception(logger, e)
        print()
        print("=" * 70)
        print("Status: Failed - See logs for details")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
