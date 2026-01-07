#!/usr/bin/env python3
"""
AI Agent for P6 Planning Integration
Implements the ReAct loop: User Input → LLM → Tool Call → Execution → Response
"""

import json
from typing import Dict, List, Optional, Any

from src.ai.tools import P6Tools
from src.ai.prompts import SYSTEM_PROMPT
from src.ai.llm_client import LLMClient, is_ai_enabled
from src.utils import logger


class P6Agent:
    """
    AI Agent for natural language interaction with P6.
    
    Implements ReAct loop:
    1. User Input + Project Context → LLM
    2. LLM returns Tool Call (e.g., search_activities)
    3. Agent executes Tool in Python
    4. Agent sends Tool Result back to LLM
    5. LLM generates final Natural Language answer
    
    VERIFICATION POINT 2: Function Calling
    Handles LLM tool call response structure correctly.
    
    VERIFICATION POINT 3: Memory
    Appends tool output back to conversation history.
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
        self.conversation_history: List[Dict[str, Any]] = []
        self.context: Dict[str, Any] = {}
        
        # Initialize LLM client if AI is enabled
        self.llm_client = None
        self.ai_enabled = is_ai_enabled()
        
        if self.ai_enabled:
            try:
                self.llm_client = LLMClient()
                logger.info("P6Agent initialized with AI enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM client: {e}")
                logger.warning("Falling back to mock mode")
                self.ai_enabled = False
        else:
            logger.info("P6Agent initialized in mock mode (AI disabled)")
        
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
    
    def chat(self, user_input: str, max_iterations: int = 5) -> str:
        """
        Process user input and return AI response using ReAct loop.
        
        ReAct Loop:
        1. Send User Message + Project Context to LLM
        2. LLM returns Tool Call (e.g., search_activities)
        3. Agent executes Tool in Python
        4. Agent sends Tool Result back to LLM
        5. LLM generates final Natural Language answer
        
        VERIFICATION POINT 2: Function Calling
        Handles LLM tool call response structure correctly.
        
        VERIFICATION POINT 3: Memory
        Appends tool output back to conversation history.
        
        Args:
            user_input: User's natural language query
            max_iterations: Maximum ReAct loop iterations (prevents infinite loops)
            
        Returns:
            AI agent's response
        """
        try:
            logger.info(f"User input: {user_input}")
            
            # Add user message to conversation history
            user_message = {"role": "user", "content": user_input}
            self.conversation_history.append(user_message)
            
            if not self.ai_enabled or not self.llm_client:
                return self._fallback_mock_response(user_input)
            
            # Build messages with system prompt and context
            messages = self._build_messages()
            
            # Get tool schemas
            tool_schemas = self.tools.get_tool_schemas()
            
            # ReAct loop
            for iteration in range(max_iterations):
                logger.info(f"ReAct iteration {iteration + 1}/{max_iterations}")
                
                # Call LLM with tools
                text_response, tool_calls = self.llm_client.chat_with_tools(
                    messages=messages,
                    tools=tool_schemas,
                    tool_choice="auto"
                )
                
                # If no tool calls, LLM has finished reasoning
                if not tool_calls:
                    logger.info("LLM returned final response (no tool calls)")
                    
                    # Add assistant response to history
                    assistant_message = {"role": "assistant", "content": text_response or ""}
                    self.conversation_history.append(assistant_message)
                    
                    return text_response or "I apologize, but I couldn't generate a response."
                
                # LLM requested tool calls
                logger.info(f"LLM requested {len(tool_calls)} tool calls")
                
                # VERIFICATION POINT 3: Memory
                # Add assistant message with tool calls to history
                tool_call_message = self.llm_client.format_tool_call_message(tool_calls)
                messages.append(tool_call_message)
                
                # Execute each tool call
                for tool_call in tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['arguments']
                    tool_call_id = tool_call['id']
                    
                    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                    
                    # Execute tool
                    tool_result = self._execute_tool(tool_name, tool_args)
                    
                    logger.debug(f"Tool result: {tool_result[:200]}...")
                    
                    # VERIFICATION POINT 3: Memory
                    # Add tool result to messages for LLM
                    tool_result_message = self.llm_client.format_tool_result_message(
                        tool_call_id=tool_call_id,
                        tool_name=tool_name,
                        result=tool_result
                    )
                    messages.append(tool_result_message)
                
                # Continue loop - LLM will process tool results and either:
                # 1. Request more tools
                # 2. Return final response
            
            # Max iterations reached
            logger.warning(f"Max iterations ({max_iterations}) reached in ReAct loop")
            return "I apologize, but I couldn't complete the task within the allowed iterations. Please try breaking down your request into smaller parts."
        
        except Exception as e:
            logger.error(f"Error in chat: {e}", exc_info=True)
            return f"❌ Error: {str(e)}\n\nPlease try rephrasing your question or check the logs for details."
    
    def _build_messages(self) -> List[Dict[str, Any]]:
        """
        Build messages list for LLM with system prompt and context.
        
        Constraint: System prompt must be injected into every conversation start.
        
        Returns:
            List of messages for LLM
        """
        messages = []
        
        # Add system prompt
        system_content = SYSTEM_PROMPT
        
        # Add project context if available
        if self.context:
            system_content += "\n\n" + "=" * 60 + "\n"
            system_content += "CURRENT PROJECT CONTEXT\n"
            system_content += "=" * 60 + "\n\n"
            
            if 'markdown_summary' in self.context:
                system_content += self.context['markdown_summary']
            
            if 'project' in self.context:
                project = self.context['project']
                system_content += f"\n\n**Project ObjectId:** {project.get('ObjectId')}\n"
                system_content += f"**Project ID:** {project.get('Id')}\n"
                system_content += f"**Project Name:** {project.get('Name')}\n"
            
            if 'statistics' in self.context:
                stats = self.context['statistics']
                system_content += f"\n**Total Activities:** {stats.get('total_activities', 0)}\n"
                system_content += f"**Total Relationships:** {stats.get('total_relationships', 0)}\n"
        
        messages.append({
            "role": "system",
            "content": system_content
        })
        
        # Add conversation history
        messages.extend(self.conversation_history)
        
        return messages
    
    def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """
        Execute a tool and return the result as a JSON string.
        
        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool
            
        Returns:
            Tool result as JSON string
        """
        try:
            # Get tool method
            if not hasattr(self.tools, tool_name):
                error_result = {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}"
                }
                return json.dumps(error_result)
            
            tool_method = getattr(self.tools, tool_name)
            
            # Execute tool
            result = tool_method(**tool_args)
            
            return result
        
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            error_result = {
                "success": False,
                "error": str(e)
            }
            return json.dumps(error_result)
    
    def _fallback_mock_response(self, user_input: str) -> str:
        """
        Fallback mock response when AI is disabled.
        
        Args:
            user_input: User input
            
        Returns:
            Mock response
        """
        user_input_lower = user_input.lower()
        
        # Help
        if 'help' in user_input_lower:
            return self._get_help_text()
        
        # Status
        if 'status' in user_input_lower:
            return self._get_status_text()
        
        # List projects
        if any(keyword in user_input_lower for keyword in ['list projects', 'show projects', 'all projects']):
            result = self.tools.list_projects()
            data = json.loads(result)
            
            if data.get('success'):
                projects = data.get('projects', [])
                response = f"📂 **Available Projects** ({len(projects)} total)\n\n"
                
                for i, project in enumerate(projects, 1):
                    response += f"{i}. **{project.get('Name')}** (ID: {project.get('Id')})\n"
                    response += f"   - ObjectId: {project.get('ObjectId')}\n"
                    response += f"   - Status: {project.get('Status')}\n"
                    if project.get('PlanStartDate'):
                        response += f"   - Start Date: {project.get('PlanStartDate')}\n"
                    response += "\n"
                
                response += "💡 To analyze a specific project, use: `analyze project [ObjectId]`"
                return response
            else:
                return f"❌ Error: {data.get('error')}"
        
        # Default response
        return (
            "⚠️ **AI Mode Disabled**\n\n"
            "AI features require LLM_API_KEY to be configured in .env file.\n\n"
            "**Available Commands:**\n"
            "- `help` - Show available commands\n"
            "- `status` - Show system status\n"
            "- `list projects` - List all projects\n"
            "- `exit` - Exit chat mode\n\n"
            "To enable AI features:\n"
            "1. Set LLM_API_KEY in .env file\n"
            "2. Choose LLM_PROVIDER (anthropic, openai, or gemini)\n"
            "3. Restart the application\n\n"
            "Get your API key from:\n"
            "- Anthropic: https://console.anthropic.com/\n"
            "- OpenAI: https://platform.openai.com/api-keys\n"
            "- Google: https://makersuite.google.com/app/apikey"
        )
    
    def _get_help_text(self) -> str:
        """Get help text."""
        return """
📚 **P6 Planning AI Assistant - Help**

**Available Commands:**
- `help` - Show this help message
- `status` - Show system status (SAFE_MODE, AI status, project context)
- `exit`, `quit`, `bye` - Exit chat mode

**Example Queries:**
- "Show me all projects"
- "Find critical activities"
- "Show activity ACT-001"
- "Search for activities containing 'drilling'"
- "What are the predecessors of activity 123?"
- "Can we delay activity ACT-001 by 2 days?"
- "Analyze the schedule health"

**Tips:**
- Be specific with activity IDs or names
- Ask one question at a time for best results
- The AI will propose changes but NOT execute them (SAFE_MODE protection)
- Use natural language - the AI understands context

**Need Help?**
Check the logs at `logs/app.log` for detailed information.
"""
    
    def _get_status_text(self) -> str:
        """Get status text."""
        from src.config import settings
        
        status = "📊 **System Status**\n\n"
        status += f"**AI Enabled:** {'✅ Yes' if self.ai_enabled else '❌ No'}\n"
        
        if self.ai_enabled:
            status += f"**LLM Provider:** {settings.LLM_PROVIDER}\n"
            status += f"**LLM Model:** {settings.LLM_MODEL}\n"
        
        status += f"**SAFE_MODE:** {'🔒 ENABLED' if settings.SAFE_MODE else '⚠️ DISABLED'}\n"
        status += f"**Session Active:** {'✅ Yes' if self.session.is_connected() else '❌ No'}\n"
        
        if self.project_id:
            status += f"\n**Current Project:**\n"
            status += f"- ObjectId: {self.project_id}\n"
            
            if 'project' in self.context:
                project = self.context['project']
                status += f"- ID: {project.get('Id')}\n"
                status += f"- Name: {project.get('Name')}\n"
                status += f"- Status: {project.get('Status')}\n"
            
            if 'statistics' in self.context:
                stats = self.context['statistics']
                status += f"\n**Statistics:**\n"
                status += f"- Total Activities: {stats.get('total_activities', 0)}\n"
                status += f"- Total Relationships: {stats.get('total_relationships', 0)}\n"
        
        return status


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_agent(session, project_id: Optional[int] = None) -> P6Agent:
    """
    Create P6 Agent with default settings.
    
    Args:
        session: Active P6Session instance
        project_id: Default project ObjectId (optional)
        
    Returns:
        P6Agent instance
    """
    return P6Agent(session, project_id=project_id)
