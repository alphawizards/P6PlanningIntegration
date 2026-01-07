#!/usr/bin/env python3
"""
LLM Client for P6 Planning Integration
Handles communication with LLMs (Claude, OpenAI, Gemini) using litellm.
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple

from src.config import settings
from src.utils import logger


class LLMClient:
    """
    Client for interacting with LLMs via litellm.
    
    Supports:
    - Anthropic Claude
    - OpenAI GPT
    - Google Gemini
    
    VERIFICATION POINT 2: Function Calling
    Handles LLM tool call response structure correctly.
    """
    
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize LLM client.
        
        Args:
            provider: LLM provider (anthropic, openai, gemini). Defaults to settings.LLM_PROVIDER
            model: Model name. Defaults to settings.LLM_MODEL
            api_key: API key. Defaults to settings.LLM_API_KEY
        """
        self.provider = provider or settings.LLM_PROVIDER
        self.model = model or settings.LLM_MODEL
        self.api_key = api_key or settings.LLM_API_KEY
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        
        if not self.api_key:
            raise ValueError(
                "LLM_API_KEY not configured. Please set LLM_API_KEY in .env file.\n"
                "Get your API key from:\n"
                "- Anthropic: https://console.anthropic.com/\n"
                "- OpenAI: https://platform.openai.com/api-keys\n"
                "- Google: https://makersuite.google.com/app/apikey"
            )
        
        # Set API key in environment for litellm
        self._set_api_key_env()
        
        logger.info(f"LLMClient initialized: provider={self.provider}, model={self.model}")
    
    def _set_api_key_env(self):
        """Set API key in environment variable for litellm."""
        if self.provider == 'anthropic':
            os.environ['ANTHROPIC_API_KEY'] = self.api_key
        elif self.provider == 'openai':
            os.environ['OPENAI_API_KEY'] = self.api_key
        elif self.provider == 'gemini':
            os.environ['GEMINI_API_KEY'] = self.api_key
    
    def _format_model_name(self) -> str:
        """
        Format model name for litellm.
        
        litellm requires provider prefix for some models:
        - anthropic: claude-3-5-sonnet-20241022
        - openai: gpt-4-turbo-preview
        - gemini: gemini/gemini-1.5-pro
        
        Returns:
            Formatted model name
        """
        if self.provider == 'gemini' and not self.model.startswith('gemini/'):
            return f'gemini/{self.model}'
        return self.model
    
    def _convert_tools_to_litellm_format(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert our tool schema format to litellm/OpenAI function calling format.
        
        Our format:
        {
            "name": "tool_name",
            "description": "...",
            "parameters": {
                "type": "object",
                "properties": {...},
                "required": [...]
            }
        }
        
        litellm format (OpenAI-compatible):
        {
            "type": "function",
            "function": {
                "name": "tool_name",
                "description": "...",
                "parameters": {...}
            }
        }
        
        Args:
            tools: List of tool schemas
            
        Returns:
            List of litellm-formatted tool schemas
        """
        litellm_tools = []
        
        for tool in tools:
            litellm_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
            }
            litellm_tools.append(litellm_tool)
        
        return litellm_tools
    
    def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        tool_choice: str = "auto"
    ) -> Tuple[Optional[str], Optional[List[Dict[str, Any]]]]:
        """
        Send chat request with tool/function calling support.
        
        VERIFICATION POINT 2: Function Calling
        Correctly handles LLM tool call response structure.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: List of tool schemas
            tool_choice: Tool choice strategy ("auto", "required", "none")
            
        Returns:
            Tuple of (text_response, tool_calls)
            - text_response: Text response from LLM (if any)
            - tool_calls: List of tool call dicts (if any)
        """
        try:
            import litellm
            
            # Convert tools to litellm format
            litellm_tools = self._convert_tools_to_litellm_format(tools)
            
            # Format model name
            model = self._format_model_name()
            
            logger.info(f"Calling LLM: {model}")
            logger.debug(f"Messages: {messages}")
            logger.debug(f"Tools: {len(tools)} tools available")
            
            # Call litellm
            response = litellm.completion(
                model=model,
                messages=messages,
                tools=litellm_tools,
                tool_choice=tool_choice,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            logger.debug(f"LLM response: {response}")
            
            # Extract response
            message = response.choices[0].message
            
            # Check for tool calls
            tool_calls = None
            if hasattr(message, 'tool_calls') and message.tool_calls:
                tool_calls = []
                for tool_call in message.tool_calls:
                    tool_calls.append({
                        'id': tool_call.id,
                        'name': tool_call.function.name,
                        'arguments': json.loads(tool_call.function.arguments)
                    })
                logger.info(f"LLM requested {len(tool_calls)} tool calls")
            
            # Get text content
            text_response = message.content if hasattr(message, 'content') else None
            
            return text_response, tool_calls
        
        except ImportError:
            logger.error("litellm not installed. Run: pip install litellm")
            raise RuntimeError(
                "litellm library not installed. Please run: pip install litellm"
            )
        
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            raise
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Send simple chat request without tools.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt (prepended to messages)
            
        Returns:
            Text response from LLM
        """
        try:
            import litellm
            
            # Add system prompt if provided
            if system_prompt:
                messages = [
                    {"role": "system", "content": system_prompt}
                ] + messages
            
            # Format model name
            model = self._format_model_name()
            
            logger.info(f"Calling LLM: {model}")
            logger.debug(f"Messages: {messages}")
            
            # Call litellm
            response = litellm.completion(
                model=model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            logger.debug(f"LLM response: {response}")
            
            # Extract response
            message = response.choices[0].message
            text_response = message.content if hasattr(message, 'content') else ""
            
            return text_response
        
        except ImportError:
            logger.error("litellm not installed. Run: pip install litellm")
            raise RuntimeError(
                "litellm library not installed. Please run: pip install litellm"
            )
        
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            raise
    
    def format_tool_result_message(self, tool_call_id: str, tool_name: str, result: str) -> Dict[str, Any]:
        """
        Format tool result as a message for the LLM.
        
        VERIFICATION POINT 3: Memory
        Formats tool output to append to conversation history.
        
        Args:
            tool_call_id: ID of the tool call
            tool_name: Name of the tool that was called
            result: Result from tool execution (JSON string)
            
        Returns:
            Message dict for conversation history
        """
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": result
        }
    
    def format_tool_call_message(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Format tool calls as a message for the LLM.
        
        This is needed to maintain conversation history when the LLM
        requests tool calls.
        
        Args:
            tool_calls: List of tool call dicts
            
        Returns:
            Message dict for conversation history
        """
        # Convert our tool call format back to OpenAI format
        openai_tool_calls = []
        for tool_call in tool_calls:
            openai_tool_calls.append({
                "id": tool_call['id'],
                "type": "function",
                "function": {
                    "name": tool_call['name'],
                    "arguments": json.dumps(tool_call['arguments'])
                }
            })
        
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": openai_tool_calls
        }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_llm_client(provider: Optional[str] = None, model: Optional[str] = None) -> LLMClient:
    """
    Create LLM client with default settings.
    
    Args:
        provider: LLM provider (optional, defaults to settings)
        model: Model name (optional, defaults to settings)
        
    Returns:
        LLMClient instance
    """
    return LLMClient(provider=provider, model=model)


def is_ai_enabled() -> bool:
    """
    Check if AI features are enabled.
    
    Returns:
        True if LLM_API_KEY is configured
    """
    return settings.AI_ENABLED
