#!/usr/bin/env python3
"""
P6 AI Package - GUI Tools for LLM Agents.

Provides tool definitions and wrappers (Layer 2: "The Brain").
"""

from .gui_tools import P6GUITools, P6GUIAgent, ToolResult, ToolDefinition

__all__ = ['P6GUITools', 'P6GUIAgent', 'ToolResult', 'ToolDefinition']
