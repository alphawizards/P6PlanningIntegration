#!/usr/bin/env python3
"""
AI Agent for P6 Planning Integration
Implements the agent loop: User Input → LLM → Tool Call → Execution → Response
"""

import json
import re
from typing import Dict, List, Optional, Any, Tuple

from src.ai.tools import P6Tools
from src.ai.prompts import (
    SYSTEM_PROMPT,
    format_activity_summary,
    format_change_proposal,
    get_safe_mode_status_message
)
from src.utils import logger


class P6Agent:
    """
    AI Agent for natural language interaction with P6.
    
    Implements agent loop:
    1. User Input
    2. LLM Processing (with system prompt and context)
    3. Tool Selection and Execution
    4. Result Processing
    5. Response Generation
    """
    
    def __init__(self, session, project_id: Optional[int] = None):
        """
        Initialize P6 Agent.
        
        Args:
            session: Active P6Session instance
            project_id: Default project ObjectId (optional)
        """
        self.session = session
        self.project_id = project_id
        self.tools = P6Tools(session)
        self.conversation_history: List[Dict[str, str]] = []
        self.context: Dict[str, Any] = {}
        
        logger.info("P6Agent initialized")
        
        # Load initial context if project_id provided
        if project_id:
            self._load_project_context(project_id)
    
    def _load_project_context(self, project_id: int):
        """
        Load initial project context.
        
        VERIFICATION POINT 3: Context Injection
        Loads project summary into agent context.
        
        Args:
            project_id: Project ObjectId
        """
        try:
            logger.info(f"Loading project context for project_id={project_id}")
            
            context_json = self.tools.get_project_context(project_id)
            context_data = json.loads(context_json)
            
            if context_data.get('success'):
                self.context['project'] = context_data.get('project', {})
                self.context['statistics'] = context_data.get('statistics', {})
                self.context['markdown_summary'] = context_data.get('markdown_summary', '')
                
                logger.info("Project context loaded successfully")
            else:
                logger.warning(f"Failed to load project context: {context_data.get('error')}")
        
        except Exception as e:
            logger.error(f"Error loading project context: {e}")
    
    def chat(self, user_input: str) -> str:
        """
        Process user input and return AI response.
        
        Main agent loop:
        1. Parse user input
        2. Determine intent and required tools
        3. Execute tools
        4. Generate response
        
        Args:
            user_input: User's natural language query
            
        Returns:
            AI agent's response
        """
        try:
            logger.info(f"User input: {user_input}")
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": user_input
            })
            
            # Parse intent and extract parameters
            intent, params = self._parse_intent(user_input)
            
            logger.info(f"Detected intent: {intent}")
            logger.debug(f"Extracted params: {params}")
            
            # Execute appropriate tool(s)
            tool_results = self._execute_tools(intent, params)
            
            # Generate response
            response = self._generate_response(intent, params, tool_results)
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": response
            })
            
            return response
        
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return f"❌ Error: {str(e)}\n\nPlease try rephrasing your question or check the logs for details."
    
    def _parse_intent(self, user_input: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse user intent from natural language input.
        
        This is a MOCK implementation. In production, this would use
        an LLM to understand intent and extract parameters.
        
        Args:
            user_input: User's input
            
        Returns:
            Tuple of (intent, parameters)
        """
        user_input_lower = user_input.lower()
        
        # List projects
        if any(keyword in user_input_lower for keyword in ['list projects', 'show projects', 'all projects', 'available projects']):
            return ('list_projects', {})
        
        # Get project context
        if any(keyword in user_input_lower for keyword in ['project context', 'project summary', 'project overview']):
            return ('get_project_context', {'project_id': self.project_id})
        
        # Search activities
        if any(keyword in user_input_lower for keyword in ['find', 'search', 'show activities', 'list activities']):
            params = {'project_id': self.project_id}
            
            # Extract status
            if 'in progress' in user_input_lower:
                params['status'] = 'In Progress'
            elif 'not started' in user_input_lower:
                params['status'] = 'Not Started'
            elif 'completed' in user_input_lower:
                params['status'] = 'Completed'
            
            # Extract search query (simple pattern matching)
            # Look for quoted strings or keywords after "named", "called", "containing"
            query_match = re.search(r'(?:named|called|containing)\s+["\']?([^"\']+)["\']?', user_input_lower)
            if query_match:
                params['query'] = query_match.group(1).strip()
            
            return ('search_activities', params)
        
        # Critical activities
        if any(keyword in user_input_lower for keyword in ['critical', 'critical path', 'critical activities']):
            return ('get_critical_activities', {'project_id': self.project_id})
        
        # Activity details
        activity_id_match = re.search(r'activity\s+([A-Z0-9-]+)', user_input, re.IGNORECASE)
        if activity_id_match or 'details' in user_input_lower or 'information about' in user_input_lower:
            activity_id = activity_id_match.group(1) if activity_id_match else None
            if activity_id:
                return ('get_activity_details', {
                    'activity_id': activity_id,
                    'project_id': self.project_id
                })
        
        # Propose change
        if any(keyword in user_input_lower for keyword in ['change', 'update', 'modify', 'adjust', 'delay', 'extend']):
            # This is a simplified parser - in production, LLM would extract these
            return ('propose_change', {
                'user_input': user_input,
                'project_id': self.project_id
            })
        
        # Analyze impact
        if any(keyword in user_input_lower for keyword in ['impact', 'effect', 'consequence', 'what if']):
            return ('analyze_impact', {
                'user_input': user_input,
                'project_id': self.project_id
            })
        
        # Help
        if any(keyword in user_input_lower for keyword in ['help', 'what can you do', 'commands', 'capabilities']):
            return ('help', {})
        
        # Status
        if any(keyword in user_input_lower for keyword in ['status', 'safe mode', 'safe_mode', 'write mode']):
            return ('status', {})
        
        # Default: general query
        return ('general_query', {'query': user_input, 'project_id': self.project_id})
    
    def _execute_tools(self, intent: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute appropriate tools based on intent.
        
        Args:
            intent: Detected intent
            params: Extracted parameters
            
        Returns:
            Tool execution results
        """
        results = {}
        
        try:
            if intent == 'list_projects':
                results['projects'] = self.tools.list_projects()
            
            elif intent == 'get_project_context':
                project_id = params.get('project_id')
                if project_id:
                    results['context'] = self.tools.get_project_context(project_id)
                else:
                    results['error'] = "No project ID specified"
            
            elif intent == 'search_activities':
                project_id = params.get('project_id')
                if project_id:
                    results['activities'] = self.tools.search_activities(
                        project_id=project_id,
                        query=params.get('query'),
                        status=params.get('status')
                    )
                else:
                    results['error'] = "No project ID specified"
            
            elif intent == 'get_critical_activities':
                project_id = params.get('project_id')
                if project_id:
                    results['critical_activities'] = self.tools.get_critical_activities(project_id)
                else:
                    results['error'] = "No project ID specified"
            
            elif intent == 'get_activity_details':
                activity_id = params.get('activity_id')
                if activity_id:
                    results['activity_details'] = self.tools.get_activity_details(
                        activity_id=activity_id,
                        project_id=params.get('project_id')
                    )
                else:
                    results['error'] = "No activity ID specified"
            
            elif intent == 'propose_change':
                # This would require more sophisticated parsing in production
                results['proposal'] = "Change proposal requires more specific parameters (activity ID, field, value)"
            
            elif intent == 'analyze_impact':
                # This would require more sophisticated parsing in production
                results['analysis'] = "Impact analysis requires specific activity and proposed changes"
            
            elif intent == 'help':
                results['help'] = self._get_help_text()
            
            elif intent == 'status':
                results['status'] = self._get_status_text()
            
            else:
                # General query - provide context
                if self.project_id and not self.context:
                    self._load_project_context(self.project_id)
                results['context'] = self.context
        
        except Exception as e:
            logger.error(f"Error executing tools: {e}")
            results['error'] = str(e)
        
        return results
    
    def _generate_response(self, intent: str, params: Dict[str, Any], tool_results: Dict[str, Any]) -> str:
        """
        Generate natural language response from tool results.
        
        This is a MOCK implementation. In production, this would use
        an LLM to generate natural, contextual responses.
        
        Args:
            intent: Detected intent
            params: Extracted parameters
            tool_results: Results from tool execution
            
        Returns:
            Natural language response
        """
        # Check for errors first
        if 'error' in tool_results:
            return f"❌ Error: {tool_results['error']}\n\nPlease try rephrasing your question or provide more details."
        
        # Intent-specific responses
        if intent == 'list_projects':
            return self._format_projects_response(tool_results.get('projects'))
        
        elif intent == 'get_project_context':
            return self._format_context_response(tool_results.get('context'))
        
        elif intent == 'search_activities':
            return self._format_activities_response(tool_results.get('activities'), params)
        
        elif intent == 'get_critical_activities':
            return self._format_critical_activities_response(tool_results.get('critical_activities'))
        
        elif intent == 'get_activity_details':
            return self._format_activity_details_response(tool_results.get('activity_details'))
        
        elif intent == 'help':
            return tool_results.get('help', '')
        
        elif intent == 'status':
            return tool_results.get('status', '')
        
        else:
            # General response
            return self._format_general_response(params.get('query', ''), tool_results)
    
    def _format_projects_response(self, projects_json: str) -> str:
        """Format projects list response."""
        try:
            data = json.loads(projects_json)
            
            if not data.get('success'):
                return f"❌ {data.get('message', 'No projects found')}"
            
            projects = data.get('projects', [])
            
            if not projects:
                return "📂 No projects found in the database."
            
            response = f"📂 **Available Projects** ({len(projects)} total)\n\n"
            
            for i, project in enumerate(projects, 1):
                response += f"{i}. **{project.get('Name')}** (ID: {project.get('Id')})\n"
                response += f"   - ObjectId: {project.get('ObjectId')}\n"
                response += f"   - Status: {project.get('Status')}\n"
                if project.get('PlanStartDate'):
                    response += f"   - Start Date: {project.get('PlanStartDate')}\n"
                response += "\n"
            
            response += "\n💡 To analyze a specific project, use: `analyze project [ObjectId]`"
            
            return response
        
        except Exception as e:
            logger.error(f"Error formatting projects response: {e}")
            return f"❌ Error formatting response: {e}"
    
    def _format_context_response(self, context_json: str) -> str:
        """Format project context response."""
        try:
            data = json.loads(context_json)
            
            if not data.get('success'):
                return f"❌ {data.get('error', 'Failed to load project context')}"
            
            project = data.get('project', {})
            stats = data.get('statistics', {})
            markdown = data.get('markdown_summary', '')
            
            response = f"📊 **Project Context**\n\n"
            response += f"**Project:** {project.get('Name')} (ID: {project.get('Id')})\n"
            response += f"**Status:** {project.get('Status')}\n"
            response += f"**ObjectId:** {project.get('ObjectId')}\n\n"
            
            response += f"**Statistics:**\n"
            response += f"- Total Activities: {stats.get('total_activities', 0)}\n"
            response += f"- Total Relationships: {stats.get('total_relationships', 0)}\n"
            
            activities_by_status = stats.get('activities_by_status', {})
            if activities_by_status:
                response += f"\n**Activities by Status:**\n"
                for status, count in activities_by_status.items():
                    response += f"- {status}: {count}\n"
            
            if markdown:
                response += f"\n---\n\n{markdown}"
            
            return response
        
        except Exception as e:
            logger.error(f"Error formatting context response: {e}")
            return f"❌ Error formatting response: {e}"
    
    def _format_activities_response(self, activities_json: str, params: Dict[str, Any]) -> str:
        """Format activities search response."""
        try:
            data = json.loads(activities_json)
            
            if not data.get('success'):
                return f"❌ {data.get('message', 'No activities found')}"
            
            activities = data.get('activities', [])
            count = data.get('count', 0)
            
            if count == 0:
                return "📋 No activities found matching your criteria."
            
            # Build filter description
            filters = []
            if params.get('query'):
                filters.append(f"containing '{params['query']}'")
            if params.get('status'):
                filters.append(f"with status '{params['status']}'")
            
            filter_desc = " ".join(filters) if filters else "all activities"
            
            response = f"📋 **Activities** ({count} found - {filter_desc})\n\n"
            
            # Limit display to first 10
            display_activities = activities[:10]
            
            for i, activity in enumerate(display_activities, 1):
                response += f"{i}. **{activity.get('Name')}** (ID: {activity.get('Id')})\n"
                response += f"   - ObjectId: {activity.get('ObjectId')}\n"
                response += f"   - Status: {activity.get('Status')}\n"
                response += f"   - Duration: {activity.get('PlannedDuration')} hours\n"
                if activity.get('StartDate'):
                    response += f"   - Start: {activity.get('StartDate')}\n"
                if activity.get('FinishDate'):
                    response += f"   - Finish: {activity.get('FinishDate')}\n"
                response += "\n"
            
            if count > 10:
                response += f"\n... and {count - 10} more activities.\n"
            
            response += "\n💡 For details on a specific activity, use: `show activity [ID]`"
            
            return response
        
        except Exception as e:
            logger.error(f"Error formatting activities response: {e}")
            return f"❌ Error formatting response: {e}"
    
    def _format_critical_activities_response(self, critical_json: str) -> str:
        """Format critical activities response."""
        try:
            data = json.loads(critical_json)
            
            if not data.get('success'):
                return f"❌ {data.get('message', 'Failed to get critical activities')}"
            
            activities = data.get('activities', [])
            count = data.get('count', 0)
            note = data.get('note', '')
            
            response = f"🚨 **Critical Path Activities**\n\n"
            
            if note:
                response += f"ℹ️ {note}\n\n"
            
            if count == 0:
                response += "No activities found.\n"
                return response
            
            response += f"Found {count} activities:\n\n"
            
            for i, activity in enumerate(activities[:10], 1):
                response += f"{i}. **{activity.get('Name')}** (ID: {activity.get('Id')})\n"
                response += f"   - Status: {activity.get('Status')}\n"
                response += f"   - Duration: {activity.get('PlannedDuration')} hours\n"
                response += "\n"
            
            if count > 10:
                response += f"\n... and {count - 10} more activities.\n"
            
            return response
        
        except Exception as e:
            logger.error(f"Error formatting critical activities response: {e}")
            return f"❌ Error formatting response: {e}"
    
    def _format_activity_details_response(self, details_json: str) -> str:
        """Format activity details response."""
        try:
            data = json.loads(details_json)
            
            if not data.get('success'):
                return f"❌ {data.get('error', 'Activity not found')}"
            
            activity = data.get('activity', {})
            
            response = f"📋 **Activity Details**\n\n"
            response += f"**Name:** {activity.get('Name')}\n"
            response += f"**ID:** {activity.get('Id')}\n"
            response += f"**ObjectId:** {activity.get('ObjectId')}\n"
            response += f"**Status:** {activity.get('Status')}\n"
            response += f"**Planned Duration:** {activity.get('PlannedDuration')} hours\n"
            
            if activity.get('StartDate'):
                response += f"**Start Date:** {activity.get('StartDate')}\n"
            if activity.get('FinishDate'):
                response += f"**Finish Date:** {activity.get('FinishDate')}\n"
            
            return response
        
        except Exception as e:
            logger.error(f"Error formatting activity details response: {e}")
            return f"❌ Error formatting response: {e}"
    
    def _format_general_response(self, query: str, tool_results: Dict[str, Any]) -> str:
        """Format general query response."""
        response = f"I understand you're asking about: \"{query}\"\n\n"
        
        if self.context:
            project = self.context.get('project', {})
            response += f"Current project context: {project.get('Name', 'Unknown')}\n\n"
        
        response += "I can help you with:\n"
        response += "- Listing projects\n"
        response += "- Analyzing project schedules\n"
        response += "- Finding activities\n"
        response += "- Identifying critical path\n"
        response += "- Proposing schedule changes\n\n"
        response += "💡 Try asking: 'Show me all projects' or 'Find critical activities'"
        
        return response
    
    def _get_help_text(self) -> str:
        """Get help text."""
        return """
🤖 **P6 AI Assistant - Help**

I'm your Lead Mining Planner AI assistant. I can help you analyze and optimize P6 schedules.

**Available Commands:**

📂 **Project Management**
- `list projects` - Show all available projects
- `analyze project [ID]` - Get comprehensive project analysis
- `project context` - Show current project summary

📋 **Activity Queries**
- `show activities` - List all activities
- `find activities [query]` - Search activities by name
- `show activity [ID]` - Get detailed activity information
- `critical activities` - Show critical path activities
- `activities in progress` - Filter by status

🔍 **Analysis**
- `what if [scenario]` - Analyze impact of changes
- `analyze impact` - Assess schedule impacts

⚙️ **System**
- `status` - Show SAFE_MODE and system status
- `help` - Show this help message

**Example Queries:**
- "Show me all projects"
- "Find activities containing 'drilling'"
- "What are the critical activities?"
- "Show activity ACT-001"
- "Can we delay activity ACT-123 by 2 days?"

**SAFE_MODE:**
Currently: {'ENABLED' if self.session.safe_mode else 'DISABLED'}

{get_safe_mode_status_message(self.session.safe_mode)}

**Tips:**
- Use natural language - I'll understand your intent
- Be specific when asking about activities (include IDs)
- I'll always explain my reasoning and show impacts
- Changes require your explicit confirmation

Need more help? Just ask!
"""
    
    def _get_status_text(self) -> str:
        """Get system status text."""
        safe_mode = self.session.safe_mode
        
        status = f"""
🔧 **System Status**

**SAFE_MODE:** {'🔒 ENABLED' if safe_mode else '🔓 DISABLED'}
**Session:** {'✓ Active' if self.session.is_active() else '✗ Inactive'}
**Project Context:** {'✓ Loaded' if self.context else '✗ Not loaded'}

{get_safe_mode_status_message(safe_mode)}

**Current Project:**
"""
        
        if self.context and self.context.get('project'):
            project = self.context['project']
            status += f"- Name: {project.get('Name')}\n"
            status += f"- ID: {project.get('Id')}\n"
            status += f"- ObjectId: {project.get('ObjectId')}\n"
        else:
            status += "- No project loaded\n"
        
        status += "\n💡 Use `help` to see available commands"
        
        return status


def call_llm(prompt: str, system_prompt: str = SYSTEM_PROMPT) -> str:
    """
    Call LLM API (MOCK implementation for MVP).
    
    In production, this would call OpenAI, Claude, or Gemini API.
    For now, returns a placeholder response.
    
    Args:
        prompt: User prompt
        system_prompt: System prompt with instructions
        
    Returns:
        LLM response
    """
    logger.info("MOCK LLM call (not implemented)")
    logger.debug(f"Prompt: {prompt}")
    
    # This is a placeholder for future LLM integration
    return "MOCK_LLM_RESPONSE: This is a placeholder. Integrate OpenAI/Claude/Gemini API here."
