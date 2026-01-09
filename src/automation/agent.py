#!/usr/bin/env python3
"""
P6 AI Agent Integration Module.

Provides AI agent interface for P6 automation:
- Natural language command processing
- Action execution
- Result formatting for LLMs
- Tool definitions for agent frameworks
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from src.utils import logger


class ActionType(Enum):
    """Types of P6 actions."""
    # Connection
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    CHECK_STATUS = "check_status"
    
    # Projects
    LIST_PROJECTS = "list_projects"
    OPEN_PROJECT = "open_project"
    CLOSE_PROJECT = "close_project"
    
    # Layouts
    LIST_LAYOUTS = "list_layouts"
    APPLY_LAYOUT = "apply_layout"
    SWITCH_VIEW = "switch_view"
    
    # Printing
    PRINT_PDF = "print_pdf"
    
    # Export
    EXPORT_XER = "export_xer"
    EXPORT_XML = "export_xml"
    EXPORT_EXCEL = "export_excel"
    
    # Scheduling
    SCHEDULE_PROJECT = "schedule_project"
    LEVEL_RESOURCES = "level_resources"
    CHECK_SCHEDULE = "check_schedule"
    
    # Batch
    BATCH_PRINT = "batch_print"
    BATCH_EXPORT = "batch_export"
    
    # Activities
    SELECT_ACTIVITY = "select_activity"
    GET_ACTIVITY_COUNT = "get_activity_count"


@dataclass
class ActionResult:
    """Result of an agent action."""
    success: bool
    action: str
    message: str
    data: Optional[Dict] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)


class P6AgentInterface:
    """
    AI Agent interface for P6 automation.
    
    Provides a unified interface for AI agents to interact with P6.
    Accepts natural language-like commands and returns structured results.
    
    Example:
        agent = P6AgentInterface(automation)
        result = agent.execute("open_project", project_name="Highway Extension")
        result = agent.execute("print_pdf", filename="report.pdf")
    """
    
    def __init__(
        self,
        automation=None,
        project_manager=None,
        layout_manager=None,
        print_manager=None,
        export_manager=None,
        schedule_manager=None,
        activity_manager=None,
        batch_processor=None
    ):
        """
        Initialize agent interface.
        
        Args:
            automation: P6AutomationBase or P6PrintAutomation instance
            project_manager: P6ProjectManager instance
            layout_manager: P6LayoutManager instance
            print_manager: P6PrintManager instance
            export_manager: P6ExportManager instance
            schedule_manager: P6ScheduleManager instance
            activity_manager: P6ActivityManager instance
            batch_processor: P6BatchProcessor instance
        """
        self.automation = automation
        self.projects = project_manager
        self.layouts = layout_manager
        self.printer = print_manager
        self.exporter = export_manager
        self.scheduler = schedule_manager
        self.activities = activity_manager
        self.batch = batch_processor
        
        # Build action handlers
        self._handlers = self._build_handlers()
        
        logger.debug("P6AgentInterface initialized")
    
    def _build_handlers(self) -> Dict[str, Callable]:
        """Build action handler mapping."""
        return {
            # Connection
            ActionType.CHECK_STATUS.value: self._handle_check_status,
            
            # Projects
            ActionType.LIST_PROJECTS.value: self._handle_list_projects,
            ActionType.OPEN_PROJECT.value: self._handle_open_project,
            ActionType.CLOSE_PROJECT.value: self._handle_close_project,
            
            # Layouts
            ActionType.LIST_LAYOUTS.value: self._handle_list_layouts,
            ActionType.APPLY_LAYOUT.value: self._handle_apply_layout,
            ActionType.SWITCH_VIEW.value: self._handle_switch_view,
            
            # Printing
            ActionType.PRINT_PDF.value: self._handle_print_pdf,
            
            # Export
            ActionType.EXPORT_XER.value: self._handle_export_xer,
            ActionType.EXPORT_XML.value: self._handle_export_xml,
            ActionType.EXPORT_EXCEL.value: self._handle_export_excel,
            
            # Scheduling
            ActionType.SCHEDULE_PROJECT.value: self._handle_schedule,
            ActionType.CHECK_SCHEDULE.value: self._handle_check_schedule,
            
            # Activities
            ActionType.SELECT_ACTIVITY.value: self._handle_select_activity,
            ActionType.GET_ACTIVITY_COUNT.value: self._handle_get_activity_count,
        }
    
    # =========================================================================
    # Main Execute Method
    # =========================================================================
    
    def execute(self, action: str, **kwargs) -> ActionResult:
        """
        Execute a P6 action.
        
        Args:
            action: Action name (e.g., "open_project", "print_pdf")
            **kwargs: Action parameters
            
        Returns:
            ActionResult with success status and data
        """
        logger.info(f"Agent executing: {action} with {kwargs}")
        
        handler = self._handlers.get(action)
        
        if not handler:
            return ActionResult(
                success=False,
                action=action,
                message=f"Unknown action: {action}",
                error=f"Action '{action}' is not supported"
            )
        
        try:
            return handler(**kwargs)
        except Exception as e:
            logger.error(f"Action failed: {action} - {e}")
            return ActionResult(
                success=False,
                action=action,
                message=f"Action failed: {e}",
                error=str(e)
            )
    
    def get_available_actions(self) -> List[str]:
        """Get list of available actions."""
        return list(self._handlers.keys())
    
    # =========================================================================
    # Action Handlers
    # =========================================================================
    
    def _handle_check_status(self, **kwargs) -> ActionResult:
        """Check P6 connection status."""
        is_connected = self.automation and self.automation.is_connected
        return ActionResult(
            success=True,
            action="check_status",
            message="P6 is connected" if is_connected else "P6 is not connected",
            data={"connected": is_connected}
        )
    
    def _handle_list_projects(self, **kwargs) -> ActionResult:
        """List available projects."""
        if not self.projects:
            return self._missing_component("project_manager")
        
        tree = self.projects.get_project_tree()
        all_projects = []
        for eps_projects in tree.values():
            all_projects.extend(eps_projects)
        
        return ActionResult(
            success=True,
            action="list_projects",
            message=f"Found {len(all_projects)} projects",
            data={"projects": all_projects, "tree": tree}
        )
    
    def _handle_open_project(self, project_name: str = None, **kwargs) -> ActionResult:
        """Open a project."""
        if not project_name:
            return ActionResult(
                success=False,
                action="open_project",
                message="project_name is required",
                error="Missing required parameter: project_name"
            )
        
        if not self.projects:
            return self._missing_component("project_manager")
        
        success = self.projects.open_project(project_name)
        return ActionResult(
            success=success,
            action="open_project",
            message=f"Opened project: {project_name}" if success else "Failed to open",
            data={"project_name": project_name}
        )
    
    def _handle_close_project(self, **kwargs) -> ActionResult:
        """Close current project."""
        if not self.projects:
            return self._missing_component("project_manager")
        
        success = self.projects.close_project()
        return ActionResult(
            success=success,
            action="close_project",
            message="Project closed" if success else "Failed to close"
        )
    
    def _handle_list_layouts(self, **kwargs) -> ActionResult:
        """List available layouts."""
        if not self.layouts:
            return self._missing_component("layout_manager")
        
        layouts = self.layouts.get_available_layouts()
        return ActionResult(
            success=True,
            action="list_layouts",
            message=f"Found {len(layouts)} layouts",
            data={"layouts": layouts}
        )
    
    def _handle_apply_layout(self, layout_name: str = None, **kwargs) -> ActionResult:
        """Apply a layout."""
        if not layout_name:
            return ActionResult(
                success=False,
                action="apply_layout",
                message="layout_name is required",
                error="Missing required parameter"
            )
        
        if not self.layouts:
            return self._missing_component("layout_manager")
        
        success = self.layouts.open_layout(layout_name)
        return ActionResult(
            success=success,
            action="apply_layout",
            message=f"Applied layout: {layout_name}" if success else "Failed"
        )
    
    def _handle_switch_view(self, view_name: str = None, **kwargs) -> ActionResult:
        """Switch to a view."""
        if not view_name:
            return ActionResult(
                success=False,
                action="switch_view",
                message="view_name is required"
            )
        
        if not self.layouts:
            return self._missing_component("layout_manager")
        
        from .layouts import P6View
        view = P6View(view_name)
        success = self.layouts.switch_view(view)
        return ActionResult(
            success=success,
            action="switch_view",
            message=f"Switched to {view_name}" if success else "Failed"
        )
    
    def _handle_print_pdf(self, filename: str = None, **kwargs) -> ActionResult:
        """Print to PDF."""
        if not filename:
            filename = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        if not self.printer:
            return self._missing_component("print_manager")
        
        path = self.printer.print_to_pdf(filename)
        return ActionResult(
            success=True,
            action="print_pdf",
            message=f"Printed to: {path}",
            data={"output_path": str(path)}
        )
    
    def _handle_export_xer(self, filename: str = None, **kwargs) -> ActionResult:
        """Export to XER."""
        if not filename:
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xer"
        
        if not self.exporter:
            return self._missing_component("export_manager")
        
        path = self.exporter.export_to_xer(filename)
        return ActionResult(
            success=True,
            action="export_xer",
            message=f"Exported to: {path}",
            data={"output_path": str(path)}
        )
    
    def _handle_export_xml(self, filename: str = None, **kwargs) -> ActionResult:
        """Export to XML."""
        if not filename:
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
        
        if not self.exporter:
            return self._missing_component("export_manager")
        
        path = self.exporter.export_to_xml(filename)
        return ActionResult(
            success=True,
            action="export_xml",
            message=f"Exported to: {path}",
            data={"output_path": str(path)}
        )
    
    def _handle_export_excel(self, filename: str = None, **kwargs) -> ActionResult:
        """Export to Excel."""
        if not filename:
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        if not self.exporter:
            return self._missing_component("export_manager")
        
        path = self.exporter.export_to_excel(filename)
        return ActionResult(
            success=True,
            action="export_excel",
            message=f"Exported to: {path}",
            data={"output_path": str(path)}
        )
    
    def _handle_schedule(self, **kwargs) -> ActionResult:
        """Schedule project (F9)."""
        if not self.scheduler:
            return self._missing_component("schedule_manager")
        
        success = self.scheduler.schedule_project()
        return ActionResult(
            success=success,
            action="schedule_project",
            message="Schedule complete" if success else "Failed"
        )
    
    def _handle_check_schedule(self, **kwargs) -> ActionResult:
        """Run schedule check."""
        if not self.scheduler:
            return self._missing_component("schedule_manager")
        
        results = self.scheduler.check_schedule()
        return ActionResult(
            success=results.get('ran', False),
            action="check_schedule",
            message="Schedule check complete",
            data=results
        )
    
    def _handle_select_activity(self, activity_id: str = None, **kwargs) -> ActionResult:
        """Select an activity."""
        if not activity_id:
            return ActionResult(
                success=False,
                action="select_activity",
                message="activity_id is required"
            )
        
        if not self.activities:
            return self._missing_component("activity_manager")
        
        success = self.activities.select_activity(activity_id)
        return ActionResult(
            success=success,
            action="select_activity",
            message=f"Selected: {activity_id}" if success else "Not found"
        )
    
    def _handle_get_activity_count(self, **kwargs) -> ActionResult:
        """Get activity count."""
        if not self.activities:
            return self._missing_component("activity_manager")
        
        count = self.activities.get_activity_count()
        return ActionResult(
            success=count is not None,
            action="get_activity_count",
            message=f"Activity count: {count}",
            data={"count": count}
        )
    
    def _missing_component(self, component: str) -> ActionResult:
        """Return error for missing component."""
        return ActionResult(
            success=False,
            action="error",
            message=f"Component not configured: {component}",
            error=f"{component} is required but not initialized"
        )
    
    # =========================================================================
    # Tool Definitions (for LLM function calling)
    # =========================================================================
    
    def get_tool_definitions(self) -> List[Dict]:
        """
        Get OpenAI-compatible tool definitions.
        
        Returns:
            List of tool definitions for LLM function calling
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_projects",
                    "description": "List all available P6 projects",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "open_project",
                    "description": "Open a P6 project by name",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_name": {
                                "type": "string",
                                "description": "Name of the project to open"
                            }
                        },
                        "required": ["project_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "print_pdf",
                    "description": "Print the current view to PDF",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "Output PDF filename"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "apply_layout",
                    "description": "Apply a saved layout to the current view",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "layout_name": {
                                "type": "string",
                                "description": "Name of the layout to apply"
                            }
                        },
                        "required": ["layout_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "schedule_project",
                    "description": "Run schedule calculation (F9) on the current project",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "export_xer",
                    "description": "Export the current project to XER format",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "Output XER filename"
                            }
                        }
                    }
                }
            }
        ]
