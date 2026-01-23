#!/usr/bin/env python3
"""Full DAO integration test for SQLite P6 database."""

import sys
sys.path.insert(0, r"C:\Users\ckr_4\01 Web Projects\P6PlanningIntegration")

from src.dao.sqlite import SQLiteManager

def main():
    print("=" * 60)
    print("SQLite DAO Integration Test")
    print("=" * 60)
    
    # Test using context manager
    with SQLiteManager() as manager:
        print(f"\n✅ Connected: {manager.is_connected()}")
        print(f"   Database: {manager.db_path}")
        
        # Test Project DAO
        print("\n" + "-" * 40)
        print("PROJECT DAO")
        print("-" * 40)
        
        project_dao = manager.get_project_dao()
        
        # Get all projects
        all_projects = project_dao.get_all_projects()
        print(f"Total projects: {len(all_projects)}")
        print(f"Columns: {list(all_projects.columns)}")
        
        if not all_projects.empty:
            print("\nSample projects (first 5):")
            print(all_projects[['ObjectId', 'Id', 'Name', 'ProjectFlag']].head().to_string(index=False))
        
        # Get active projects
        active_projects = project_dao.get_active_projects()
        print(f"\nActive projects: {len(active_projects)}")
        
        # Test Activity DAO
        print("\n" + "-" * 40)
        print("ACTIVITY DAO")
        print("-" * 40)
        
        activity_dao = manager.get_activity_dao()
        
        # Get sample project to test activities
        if not all_projects.empty:
            sample_project_id = int(all_projects.iloc[0]['ObjectId'])
            print(f"Testing with project ObjectId: {sample_project_id}")
            
            activities = activity_dao.get_activities_for_project(sample_project_id)
            print(f"Activities in project: {len(activities)}")
            
            if not activities.empty:
                print(f"Activity columns: {list(activities.columns)}")
                print("\nSample activities (first 3):")
                display_cols = [c for c in ['ObjectId', 'Id', 'Name', 'Status'] if c in activities.columns]
                print(activities[display_cols].head(3).to_string(index=False))
        
        # Test Relationship DAO
        print("\n" + "-" * 40)
        print("RELATIONSHIP DAO")
        print("-" * 40)
        
        relationship_dao = manager.get_relationship_dao()
        
        if not all_projects.empty:
            sample_project_id = int(all_projects.iloc[0]['ObjectId'])
            print(f"Testing with project ObjectId: {sample_project_id}")
            
            relationships = relationship_dao.get_relationships(sample_project_id)
            print(f"Relationships in project: {len(relationships)}")
            
            if not relationships.empty:
                print(f"Relationship columns: {list(relationships.columns)}")
                print("\nSample relationships (first 3):")
                print(relationships.head(3).to_string(index=False))
    
    print("\n" + "=" * 60)
    print("✅ All DAO tests completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()
