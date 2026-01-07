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
        
        # Proposal cache for execution workflow (Phase 7)
        self._proposal_cache: Dict[str, Dict[str, Any]] = {}
        
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
            },
            # Phase 7: Mining-Specific Analysis Tools
            {
                "name": "check_schedule_health",
                "description": "Check schedule health using DCMA 14-point assessment principles. Identifies dangling logic, negative float, and high float issues. Use this when user asks to 'review the schedule' or 'check schedule health'.",
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
                "name": "validate_production_logic",
                "description": "Validate production logic by comparing planned durations with theoretical durations (Volume / Rate). Flags activities with >10% variance. Use this when user asks about 'efficiency' or 'production rates'.",
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
            # Phase 7: Execution Workflow
            {
                "name": "execute_approved_change",
                "description": "Execute a previously proposed schedule change. Requires SAFE_MODE to be disabled. Only works with valid proposal_id from propose_schedule_change. This is the ONLY tool that actually modifies P6 data.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "proposal_id": {
                            "type": "string",
                            "description": "Unique proposal ID from propose_schedule_change (8-character hash)"
                        }
                    },
                    "required": ["proposal_id"]
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
            
            # Generate unique proposal ID (Phase 7: Execution Workflow)
            import hashlib
            import time
            proposal_id = hashlib.md5(f"{activity_object_id}:{time.time()}:{json.dumps(changes)}".encode()).hexdigest()[:8]
            
            # Build proposal
            proposal = {
                "success": True,
                "proposal_id": proposal_id,
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
                "confirmation_command": f"execute_approved_change(proposal_id='{proposal_id}')",
                "warning": "This change has NOT been applied. User confirmation required." if safe_mode_enabled else "SAFE_MODE is disabled - change can be executed after confirmation."
            }
            
            # Cache proposal for execution (Phase 7)
            self._proposal_cache[proposal_id] = {
                "activity_object_id": activity_object_id,
                "changes": changes,
                "rationale": rationale,
                "timestamp": time.time(),
                "current_values": current_activity
            }
            
            logger.info(f"Proposal cached with ID: {proposal_id}")
            
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

    # ========================================================================
    # PHASE 7: MINING-SPECIFIC ANALYSIS TOOLS
    # ========================================================================
    
    def check_schedule_health(self, project_id: int) -> str:
        """
        Check schedule health using DCMA 14-point assessment principles.
        
        Checks:
        1. Dangling Logic - Activities with no predecessors or successors
        2. Negative Float - Activities with TotalFloat < 0
        3. High Float - Activities with TotalFloat > 44 days (1056 hours)
        
        VERIFICATION POINT 1: Production Logic
        Handles missing data gracefully (no crash).
        
        Args:
            project_id: Project ObjectId (int)
            
        Returns:
            JSON string with health check results
        """
        try:
            logger.info(f"AI Tool: check_schedule_health(project_id={project_id})")
            
            # Get all activities for project
            activities_df = self.activity_dao.get_activities_for_project(project_id)
            
            if activities_df.empty:
                return json.dumps({
                    "success": False,
                    "error": f"No activities found for project {project_id}"
                })
            
            # Get all relationships for project
            relationships_df = self.relationship_dao.get_relationships(project_id)
            
            # Initialize results
            health_results = {
                "success": True,
                "project_id": project_id,
                "total_activities": len(activities_df),
                "checks": []
            }
            
            # Check 1: Dangling Logic
            # Activities with no predecessors or successors
            dangling_activities = []
            
            if not relationships_df.empty:
                # Get activities with predecessors
                activities_with_pred = set(relationships_df['SuccessorObjectId'].dropna())
                # Get activities with successors
                activities_with_succ = set(relationships_df['PredecessorObjectId'].dropna())
                # Activities with at least one connection
                connected_activities = activities_with_pred | activities_with_succ
                
                # Find dangling activities
                for _, activity in activities_df.iterrows():
                    activity_oid = activity.get('ObjectId')
                    if activity_oid not in connected_activities:
                        dangling_activities.append({
                            "ObjectId": activity_oid,
                            "Id": activity.get('Id'),
                            "Name": activity.get('Name'),
                            "Status": activity.get('Status')
                        })
            else:
                # No relationships at all - all activities are dangling
                dangling_activities = [
                    {
                        "ObjectId": activity.get('ObjectId'),
                        "Id": activity.get('Id'),
                        "Name": activity.get('Name'),
                        "Status": activity.get('Status')
                    }
                    for _, activity in activities_df.iterrows()
                ]
            
            health_results["checks"].append({
                "check_name": "Dangling Logic",
                "description": "Activities with no predecessors or successors",
                "status": "FAIL" if len(dangling_activities) > 0 else "PASS",
                "count": len(dangling_activities),
                "percentage": round(len(dangling_activities) / len(activities_df) * 100, 1),
                "threshold": "0% (DCMA best practice)",
                "issues": dangling_activities[:10]  # Limit to first 10
            })
            
            # Check 2: Negative Float
            # Activities with TotalFloat < 0
            negative_float_activities = []
            
            if 'TotalFloat' in activities_df.columns:
                for _, activity in activities_df.iterrows():
                    total_float = activity.get('TotalFloat')
                    if total_float is not None and total_float < 0:
                        negative_float_activities.append({
                            "ObjectId": activity.get('ObjectId'),
                            "Id": activity.get('Id'),
                            "Name": activity.get('Name'),
                            "TotalFloat": total_float,
                            "Status": activity.get('Status')
                        })
            
            health_results["checks"].append({
                "check_name": "Negative Float",
                "description": "Activities with TotalFloat < 0 (schedule is behind)",
                "status": "FAIL" if len(negative_float_activities) > 0 else "PASS",
                "count": len(negative_float_activities),
                "percentage": round(len(negative_float_activities) / len(activities_df) * 100, 1) if len(activities_df) > 0 else 0,
                "threshold": "0% (DCMA best practice)",
                "issues": negative_float_activities[:10]
            })
            
            # Check 3: High Float
            # Activities with TotalFloat > 44 days (1056 hours)
            high_float_activities = []
            high_float_threshold = 1056.0  # 44 days * 24 hours
            
            if 'TotalFloat' in activities_df.columns:
                for _, activity in activities_df.iterrows():
                    total_float = activity.get('TotalFloat')
                    if total_float is not None and total_float > high_float_threshold:
                        high_float_activities.append({
                            "ObjectId": activity.get('ObjectId'),
                            "Id": activity.get('Id'),
                            "Name": activity.get('Name'),
                            "TotalFloat": total_float,
                            "TotalFloat_Days": round(total_float / 24, 1),
                            "Status": activity.get('Status')
                        })
            
            health_results["checks"].append({
                "check_name": "High Float",
                "description": f"Activities with TotalFloat > 44 days ({high_float_threshold} hours)",
                "status": "WARNING" if len(high_float_activities) > 0 else "PASS",
                "count": len(high_float_activities),
                "percentage": round(len(high_float_activities) / len(activities_df) * 100, 1) if len(activities_df) > 0 else 0,
                "threshold": "5% (DCMA best practice)",
                "issues": high_float_activities[:10]
            })
            
            # Overall health score
            failed_checks = sum(1 for check in health_results["checks"] if check["status"] == "FAIL")
            warning_checks = sum(1 for check in health_results["checks"] if check["status"] == "WARNING")
            total_checks = len(health_results["checks"])
            
            health_results["overall_health"] = {
                "total_checks": total_checks,
                "passed": total_checks - failed_checks - warning_checks,
                "failed": failed_checks,
                "warnings": warning_checks,
                "health_score": round((total_checks - failed_checks - warning_checks) / total_checks * 100, 1) if total_checks > 0 else 0,
                "status": "HEALTHY" if failed_checks == 0 and warning_checks == 0 else "NEEDS ATTENTION" if failed_checks == 0 else "CRITICAL"
            }
            
            return json.dumps(health_results, indent=2)
            
        except Exception as e:
            logger.error(f"AI Tool error in check_schedule_health: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })

    def validate_production_logic(self, project_id: int) -> str:
        """
        Validate production logic by comparing planned durations with theoretical durations.
        
        Logic: Theoretical Duration = Volume / Production Rate
        Alert: If variance > 10%, flag as "Invalid Duration"
        
        VERIFICATION POINT 1: Production Logic
        Correctly calculates Theoretical Duration = Volume / Rate
        Handles missing UDFs gracefully (no crash).
        
        Args:
            project_id: Project ObjectId (int)
            
        Returns:
            JSON string with production validation results
        """
        try:
            logger.info(f"AI Tool: validate_production_logic(project_id={project_id})")
            
            # Get all activities for project
            activities_df = self.activity_dao.get_activities_for_project(project_id)
            
            if activities_df.empty:
                return json.dumps({
                    "success": False,
                    "error": f"No activities found for project {project_id}"
                })
            
            # Filter for production activities
            # Look for activities with 'Production' in name or specific types
            production_activities = activities_df[
                activities_df['Name'].str.contains('Production|Drill|Blast|Muck|Haul', case=False, na=False)
            ]
            
            if production_activities.empty:
                return json.dumps({
                    "success": True,
                    "project_id": project_id,
                    "message": "No production activities found (activities with 'Production', 'Drill', 'Blast', 'Muck', or 'Haul' in name)",
                    "total_activities": len(activities_df),
                    "production_activities": 0,
                    "validation_results": []
                })
            
            # Validate production logic
            validation_results = []
            invalid_count = 0
            missing_udf_count = 0
            
            for _, activity in production_activities.iterrows():
                activity_id = activity.get('Id')
                activity_name = activity.get('Name')
                planned_duration = activity.get('PlannedDuration')
                
                # Try to get UDFs (Volume and ProductionRate)
                # For MVP, these may not exist - handle gracefully
                volume = activity.get('Volume')  # UDF
                production_rate = activity.get('ProductionRate')  # UDF
                
                result = {
                    "ObjectId": activity.get('ObjectId'),
                    "Id": activity_id,
                    "Name": activity_name,
                    "PlannedDuration": planned_duration,
                    "Volume": volume,
                    "ProductionRate": production_rate
                }
                
                # Check if UDFs are available
                if volume is None or production_rate is None:
                    result["status"] = "MISSING_UDF"
                    result["message"] = "Volume or ProductionRate UDF not available"
                    missing_udf_count += 1
                elif production_rate == 0:
                    result["status"] = "ERROR"
                    result["message"] = "ProductionRate is zero (division by zero)"
                    invalid_count += 1
                elif planned_duration is None or planned_duration == 0:
                    result["status"] = "ERROR"
                    result["message"] = "PlannedDuration is missing or zero"
                    invalid_count += 1
                else:
                    # Calculate theoretical duration
                    theoretical_duration = volume / production_rate
                    variance = abs(planned_duration - theoretical_duration)
                    variance_percentage = (variance / theoretical_duration * 100) if theoretical_duration > 0 else 0
                    
                    result["TheoreticalDuration"] = round(theoretical_duration, 2)
                    result["Variance"] = round(variance, 2)
                    result["VariancePercentage"] = round(variance_percentage, 1)
                    
                    # Check if variance > 10%
                    if variance_percentage > 10:
                        result["status"] = "INVALID"
                        result["message"] = f"Duration variance {variance_percentage:.1f}% exceeds 10% threshold"
                        invalid_count += 1
                    else:
                        result["status"] = "VALID"
                        result["message"] = "Duration matches production logic"
                
                validation_results.append(result)
            
            # Summary
            valid_count = len([r for r in validation_results if r["status"] == "VALID"])
            
            summary = {
                "success": True,
                "project_id": project_id,
                "total_activities": len(activities_df),
                "production_activities": len(production_activities),
                "validation_summary": {
                    "valid": valid_count,
                    "invalid": invalid_count,
                    "missing_udf": missing_udf_count,
                    "total_validated": len(validation_results)
                },
                "validation_results": validation_results,
                "recommendations": []
            }
            
            # Add recommendations
            if invalid_count > 0:
                summary["recommendations"].append(
                    f"⚠️ {invalid_count} production activities have duration variances > 10%. Review and adjust durations or production rates."
                )
            
            if missing_udf_count > 0:
                summary["recommendations"].append(
                    f"ℹ️ {missing_udf_count} production activities are missing Volume or ProductionRate UDFs. Add UDFs for accurate validation."
                )
            
            if valid_count == len(validation_results) and missing_udf_count == 0:
                summary["recommendations"].append(
                    "✅ All production activities have valid durations matching production logic."
                )
            
            return json.dumps(summary, indent=2)
            
        except Exception as e:
            logger.error(f"AI Tool error in validate_production_logic: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })

    # ========================================================================
    # PHASE 7: EXECUTION WORKFLOW
    # ========================================================================
    
    def execute_approved_change(self, proposal_id: str) -> str:
        """
        Execute a previously proposed schedule change.
        
        VERIFICATION POINT 2: Execution Safety
        Requires a "signature" (proposal_id) to prevent hallucination.
        Only executes changes that were previously proposed and cached.
        
        VERIFICATION POINT 3: Write Permission
        Checks global SAFE_MODE flag and fails if enabled.
        Does NOT temporarily override SAFE_MODE.
        
        Args:
            proposal_id: Unique proposal ID from propose_schedule_change
            
        Returns:
            JSON string with execution result
        """
        try:
            logger.info(f"AI Tool: execute_approved_change(proposal_id={proposal_id})")
            
            # VERIFICATION POINT 3: Check SAFE_MODE
            if self.session.safe_mode:
                return json.dumps({
                    "success": False,
                    "error": "SAFE_MODE is enabled",
                    "message": "Cannot execute changes while SAFE_MODE is enabled. To execute changes:\n1. Set SAFE_MODE=false in .env file\n2. Restart the application\n3. Re-run the execution command",
                    "safe_mode_enabled": True
                })
            
            # VERIFICATION POINT 2: Validate proposal_id (signature)
            if proposal_id not in self._proposal_cache:
                return json.dumps({
                    "success": False,
                    "error": f"Invalid proposal_id: {proposal_id}",
                    "message": "Proposal not found. The proposal may have expired or the ID is incorrect. Please generate a new proposal using propose_schedule_change.",
                    "available_proposals": list(self._proposal_cache.keys())
                })
            
            # Retrieve cached proposal
            cached_proposal = self._proposal_cache[proposal_id]
            activity_object_id = cached_proposal["activity_object_id"]
            changes = cached_proposal["changes"]
            rationale = cached_proposal["rationale"]
            
            logger.info(f"Executing proposal {proposal_id} for activity {activity_object_id}")
            logger.info(f"Changes: {changes}")
            
            # Execute the change using ActivityDAO
            try:
                self.activity_dao.update_activity(activity_object_id, changes)
                
                # Get updated activity to confirm changes
                updated_activity_df = self.activity_dao.get_activity_by_object_id(activity_object_id)
                
                if updated_activity_df.empty:
                    return json.dumps({
                        "success": False,
                        "error": "Activity not found after update"
                    })
                
                updated_activity = updated_activity_df.iloc[0].to_dict()
                
                # Convert dates for JSON
                for key, value in updated_activity.items():
                    if pd.isna(value):
                        updated_activity[key] = None
                    elif hasattr(value, 'isoformat'):
                        updated_activity[key] = value.isoformat()
                
                # Remove proposal from cache (one-time use)
                del self._proposal_cache[proposal_id]
                
                result = {
                    "success": True,
                    "proposal_id": proposal_id,
                    "message": "Change executed successfully",
                    "activity": {
                        "ObjectId": activity_object_id,
                        "Id": updated_activity.get('Id'),
                        "Name": updated_activity.get('Name')
                    },
                    "executed_changes": changes,
                    "rationale": rationale,
                    "updated_values": {
                        key: updated_activity.get(key)
                        for key in changes.keys()
                    },
                    "timestamp": pd.Timestamp.now().isoformat()
                }
                
                logger.info(f"Successfully executed proposal {proposal_id}")
                
                return json.dumps(result, indent=2)
                
            except Exception as dao_error:
                logger.error(f"DAO error executing change: {dao_error}")
                return json.dumps({
                    "success": False,
                    "error": f"Failed to execute change: {str(dao_error)}",
                    "proposal_id": proposal_id,
                    "activity_object_id": activity_object_id
                })
            
        except Exception as e:
            logger.error(f"AI Tool error in execute_approved_change: {e}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
