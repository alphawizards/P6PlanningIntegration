#!/usr/bin/env python3
"""
P6 Command Tester - Text-based interface for testing P6 automation.

This bypasses voice/Whisper and lets you type commands directly.

Usage:
    python test_commands.py
    python test_commands.py --debug   # Enable verbose logging
"""

import sys
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging (enable debug with --debug flag)
if "--debug" in sys.argv:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    print("[DEBUG MODE ENABLED]")
else:
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

try:
    from pywinauto import Desktop
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False
    print("ERROR: pywinauto not installed. Run: pip install pywinauto")
    sys.exit(1)

from src.ai.gui_tools import P6GUITools, P6GUIAgent

def find_p6_window():
    """Find P6 window."""
    patterns = [
        ".*Primavera P6.*",
        ".*P6 Professional.*",
    ]
    for pattern in patterns:
        try:
            window = Desktop(backend="uia").window(title_re=pattern)
            if window.exists():
                return window
        except Exception:
            continue
    return None


def main():
    print("=" * 60)
    print("P6 Command Tester (Text Mode)")
    print("=" * 60)
    print()

    # Find P6
    print("Looking for P6 window...")
    p6_window = find_p6_window()

    if not p6_window:
        print("ERROR: P6 window not found!")
        print("Please open P6 Professional and try again.")
        return

    print(f"Found: {p6_window.window_text()}")
    print()

    # Create tools
    tools = P6GUITools(p6_window, safe_mode=True)

    print("Available commands:")
    print("-" * 40)
    print("  select <activity_id>  - Select an activity (e.g., select A1010)")
    print("  first                 - Go to first activity")
    print("  last                  - Go to last activity")
    print("  columns               - Show visible columns")
    print("  help                  - Show available tools")
    print("  quit                  - Exit")
    print("-" * 40)
    print()
    print("Type a command and press Enter:")
    print()

    while True:
        try:
            cmd = input("> ").strip().lower()

            if not cmd:
                continue

            if cmd in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            elif cmd.startswith("select "):
                activity_id = cmd.replace("select ", "").strip().upper()
                print(f"Selecting activity: {activity_id}")
                result = tools.execute("select_activity", activity_id=activity_id)
                status = "✓ SUCCESS" if result.success else "✗ FAILED"
                print(f"Result: [{status}] {result.message}")
                if result.error:
                    print(f"  Error: {result.error}")

            elif cmd == "first":
                print("Going to first activity...")
                result = tools.execute("go_to_first_activity")
                print(f"Result: {result.message}")

            elif cmd == "last":
                print("Going to last activity...")
                result = tools.execute("go_to_last_activity")
                print(f"Result: {result.message}")

            elif cmd in ("columns", "cols"):
                print("Getting visible columns...")
                result = tools.execute("get_visible_columns")
                if result.success:
                    cols = result.data.get("columns", [])
                    print(f"Found {len(cols)} columns:")
                    for i, col in enumerate(cols[:15], 1):
                        print(f"  {i}. {col}")
                    if len(cols) > 15:
                        print(f"  ... and {len(cols) - 15} more")
                else:
                    print(f"Error: {result.message}")

            elif cmd == "help":
                print("Available tools:")
                for tool_name in tools.get_available_tools():
                    info = tools.get_tool_info(tool_name)
                    if info:
                        safe = "" if info.requires_unsafe_mode else " (safe)"
                        print(f"  - {tool_name}{safe}")

            elif cmd == "schedule" or cmd == "f9":
                print("Scheduling project (F9)...")
                result = tools.execute("reschedule_project_gui")
                print(f"Result: {result.message}")

            else:
                print(f"Unknown command: {cmd}")
                print("Type 'help' for available commands")

            print()

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
            print()


if __name__ == "__main__":
    main()
