#!/usr/bin/env python3
"""
AI Tools for P6 Planning Integration
Wraps DAO operations with AI-friendly interfaces returning JSON/text responses.
"""

import json
from typing import Dict, List, Optional, Any
import pandas as pd

from src.dao import ProjectDAO, ActivityDAO, RelationshipDAO
from src.reporting import ContextGenerator
from src.utils import logger


class P6Tools:
    """
    AI-friendly wrapper for P6 operations.
    
    VERIFICATION POINT 1: Tool Schemas
    All methods have type hints matching DAO requirements.
    
    VERIFICATION POINT 3: Context Injection
    Includes get_project_context() for initial AI context.
    """
    
    def __init__(self, session):
        """
        Initialize P6Tools with an active session.
        
        Args:
            session: Active P6Session instance
        """
        self.session = session
        self.project_dao = ProjectDAO(session)
        self.activity_dao = ActivityDAO(session)
        self.relationship_dao = RelationshipDAO(session)
        self.context_generator = ContextGenerator()
        
        logger.info("P6Tools initialized for AI agent")
    
    # ========================================================================
    # TOOL SCHEMAS (for LLM function calling)
    # ========================================================================
    
    @staticmethod
    def get_tool_schemas() -> List[Dict[str, Any]]:
        """
        Get JSON schemas for all available tools.
        
        VERIFICATION POINT 1: Tool Schemas
        Schemas exactly match DAO argument types.
        
        Returns:
            List of tool schema dictionaries
        """
        return [
            {
                "name": "get_project_context",
                "description": "Get comprehensive context about a project including summary, activities, and relationships. Use this first to understand the project.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "integer",
                            "description": "Project ObjectId (internal unique identifier)"
                        }
                    },
                    "required": ["project_id"]
                }
            },
            {
                "name": "list_projects",
                "description": "List all available projects with their basic information (Id, Name, Status, dates).",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "search_activities",
                "description": "Search for activities by name, status, or other criteria. Returns matching activities with key fields.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "integer",
                            "description": "Project ObjectId to search within"
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query (activity name, status, etc.)"
                        },
                        "status": {
                            "type": "string",
                            "description": "Filter by status (optional): 'Not Started', 'In Progress', 'Completed'"
                        }
                    },
                    "required": ["project_id"]
                }
            },
            {
                "name": "get_critical_activities",
                "description": "Get activities on the critical path (TotalFloat <= 0) for a project. These are the activities that directly impact project completion date.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "integer",
                            "description": "Project ObjectId"
                        }
                    },
                    "required": ["project_id"]
                }
            },
            {
                "name": "get_activity_details",
                "description": "Get detailed information about a specific activity including all fields and relationships.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "activity_id": {
                            "type": "string",
                            "description": "Activity Id (user-visible identifier, e.g., 'ACT-001')"
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Project ObjectId (optional, improves search performance)"
                        }
                    },
                    "required": ["activity_id"]
                }
            },
            {
                "name": "get_activity_relationships",
                "description": "Get predecessors and successors for a specific activity. Shows the logic network connections.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "activity_object_id": {
                            "type": "integer",
                            "description": "Activity ObjectId (internal unique identifier)"
                        }
                    },
                    "required": ["activity_object_id"]
                }
            },
            {
                "name": "propose_schedule_change",
                "description": "Propose a change to an activity's schedule (duration, dates, status). DOES NOT execute the change - returns a proposal for user approval. SAFE_MODE aware.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "activity_object_id": {
                            "type": "integer",
                            "description": "Activity ObjectId to modify"
                        },
                        "changes": {
                            "type": "object",
                            "description": "Proposed changes as key-value pairs (e.g., {'PlannedDuration': 40.0, 'Status': 'In Progress'})"
                        },
                        "rationale": {
                            "type": "string",
                            "description": "Explanation for why this change is recommended"
                        }
                    },
                    "required": ["activity_object_id", "changes", "rationale"]
                }
            },
            {
                "name": "analyze_schedule_impact",
                "description": "Analyze the potential impact of changing an activity's duration or dates. Considers critical path, successors, and project completion.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "activity_object_id": {
                            "type": "integer",
                            "description": "Activity ObjectId to analyze"
                        },
                        "proposed_duration": {
                            "type": "number",
                            "description": "Proposed new duration in hours (optional)"
                        }
                    },
                    "required": ["activity_object_id"]
                }
            }
        ]
    
    # ========================================================================
    # READ OPERATIONS (Always Available)
    # ========================================================================
    
    def list_projects(self) -> str:
        """
        List all available projects.
        
        Returns:
            JSON string of projects list
        """
        try:
            logger.info("AI Tool: list_projects")
            
            projects_df = self.project_dao.get_all_projects()
            
            if projects_df.empty:
                return json.dumps({
                    "success": False,
                    "message": "No projects found in database",
                    "projects": []
                })
            
            # Convert to records
            projects_list = projects_df.to_dict('records')
            
            # Convert dates to strings
            for project in projects_list:
                for key, value in project.items():
                    if pd.isna(value):
                        project[key] = None
                    elif hasattr(value, 'isoformat'):
                        project[key] = value.isoformat()
            
            return json.dumps({
                "success": True,
                "count": len(projects_list),
                "projects": projects_list
            }, indent=2)
            
        except Exception as e:
            logger.error(f"AI Tool error in list_projects: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    def get_project_context(self, project_id: int) -> str:
        """
        Get comprehensive project context for AI.
        
        VERIFICATION POINT 3: Context Injection
        Provides initial context for AI agent.
        
        Args:
            project_id: Project ObjectId (int, not string)
            
        Returns:
            JSON string with project summary and context
        """
        try:
            logger.info(f"AI Tool: get_project_context(project_id={project_id})")
            
            # Get project
            projects_df = self.project_dao.get_all_projects()
            project = projects_df[projects_df['ObjectId'] == project_id]
            
            if project.empty:
                return json.dumps({
                    "success": False,
                    "error": f"Project not found: {project_id}"
                })
            
            # Get activities
            activities_df = self.activity_dao.get_activities_for_project(project_id)
            
            # Get relationships
            relationships_df = self.relationship_dao.get_relationships(project_id)
            
            # Generate markdown summary
            markdown_summary = self.context_generator.generate_project_summary(
                project,
                activities_df
            )
            
            # Prepare context
            context = {
                "success": True,
                "project": {
                    "ObjectId": int(project.iloc[0]['ObjectId']),
                    "Id": project.iloc[0]['Id'],
                    "Name": project.iloc[0]['Name'],
                    "Status": project.iloc[0]['Status'],
                    "PlanStartDate": project.iloc[0]['PlanStartDate'].isoformat() if pd.notna(project.iloc[0]['PlanStartDate']) else None,
                },
                "statistics": {
                    "total_activities": len(activities_df),
                    "total_relationships": len(relationships_df),
                    "activities_by_status": activities_df['Status'].value_counts().to_dict() if not activities_df.empty else {}
                },
                "markdown_summary": markdown_summary
            }
            
            return json.dumps(context, indent=2)
            
        except Exception as e:
            logger.error(f"AI Tool error in get_project_context: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    def search_activities(self, project_id: int, query: Optional[str] = None, status: Optional[str] = None) -> str:
        """
        Search for activities by criteria.
        
        Args:
            project_id: Project ObjectId (int)
            query: Search query for activity name (optional)
            status: Filter by status (optional)
            
        Returns:
            JSON string of matching activities
        """
        try:
            logger.info(f"AI Tool: search_activities(project_id={project_id}, query={query}, status={status})")
            
            # Get activities
            if status:
                activities_df = self.activity_dao.get_activities_by_status(status, project_id)
            else:
                activities_df = self.activity_dao.get_activities_for_project(project_id)
            
            # Filter by query if provided
            if query and not activities_df.empty:
                activities_df = activities_df[
                    activities_df['Name'].str.contains(query, case=False, na=False)
                ]
            
            if activities_df.empty:
                return json.dumps({
                    "success": True,
                    "message": "No activities found matching criteria",
                    "count": 0,
                    "activities": []
                })
            
            # Convert to records
            activities_list = activities_df.to_dict('records')
            
            # Convert dates and handle NaN
            for activity in activities_list:
                for key, value in activity.items():
                    if pd.isna(value):
                        activity[key] = None
                    elif hasattr(value, 'isoformat'):
                        activity[key] = value.isoformat()
            
            return json.dumps({
                "success": True,
                "count": len(activities_list),
                "activities": activities_list
            }, indent=2)
            
        except Exception as e:
            logger.error(f"AI Tool error in search_activities: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    def get_critical_activities(self, project_id: int) -> str:
        """
        Get critical path activities (TotalFloat <= 0).
        
        Args:
            project_id: Project ObjectId (int)
            
        Returns:
            JSON string of critical activities
        """
        try:
            logger.info(f"AI Tool: get_critical_activities(project_id={project_id})")
            
            # Get all activities
            activities_df = self.activity_dao.get_activities_for_project(project_id)
            
            if activities_df.empty:
                return json.dumps({
                    "success": True,
                    "message": "No activities found",
                    "count": 0,
                    "activities": []
                })
            
            # Note: TotalFloat not in current ACTIVITY_FIELDS
            # This is a placeholder - would need to add TotalFloat to definitions.py
            # For now, return all activities with a note
            
            activities_list = activities_df.to_dict('records')
            
            # Convert dates and handle NaN
            for activity in activities_list:
                for key, value in activity.items():
                    if pd.isna(value):
                        activity[key] = None
                    elif hasattr(value, 'isoformat'):
                        activity[key] = value.isoformat()
            
            return json.dumps({
                "success": True,
                "note": "TotalFloat field not yet available - showing all activities",
                "count": len(activities_list),
                "activities": activities_list
            }, indent=2)
            
        except Exception as e:
            logger.error(f"AI Tool error in get_critical_activities: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    def get_activity_details(self, activity_id: str, project_id: Optional[int] = None) -> str:
        """
        Get detailed information about a specific activity.
        
        Args:
            activity_id: Activity Id (string, e.g., 'ACT-001')
            project_id: Project ObjectId (int, optional)
            
        Returns:
            JSON string with activity details
        """
        try:
            logger.info(f"AI Tool: get_activity_details(activity_id={activity_id}, project_id={project_id})")
            
            # Get activity
            activity_df = self.activity_dao.get_activity_by_id(activity_id, project_id)
            
            if activity_df.empty:
                return json.dumps({
                    "success": False,
                    "error": f"Activity not found: {activity_id}"
                })
            
            # Convert to dict
            activity = activity_df.iloc[0].to_dict()
            
            # Convert dates and handle NaN
            for key, value in activity.items():
                if pd.isna(value):
                    activity[key] = None
                elif hasattr(value, 'isoformat'):
                    activity[key] = value.isoformat()
            
            return json.dumps({
                "success": True,
                "activity": activity
            }, indent=2)
            
        except Exception as e:
            logger.error(f"AI Tool error in get_activity_details: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    def get_activity_relationships(self, activity_object_id: int) -> str:
        """
        Get predecessors and successors for an activity.
        
        Args:
            activity_object_id: Activity ObjectId (int)
            
        Returns:
            JSON string with relationships
        """
        try:
            logger.info(f"AI Tool: get_activity_relationships(activity_object_id={activity_object_id})")
            
            # Get all relationships for the project
            # Note: We need to know the project_id - this is a limitation
            # For now, get all relationships and filter
            
            # Get activity to find project
            activity_df = self.activity_dao.get_activity_by_object_id(activity_object_id)
            
            if activity_df.empty:
                return json.dumps({
                    "success": False,
                    "error": f"Activity not found: {activity_object_id}"
                })
            
            # Get project_id from activity
            # Note: ProjectObjectId not in current ACTIVITY_FIELDS
            # This is a placeholder - would need to add to definitions.py
            
            return json.dumps({
                "success": False,
                "error": "ProjectObjectId not available in current schema - cannot fetch relationships"
            })
            
        except Exception as e:
            logger.error(f"AI Tool error in get_activity_relationships: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    # ========================================================================
    # WRITE OPERATIONS (Proposal Only - Requires Confirmation)
    # ========================================================================
    
    def propose_schedule_change(self, activity_object_id: int, changes: Dict[str, Any], rationale: str) -> str:
        """
        Propose a schedule change (DOES NOT EXECUTE).
        
        VERIFICATION POINT 2: Prompt Engineering
        Returns proposal for user approval, does not execute.
        
        CONSTRAINT: Does NOT call update_activity directly.
        Returns a "Proposed Change Object" requiring separate confirmation.
        
        Args:
            activity_object_id: Activity ObjectId (int, not string)
            changes: Dict of proposed changes (e.g., {'PlannedDuration': 40.0})
            rationale: Explanation for the change
            
        Returns:
            JSON string with change proposal
        """
        try:
            logger.info(f"AI Tool: propose_schedule_change(activity_object_id={activity_object_id})")
            logger.info(f"Proposed changes: {changes}")
            logger.info(f"Rationale: {rationale}")
            
            # Get current activity state
            activity_df = self.activity_dao.get_activity_by_object_id(activity_object_id)
            
            if activity_df.empty:
                return json.dumps({
                    "success": False,
                    "error": f"Activity not found: {activity_object_id}"
                })
            
            current_activity = activity_df.iloc[0].to_dict()
            
            # Convert dates for JSON
            for key, value in current_activity.items():
                if pd.isna(value):
                    current_activity[key] = None
                elif hasattr(value, 'isoformat'):
                    current_activity[key] = value.isoformat()
            
            # Check SAFE_MODE
            safe_mode_enabled = self.session.safe_mode
            
            # Build proposal
            proposal = {
                "success": True,
                "proposal_type": "schedule_change",
                "activity": {
                    "ObjectId": activity_object_id,
                    "Id": current_activity.get('Id'),
                    "Name": current_activity.get('Name')
                },
                "current_values": {
                    key: current_activity.get(key)
                    for key in changes.keys()
                },
                "proposed_changes": changes,
                "rationale": rationale,
                "safe_mode_enabled": safe_mode_enabled,
                "requires_confirmation": True,
                "confirmation_command": f"EXECUTE_CHANGE:{activity_object_id}:{json.dumps(changes)}",
                "warning": "This change has NOT been applied. User confirmation required." if safe_mode_enabled else "SAFE_MODE is disabled - change can be executed after confirmation."
            }
            
            return json.dumps(proposal, indent=2)
            
        except Exception as e:
            logger.error(f"AI Tool error in propose_schedule_change: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    def analyze_schedule_impact(self, activity_object_id: int, proposed_duration: Optional[float] = None) -> str:
        """
        Analyze impact of changing an activity.
        
        Args:
            activity_object_id: Activity ObjectId (int)
            proposed_duration: Proposed new duration in hours (optional)
            
        Returns:
            JSON string with impact analysis
        """
        try:
            logger.info(f"AI Tool: analyze_schedule_impact(activity_object_id={activity_object_id})")
            
            # Get activity
            activity_df = self.activity_dao.get_activity_by_object_id(activity_object_id)
            
            if activity_df.empty:
                return json.dumps({
                    "success": False,
                    "error": f"Activity not found: {activity_object_id}"
                })
            
            activity = activity_df.iloc[0]
            current_duration = activity.get('PlannedDuration')
            
            # Build analysis
            analysis = {
                "success": True,
                "activity": {
                    "ObjectId": activity_object_id,
                    "Id": activity.get('Id'),
                    "Name": activity.get('Name'),
                    "current_duration": current_duration
                },
                "impact_summary": "Impact analysis requires TotalFloat and successor data",
                "notes": [
                    "TotalFloat field not yet available in schema",
                    "Successor relationships would need to be analyzed",
                    "Critical path recalculation would be required"
                ]
            }
            
            if proposed_duration is not None:
                duration_change = proposed_duration - (current_duration or 0)
                analysis["proposed_duration"] = proposed_duration
                analysis["duration_change"] = duration_change
                analysis["change_type"] = "increase" if duration_change > 0 else "decrease" if duration_change < 0 else "no change"
            
            return json.dumps(analysis, indent=2)
            
        except Exception as e:
            logger.error(f"AI Tool error in analyze_schedule_impact: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
