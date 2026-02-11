#!/usr/bin/env python3
"""
P6 Voice-Driven GUI Agent - Main Entry Point.

Per agents.md:
"User Voice -> Text -> P6Agent (Layer 2) -> Decide Tool -> Call Layer 3 Script"

This script:
1. Optionally launches P6 Professional and logs in (--launch flag)
2. Finds and connects to P6 Professional window
3. Loads Whisper model for voice transcription
4. Creates the overlay window
5. Wires everything together

Usage:
    python main.py [--safe-mode] [--model tiny|base|small]
    python main.py --launch --password admin    # Auto-launch and login to P6
"""

import sys
import argparse
import threading
import time
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from pywinauto import Desktop
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False
    print("ERROR: pywinauto not installed. Run: pip install pywinauto")

# Local imports
from src.gui.overlay import P6VoiceOverlay, AgentStatus
from src.gui.whisper_handler import WhisperTranscriber, WhisperModel, AsyncWhisperTranscriber
from src.ai.gui_tools import P6GUIAgent, P6GUITools
from src.automation.p6_launcher import P6Launcher, P6LaunchError

# Logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/voice_agent.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)


def find_p6_window():
    """
    Find the P6 Professional window.

    Returns:
        pywinauto window wrapper or None if not found
    """
    if not PYWINAUTO_AVAILABLE:
        return None

    try:
        # Try different title patterns
        patterns = [
            ".*Primavera P6.*",
            ".*P6 Professional.*",
            "Oracle Primavera P6.*"
        ]

        for pattern in patterns:
            try:
                window = Desktop(backend="uia").window(title_re=pattern)
                if window.exists():
                    logger.info(f"Found P6 window: {window.window_text()}")
                    return window
            except Exception:
                continue

        logger.warning("P6 window not found")
        return None

    except Exception as e:
        logger.error(f"Error finding P6 window: {e}")
        return None


def main():
    """Main entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="P6 Voice-Driven GUI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                              # Start with default settings
  python main.py --safe-mode                  # Start in safe mode (no edits)
  python main.py --model small                # Use larger Whisper model
  python main.py --launch                     # Auto-launch P6 and login
  python main.py --launch --password mypass   # Launch with custom password

Controls:
  - Hold SPACEBAR or click button to record voice
  - Release to transcribe and execute
  - Press ESC to close
        """
    )
    parser.add_argument(
        '--safe-mode',
        action='store_true',
        default=True,
        help='Enable safe mode (default: True, prevents edits)'
    )
    parser.add_argument(
        '--unsafe',
        action='store_true',
        help='Disable safe mode (allows edits)'
    )
    parser.add_argument(
        '--model',
        choices=['tiny', 'base', 'small', 'medium'],
        default='base',
        help='Whisper model size (default: base)'
    )
    parser.add_argument(
        '--no-whisper',
        action='store_true',
        help='Skip Whisper loading (for testing UI only)'
    )
    # P6 Launcher arguments
    parser.add_argument(
        '--launch',
        action='store_true',
        help='Auto-launch P6 Professional and login before starting agent'
    )
    parser.add_argument(
        '--password',
        default='admin',
        help='P6 login password (default: admin)'
    )
    parser.add_argument(
        '--username',
        default='ADMIN',
        help='P6 login username (default: ADMIN)'
    )
    parser.add_argument(
        '--taskbar',
        action='store_true',
        help='Launch P6 by clicking taskbar icon instead of executable'
    )

    args = parser.parse_args()

    # Determine safe mode
    safe_mode = not args.unsafe

    print("=" * 60)
    print("P6 Voice-Driven GUI Agent")
    print("=" * 60)
    print()
    print(f"Safe Mode:    {'ENABLED' if safe_mode else 'DISABLED (edits allowed)'}")
    print(f"Whisper Model: {args.model}")
    print()

    # Create logs directory
    Path("logs").mkdir(exist_ok=True)

    # Handle P6 Launch (if --launch flag provided)
    p6_window = None

    if args.launch:
        print()
        print("=" * 60)
        print("Launching P6 Professional...")
        print("=" * 60)
        print(f"Username: {args.username}")
        print(f"Password: {'*' * len(args.password)}")
        print()

        try:
            launcher = P6Launcher(username=args.username)
            p6_window = launcher.launch_and_login(
                password=args.password,
                use_taskbar=args.taskbar
            )

            if p6_window:
                print()
                print("P6 launched and logged in successfully!")
                print(f"Window: {p6_window.window_text()}")
            else:
                print()
                print("WARNING: P6 launch completed but window not found")

        except P6LaunchError as e:
            print()
            print(f"ERROR launching P6: {e}")
            print("Continuing without P6 connection...")
        except Exception as e:
            print()
            print(f"UNEXPECTED ERROR: {e}")
            print("Continuing without P6 connection...")

    # Find P6 window (if not already found via launcher)
    if not p6_window:
        print()
        print("Looking for P6 Professional window...")
        p6_window = find_p6_window()

    if not p6_window:
        print()
        print("WARNING: P6 Professional window not found!")
        print("The agent will start, but GUI commands won't work.")
        if not args.launch:
            print("TIP: Use --launch flag to auto-launch P6")
        print("Or open P6 Professional manually and restart the agent.")
        print()

    # Create agent
    if p6_window:
        print("Creating P6 GUI Agent...")
        agent = P6GUIAgent(p6_window, safe_mode=safe_mode)
    else:
        agent = None

    # Create command handler
    def handle_command(text: str) -> str:
        """Handle voice command from overlay."""
        logger.info(f"[COMMAND] {text}")

        if agent is None:
            return "P6 not connected. Please open P6 Professional."

        # For now, return available tools
        # In production, this would call an LLM to interpret the command
        tools = agent.get_tools()

        # Simple keyword matching for demo
        text_lower = text.lower()

        if "select" in text_lower and "activity" in text_lower:
            # Extract activity ID (simple pattern)
            import re
            match = re.search(r'([A-Z]\d+)', text, re.IGNORECASE)
            if match:
                activity_id = match.group(1).upper()
                result = tools.execute("select_activity", activity_id=activity_id)
                return result.message
            return "Please specify an activity ID (e.g., 'select activity A1010')"

        elif "columns" in text_lower or "visible" in text_lower:
            result = tools.execute("get_visible_columns")
            if result.success:
                cols = result.data.get("columns", [])[:5]
                return f"Found {result.data.get('count')} columns: {', '.join(cols)}..."
            return result.message

        elif "first" in text_lower:
            result = tools.execute("go_to_first_activity")
            return result.message

        elif "last" in text_lower:
            result = tools.execute("go_to_last_activity")
            return result.message

        elif "schedule" in text_lower or "f9" in text_lower:
            if safe_mode:
                return "[SAFE MODE] Would schedule project (F9)"
            result = tools.execute("reschedule_project_gui")
            return result.message

        elif "help" in text_lower:
            tool_list = tools.get_available_tools()
            return f"Available commands: {', '.join(tool_list)}"

        else:
            return f"Command not recognized. Say 'help' for available commands."

    # Create overlay
    print("Creating overlay window...")
    overlay = P6VoiceOverlay(
        on_command=handle_command,
        position="bottom-right"
    )
    overlay.set_safe_mode(safe_mode)

    # Load Whisper (unless disabled)
    if not args.no_whisper:
        print(f"Loading Whisper model ({args.model})...")
        print("(This may take a minute on first run)")

        model_map = {
            'tiny': WhisperModel.TINY,
            'base': WhisperModel.BASE,
            'small': WhisperModel.SMALL,
            'medium': WhisperModel.MEDIUM
        }

        transcriber = WhisperTranscriber(model_name=model_map[args.model])
        overlay.set_transcriber(transcriber)
    else:
        print("Whisper disabled (--no-whisper flag)")
        # Enable recording without Whisper for testing
        overlay._whisper_loaded = True
        overlay._set_status(AgentStatus.IDLE)

    print()
    print("=" * 60)
    print("Agent ready!")
    print("=" * 60)
    print()
    print("Controls:")
    print("  - Hold SPACEBAR or click button to record")
    print("  - Release to transcribe and execute")
    print("  - Say 'help' for available commands")
    print("  - Press ESC to close")
    print()

    # Run overlay (blocking)
    overlay.run()

    # Cleanup
    print("\nShutting down...")
    if not args.no_whisper:
        transcriber.cleanup()

    print("Done!")


if __name__ == "__main__":
    main()
