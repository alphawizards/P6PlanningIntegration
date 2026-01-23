#!/usr/bin/env python3
"""
P6 Automation Package - Enhanced for Voice Control.

Provides GUI automation tools (Layer 3: "The Hands").

Modules:
- activities.py: P6ActivityManager for activity operations
- p6_launcher.py: P6Launcher for startup/login automation
"""

from .activities import P6ActivityManager, ConstraintType
from .p6_launcher import P6Launcher, P6LaunchError, launch_p6

__all__ = [
    'P6ActivityManager',
    'ConstraintType',
    'P6Launcher',
    'P6LaunchError',
    'launch_p6',
]
