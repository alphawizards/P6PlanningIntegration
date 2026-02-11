#!/usr/bin/env python3
"""
P6 GUI Tools for AI Agent.

Per agents.md Phase 2:
"Create a wrapper class P6GUITools that exposes the methods from
P6ActivityManager to the LLM."

This module provides tool definitions that the AI agent can call
to control the P6 GUI directly.

Architecture:
- Layer 2: Orchestration (The Brain) - This is called by P6Agent
- Layer 3: Execution (The Tools) - This calls P6ActivityManager
"""

import json
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

# Import from parent project
try:
    from src.utils import logger
    from src.config.settings import SAFE_MODE
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    SAFE_MODE = True

# Import the enhanced activity manager
from src.automation.activities import P6ActivityManager, ConstraintType


class ToolCategory(Enum):
    """Categories of GUI tools."""
    NAVIGATION = "navigation"
    EDITING = "editing"
    SCHEDULING = "scheduling"
    SELECTION = "selection"


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_json(self) -> str:
        """Convert to JSON string for LLM consumption."""
        return json.dumps(asdict(self), indent=2)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ToolDefinition:
    """Definition of a tool for LLM function calling."""
    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, Any]
    requires_unsafe_mode: bool = False

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    def to_anthropic_format(self) -> Dict[str, Any]:
        """Convert to Anthropic tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters
        }


class P6GUITools:
    """
    GUI Tools wrapper for AI Agent.

    Per agents.md:
    "Implement a P6GUITools class similar to src/ai/tools.py
    but mapping to P6ActivityManager (automation) instead of ActivityDAO."

    System Prompt Update Required:
    "You are a GUI agent. You interact with the P6 window directly.
    Do not assume direct database access."
    """

    # System prompt for the LLM
    SYSTEM_PROMPT = """You are a P6 GUI Agent controlling Oracle Primavera P6 Professional directly.

IMPORTANT: You interact with the P6 window through keyboard and mouse automation.
You do NOT have direct database access. All operations go through the GUI.

Available Capabilities:
- Select and navigate to activities
- Edit activity fields (duration, dates, names, etc.)
- Set and clear constraints
- Add and delete activities
- Schedule the project (F9)

Safety Rules:
1. Always confirm destructive actions (delete, clear) with the user first
2. Respect SAFE_MODE - editing operations will fail if SAFE_MODE=True
3. Log all actions for audit purposes

When the user asks to modify something:
1. First select/find the activity
2. Navigate to the correct column
3. Enter the new value
4. Confirm the change

Always report back what you did and whether it succeeded."""

    def __init__(self, main_window, safe_mode: bool = None):
        """
        Initialize GUI tools.

        Args:
            main_window: P6 main window (pywinauto wrapper)
            safe_mode: Override SAFE_MODE (default: use config)
        """
        self._window = main_window
        self.safe_mode = safe_mode if safe_mode is not None else SAFE_MODE

        # Initialize the activity manager
        self._activity_manager = P6ActivityManager(main_window, safe_mode=self.safe_mode)

        # Build tool registry
        self._tools: Dict[str, Callable] = {}
        self._tool_definitions: List[ToolDefinition] = []
        self._register_tools()

        logger.info(f"P6GUITools initialized with {len(self._tools)} tools (safe_mode={self.safe_mode})")

    def _register_tools(self):
        """Register all available GUI tools."""

        # =================================================================
        # Selection Tools
        # =================================================================

        self._register_tool(
            name="select_activity",
            description="Select an activity by its Activity ID. This highlights the activity row in P6.",
            category=ToolCategory.SELECTION,
            parameters={
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": "The Activity ID to select (e.g., 'A1010')"
                    }
                },
                "required": ["activity_id"]
            },
            handler=self._handle_select_activity,
            requires_unsafe_mode=False
        )

        self._register_tool(
            name="get_visible_columns",
            description="Get the list of visible columns in the current P6 view. Returns column names in display order.",
            category=ToolCategory.NAVIGATION,
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self._handle_get_columns,
            requires_unsafe_mode=False
        )

        # =================================================================
        # Editing Tools (require unsafe mode)
        # =================================================================

        self._register_tool(
            name="update_activity_gui",
            description="Edit a field value for an activity. Uses keyboard navigation to find and edit the cell.",
            category=ToolCategory.EDITING,
            parameters={
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": "The Activity ID to edit"
                    },
                    "field": {
                        "type": "string",
                        "description": "The column/field name to edit (e.g., 'Original Duration', 'Activity Name')"
                    },
                    "value": {
                        "type": "string",
                        "description": "The new value to set"
                    }
                },
                "required": ["activity_id", "field", "value"]
            },
            handler=self._handle_update_activity,
            requires_unsafe_mode=True
        )

        self._register_tool(
            name="set_activity_constraint",
            description="Set a constraint on an activity (e.g., 'Start On or After', 'Must Finish By').",
            category=ToolCategory.EDITING,
            parameters={
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": "The Activity ID to constrain"
                    },
                    "constraint_type": {
                        "type": "string",
                        "enum": [ct.value for ct in ConstraintType],
                        "description": "Type of constraint"
                    },
                    "constraint_date": {
                        "type": "string",
                        "description": "The constraint date (e.g., '15-Jan-26')"
                    }
                },
                "required": ["activity_id", "constraint_type", "constraint_date"]
            },
            handler=self._handle_set_constraint,
            requires_unsafe_mode=True
        )

        self._register_tool(
            name="clear_activity_constraint",
            description="Remove/clear the constraint from an activity.",
            category=ToolCategory.EDITING,
            parameters={
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": "The Activity ID to clear constraint from"
                    }
                },
                "required": ["activity_id"]
            },
            handler=self._handle_clear_constraint,
            requires_unsafe_mode=True
        )

        self._register_tool(
            name="add_activity_gui",
            description="Add a new activity to the project.",
            category=ToolCategory.EDITING,
            parameters={
                "type": "object",
                "properties": {
                    "wbs_path": {
                        "type": "string",
                        "description": "Optional WBS path to add the activity under"
                    }
                },
                "required": []
            },
            handler=self._handle_add_activity,
            requires_unsafe_mode=True
        )

        self._register_tool(
            name="delete_activity_gui",
            description="Delete an activity from the project. WARNING: This is destructive!",
            category=ToolCategory.EDITING,
            parameters={
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": "The Activity ID to delete"
                    }
                },
                "required": ["activity_id"]
            },
            handler=self._handle_delete_activity,
            requires_unsafe_mode=True
        )

        # =================================================================
        # Scheduling Tools
        # =================================================================

        self._register_tool(
            name="reschedule_project_gui",
            description="Run the project scheduler (F9). Recalculates all dates based on logic and constraints.",
            category=ToolCategory.SCHEDULING,
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self._handle_reschedule,
            requires_unsafe_mode=True
        )

        # =================================================================
        # Navigation Tools
        # =================================================================

        self._register_tool(
            name="navigate_to_activity",
            description="Navigate to and select an activity, making it visible in the view.",
            category=ToolCategory.NAVIGATION,
            parameters={
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": "The Activity ID to navigate to"
                    }
                },
                "required": ["activity_id"]
            },
            handler=self._handle_navigate_to_activity,
            requires_unsafe_mode=False
        )

        self._register_tool(
            name="go_to_first_activity",
            description="Navigate to the first activity in the view.",
            category=ToolCategory.NAVIGATION,
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self._handle_go_first,
            requires_unsafe_mode=False
        )

        self._register_tool(
            name="go_to_last_activity",
            description="Navigate to the last activity in the view.",
            category=ToolCategory.NAVIGATION,
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            handler=self._handle_go_last,
            requires_unsafe_mode=False
        )

    def _register_tool(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        parameters: Dict[str, Any],
        handler: Callable,
        requires_unsafe_mode: bool = False
    ):
        """Register a tool with its handler."""
        self._tools[name] = handler
        self._tool_definitions.append(ToolDefinition(
            name=name,
            description=description,
            category=category,
            parameters=parameters,
            requires_unsafe_mode=requires_unsafe_mode
        ))

    # =========================================================================
    # Tool Handlers
    # =========================================================================

    def _handle_select_activity(self, activity_id: str) -> ToolResult:
        """Handle select_activity tool call."""
        try:
            success = self._activity_manager.select_activity(activity_id)
            if success:
                return ToolResult(
                    success=True,
                    message=f"Selected activity: {activity_id}",
                    data={"activity_id": activity_id}
                )
            else:
                return ToolResult(
                    success=False,
                    message=f"Could not find activity: {activity_id}",
                    error="Activity not found"
                )
        except Exception as e:
            return ToolResult(
                success=False,
                message=f"Failed to select activity",
                error=str(e)
            )

    def _handle_get_columns(self) -> ToolResult:
        """Handle get_visible_columns tool call."""
        try:
            columns = self._activity_manager.get_visible_columns()
            return ToolResult(
                success=True,
                message=f"Found {len(columns)} visible columns",
                data={"columns": columns, "count": len(columns)}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                message="Failed to get columns",
                error=str(e)
            )

    def _handle_update_activity(
        self,
        activity_id: str,
        field: str,
        value: str
    ) -> ToolResult:
        """Handle update_activity_gui tool call."""
        # FIX AI-001: Validate field name against visible columns
        try:
            columns = self._activity_manager.get_visible_columns()
            field_lower = field.lower()
            valid_field = None

            # Try exact match first, then partial match
            for col in columns:
                if col.lower() == field_lower:
                    valid_field = col
                    break

            if valid_field is None:
                for col in columns:
                    if field_lower in col.lower():
                        valid_field = col
                        logger.debug(f"Partial field match: '{field}' -> '{col}'")
                        break

            if valid_field is None:
                return ToolResult(
                    success=False,
                    message=f"Field '{field}' not found in visible columns",
                    error=f"Available fields: {columns[:10]}{'...' if len(columns) > 10 else ''}"
                )

            # Use the validated column name
            field = valid_field

        except Exception as e:
            logger.warning(f"Could not validate field name (continuing anyway): {e}")

        try:
            success = self._activity_manager.edit_activity_field(
                activity_id=activity_id,
                field_name=field,
                value=value
            )
            if success:
                return ToolResult(
                    success=True,
                    message=f"Updated {activity_id}.{field} = {value}",
                    data={
                        "activity_id": activity_id,
                        "field": field,
                        "value": value
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    message=f"Failed to update {activity_id}.{field}",
                    error="Edit operation failed"
                )
        except Exception as e:
            return ToolResult(
                success=False,
                message=f"Error updating activity",
                error=str(e)
            )

    def _handle_set_constraint(
        self,
        activity_id: str,
        constraint_type: str,
        constraint_date: str
    ) -> ToolResult:
        """Handle set_activity_constraint tool call."""
        try:
            # Convert string to ConstraintType enum
            ct = None
            for c in ConstraintType:
                if c.value == constraint_type:
                    ct = c
                    break

            if ct is None:
                return ToolResult(
                    success=False,
                    message=f"Invalid constraint type: {constraint_type}",
                    error=f"Valid types: {[c.value for c in ConstraintType]}"
                )

            success = self._activity_manager.set_constraint(
                activity_id=activity_id,
                constraint_type=ct,
                constraint_date=constraint_date
            )

            if success:
                return ToolResult(
                    success=True,
                    message=f"Set constraint on {activity_id}: {constraint_type} = {constraint_date}",
                    data={
                        "activity_id": activity_id,
                        "constraint_type": constraint_type,
                        "constraint_date": constraint_date
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    message=f"Failed to set constraint",
                    error="Constraint operation failed"
                )
        except Exception as e:
            return ToolResult(
                success=False,
                message="Error setting constraint",
                error=str(e)
            )

    def _handle_clear_constraint(self, activity_id: str) -> ToolResult:
        """Handle clear_activity_constraint tool call."""
        try:
            success = self._activity_manager.clear_constraint(activity_id)
            if success:
                return ToolResult(
                    success=True,
                    message=f"Cleared constraint on {activity_id}",
                    data={"activity_id": activity_id}
                )
            else:
                return ToolResult(
                    success=False,
                    message=f"Failed to clear constraint",
                    error="Clear operation failed"
                )
        except Exception as e:
            return ToolResult(
                success=False,
                message="Error clearing constraint",
                error=str(e)
            )

    def _handle_add_activity(self, wbs_path: str = None) -> ToolResult:
        """Handle add_activity_gui tool call."""
        try:
            success = self._activity_manager.add_activity(wbs_path=wbs_path)
            if success:
                return ToolResult(
                    success=True,
                    message="Added new activity",
                    data={"wbs_path": wbs_path}
                )
            else:
                return ToolResult(
                    success=False,
                    message="Failed to add activity",
                    error="Add operation failed"
                )
        except Exception as e:
            return ToolResult(
                success=False,
                message="Error adding activity",
                error=str(e)
            )

    def _handle_delete_activity(self, activity_id: str) -> ToolResult:
        """Handle delete_activity_gui tool call."""
        try:
            success = self._activity_manager.delete_activity(activity_id)
            if success:
                return ToolResult(
                    success=True,
                    message=f"Deleted activity: {activity_id}",
                    data={"activity_id": activity_id}
                )
            else:
                return ToolResult(
                    success=False,
                    message=f"Failed to delete activity",
                    error="Delete operation failed"
                )
        except Exception as e:
            return ToolResult(
                success=False,
                message="Error deleting activity",
                error=str(e)
            )

    def _handle_reschedule(self) -> ToolResult:
        """Handle reschedule_project_gui tool call."""
        # CRITICAL FIX SM-001: Must check safe_mode before scheduling
        # Scheduling can recalculate dates and corrupt data
        if self.safe_mode:
            logger.warning("[SAFE_MODE] Blocked reschedule_project_gui operation")
            return ToolResult(
                success=False,
                message="[SAFE_MODE] Project scheduling blocked. Disable safe_mode to reschedule.",
                error="Operation blocked by SAFE_MODE"
            )

        try:
            # F9 schedules the project
            self._window.set_focus()
            self._window.type_keys("{F9}")
            import time
            time.sleep(2.0)  # Wait for scheduling dialog

            # Handle scheduling dialog if it appears
            try:
                from pywinauto import Desktop
                schedule_dialog = Desktop(backend="uia").window(
                    title_re=".*Schedule.*|.*F9.*"
                )
                if schedule_dialog.exists():
                    # Click Schedule/OK button
                    ok_button = schedule_dialog.child_window(
                        title_re=".*Schedule.*|.*OK.*",
                        control_type="Button"
                    )
                    if ok_button.exists():
                        ok_button.click_input()
                        time.sleep(3.0)  # Wait for scheduling to complete
            except Exception:
                pass

            return ToolResult(
                success=True,
                message="Project scheduled (F9)",
                data={"action": "reschedule"}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                message="Error scheduling project",
                error=str(e)
            )

    def _handle_navigate_to_activity(self, activity_id: str) -> ToolResult:
        """Handle navigate_to_activity tool call."""
        return self._handle_select_activity(activity_id)

    def _handle_go_first(self) -> ToolResult:
        """Handle go_to_first_activity tool call."""
        try:
            success = self._activity_manager.go_to_first()
            if success:
                return ToolResult(
                    success=True,
                    message="Navigated to first activity"
                )
            else:
                return ToolResult(
                    success=False,
                    message="Failed to navigate",
                    error="Navigation failed"
                )
        except Exception as e:
            return ToolResult(
                success=False,
                message="Error navigating",
                error=str(e)
            )

    def _handle_go_last(self) -> ToolResult:
        """Handle go_to_last_activity tool call."""
        try:
            success = self._activity_manager.go_to_last()
            if success:
                return ToolResult(
                    success=True,
                    message="Navigated to last activity"
                )
            else:
                return ToolResult(
                    success=False,
                    message="Failed to navigate",
                    error="Navigation failed"
                )
        except Exception as e:
            return ToolResult(
                success=False,
                message="Error navigating",
                error=str(e)
            )

    # =========================================================================
    # Public Interface
    # =========================================================================

    def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool parameters

        Returns:
            ToolResult with success/failure and message
        """
        if tool_name not in self._tools:
            return ToolResult(
                success=False,
                message=f"Unknown tool: {tool_name}",
                error=f"Available tools: {list(self._tools.keys())}"
            )

        handler = self._tools[tool_name]
        logger.info(f"Executing tool: {tool_name} with args: {kwargs}")

        try:
            result = handler(**kwargs)
            logger.info(f"Tool result: {result.success} - {result.message}")
            return result
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return ToolResult(
                success=False,
                message=f"Tool execution failed: {tool_name}",
                error=str(e)
            )

    def get_tool_definitions(self, format: str = "openai") -> List[Dict[str, Any]]:
        """
        Get tool definitions for LLM function calling.

        Args:
            format: "openai" or "anthropic"

        Returns:
            List of tool definitions in the requested format
        """
        if format == "openai":
            return [td.to_openai_format() for td in self._tool_definitions]
        elif format == "anthropic":
            return [td.to_anthropic_format() for td in self._tool_definitions]
        else:
            raise ValueError(f"Unknown format: {format}")

    def get_system_prompt(self) -> str:
        """Get the system prompt for the LLM."""
        return self.SYSTEM_PROMPT

    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return list(self._tools.keys())

    def get_tool_info(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get information about a specific tool."""
        for td in self._tool_definitions:
            if td.name == tool_name:
                return td
        return None


# =============================================================================
# Agent Interface (for P6Agent integration)
# =============================================================================

class P6GUIAgent:
    """
    High-level agent interface for voice commands.

    This is called by the overlay when voice input is received.
    It processes natural language and calls the appropriate tools.
    """

    def __init__(self, main_window, safe_mode: bool = None):
        """Initialize the GUI agent."""
        self._tools = P6GUITools(main_window, safe_mode=safe_mode)
        logger.info("P6GUIAgent initialized")

    def chat(self, user_message: str) -> str:
        """
        Process a user message (from voice or text).

        This would typically call an LLM to interpret the message
        and decide which tool to call.

        Args:
            user_message: Natural language command

        Returns:
            Response message
        """
        logger.info(f"[VOICE INPUT] {user_message}")

        # In production, this would call the LLM
        # For now, provide a simple response
        return f"Received: {user_message}\nTools available: {self._tools.get_available_tools()}"

    def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a specific tool."""
        return self._tools.execute(tool_name, **kwargs)

    def get_tools(self) -> P6GUITools:
        """Get the underlying tools instance."""
        return self._tools
