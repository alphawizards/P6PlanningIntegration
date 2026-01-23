#!/usr/bin/env python3
"""
P6 Voice Agent Overlay Window.

Per agents.md Phase 3 & 4:
"Build a small 'Always on Top' window using tkinter.
Style: 'Always on Top', frameless window (overrideredirect(True))."

Features:
- Push-to-Talk button for voice recording
- Transcribed text display
- Status indicators (Listening, Thinking, Executing)
- Always-on-top positioning

Architecture:
- Main Thread: Tkinter GUI (never blocks)
- Background Thread: Whisper transcription (daemon)
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import time
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Import logging
try:
    from src.utils import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG)


class AgentStatus(Enum):
    """Agent status states for UI display."""
    IDLE = "Ready"
    LOADING = "Loading Whisper..."
    LISTENING = "Listening..."
    PROCESSING = "Processing..."
    EXECUTING = "Executing..."
    SUCCESS = "Done!"
    ERROR = "Error"


@dataclass
class StatusColors:
    """Color scheme for status indicators."""
    IDLE = "#4CAF50"       # Green
    LOADING = "#FF9800"    # Orange
    LISTENING = "#2196F3"  # Blue
    PROCESSING = "#9C27B0" # Purple
    EXECUTING = "#FF5722"  # Deep Orange
    SUCCESS = "#4CAF50"    # Green
    ERROR = "#F44336"      # Red


class P6VoiceOverlay:
    """
    Voice control overlay window for P6.

    Per agents.md:
    - Always on Top
    - Frameless window
    - Push-to-Talk recording
    - Real-time transcription display
    - Status feedback

    Threading Model:
    - Main thread: Tkinter event loop
    - Worker thread: Whisper transcription (daemon)
    - Communication: Queue-based message passing
    """

    # Window dimensions
    WINDOW_WIDTH = 400
    WINDOW_HEIGHT = 300
    WINDOW_PADDING = 10

    # Colors
    BG_COLOR = "#1E1E1E"        # Dark background
    TEXT_COLOR = "#FFFFFF"       # White text
    ACCENT_COLOR = "#0078D4"     # Blue accent
    BUTTON_COLOR = "#2D2D2D"     # Button background
    BUTTON_ACTIVE = "#3D3D3D"    # Button hover

    def __init__(
        self,
        on_command: Optional[Callable[[str], None]] = None,
        position: str = "bottom-right"
    ):
        """
        Initialize the overlay window.

        Args:
            on_command: Callback when voice command is received
            position: Window position ('bottom-right', 'bottom-left', 'top-right', 'top-left')
        """
        self._on_command = on_command
        self._position = position

        # State
        self._status = AgentStatus.LOADING
        self._is_recording = False
        self._whisper_loaded = False

        # Threading
        self._message_queue = queue.Queue()
        self._transcriber = None
        self._transcription_thread = None

        # Create window
        self._root = None
        self._create_window()

        logger.info("P6VoiceOverlay initialized")

    def _create_window(self):
        """Create the Tkinter overlay window."""
        self._root = tk.Tk()
        self._root.title("P6 Voice Agent")

        # Frameless window
        self._root.overrideredirect(True)

        # Window size
        self._root.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")

        # Always on top
        self._root.attributes('-topmost', True)

        # Background color
        self._root.configure(bg=self.BG_COLOR)

        # Position window
        self._position_window()

        # Create UI components
        self._create_title_bar()
        self._create_status_bar()
        self._create_transcript_area()
        self._create_record_button()
        self._create_controls()

        # Bind events
        self._bind_events()

        # Start message processing
        self._process_messages()

    def _position_window(self):
        """Position window according to preference."""
        screen_width = self._root.winfo_screenwidth()
        screen_height = self._root.winfo_screenheight()

        padding = 20

        if self._position == "bottom-right":
            x = screen_width - self.WINDOW_WIDTH - padding
            y = screen_height - self.WINDOW_HEIGHT - padding - 40  # Account for taskbar
        elif self._position == "bottom-left":
            x = padding
            y = screen_height - self.WINDOW_HEIGHT - padding - 40
        elif self._position == "top-right":
            x = screen_width - self.WINDOW_WIDTH - padding
            y = padding
        elif self._position == "top-left":
            x = padding
            y = padding
        else:
            # Center
            x = (screen_width - self.WINDOW_WIDTH) // 2
            y = (screen_height - self.WINDOW_HEIGHT) // 2

        self._root.geometry(f"+{x}+{y}")

    def _create_title_bar(self):
        """Create custom title bar (since window is frameless)."""
        title_frame = tk.Frame(self._root, bg=self.ACCENT_COLOR, height=30)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)

        # Title
        title_label = tk.Label(
            title_frame,
            text="P6 Voice Agent",
            bg=self.ACCENT_COLOR,
            fg=self.TEXT_COLOR,
            font=("Segoe UI", 10, "bold")
        )
        title_label.pack(side=tk.LEFT, padx=10)

        # Close button
        close_btn = tk.Button(
            title_frame,
            text="X",
            bg=self.ACCENT_COLOR,
            fg=self.TEXT_COLOR,
            font=("Segoe UI", 10, "bold"),
            bd=0,
            command=self._on_close,
            activebackground="#E81123",
            activeforeground=self.TEXT_COLOR
        )
        close_btn.pack(side=tk.RIGHT, padx=5)

        # Minimize button
        min_btn = tk.Button(
            title_frame,
            text="_",
            bg=self.ACCENT_COLOR,
            fg=self.TEXT_COLOR,
            font=("Segoe UI", 10, "bold"),
            bd=0,
            command=self._on_minimize,
            activebackground=self.BUTTON_ACTIVE,
            activeforeground=self.TEXT_COLOR
        )
        min_btn.pack(side=tk.RIGHT)

        # Make title bar draggable
        title_frame.bind("<Button-1>", self._start_drag)
        title_frame.bind("<B1-Motion>", self._on_drag)
        title_label.bind("<Button-1>", self._start_drag)
        title_label.bind("<B1-Motion>", self._on_drag)

    def _create_status_bar(self):
        """Create status indicator bar."""
        self._status_frame = tk.Frame(self._root, bg=self.BG_COLOR)
        self._status_frame.pack(fill=tk.X, padx=self.WINDOW_PADDING, pady=5)

        # Status indicator (colored dot)
        self._status_dot = tk.Canvas(
            self._status_frame,
            width=12,
            height=12,
            bg=self.BG_COLOR,
            highlightthickness=0
        )
        self._status_dot.pack(side=tk.LEFT)
        self._status_dot.create_oval(2, 2, 10, 10, fill=StatusColors.LOADING, outline="")

        # Status text
        self._status_label = tk.Label(
            self._status_frame,
            text=AgentStatus.LOADING.value,
            bg=self.BG_COLOR,
            fg=self.TEXT_COLOR,
            font=("Segoe UI", 9)
        )
        self._status_label.pack(side=tk.LEFT, padx=5)

    def _create_transcript_area(self):
        """Create scrollable transcript display."""
        transcript_frame = tk.Frame(self._root, bg=self.BG_COLOR)
        transcript_frame.pack(fill=tk.BOTH, expand=True, padx=self.WINDOW_PADDING, pady=5)

        # Label
        tk.Label(
            transcript_frame,
            text="Transcript:",
            bg=self.BG_COLOR,
            fg="#888888",
            font=("Segoe UI", 8),
            anchor=tk.W
        ).pack(fill=tk.X)

        # Text area
        self._transcript_text = scrolledtext.ScrolledText(
            transcript_frame,
            wrap=tk.WORD,
            bg="#2D2D2D",
            fg=self.TEXT_COLOR,
            font=("Consolas", 10),
            height=6,
            state=tk.DISABLED,
            relief=tk.FLAT,
            borderwidth=0
        )
        self._transcript_text.pack(fill=tk.BOTH, expand=True)

    def _create_record_button(self):
        """Create the push-to-talk record button."""
        button_frame = tk.Frame(self._root, bg=self.BG_COLOR)
        button_frame.pack(fill=tk.X, padx=self.WINDOW_PADDING, pady=10)

        # Large record button
        self._record_btn = tk.Button(
            button_frame,
            text="Hold to Record",
            bg=self.BUTTON_COLOR,
            fg=self.TEXT_COLOR,
            font=("Segoe UI", 12, "bold"),
            relief=tk.FLAT,
            activebackground=self.ACCENT_COLOR,
            activeforeground=self.TEXT_COLOR,
            height=2
        )
        self._record_btn.pack(fill=tk.X)

        # Bind press/release events
        self._record_btn.bind("<ButtonPress-1>", self._on_record_start)
        self._record_btn.bind("<ButtonRelease-1>", self._on_record_stop)

    def _create_controls(self):
        """Create additional control buttons."""
        control_frame = tk.Frame(self._root, bg=self.BG_COLOR)
        control_frame.pack(fill=tk.X, padx=self.WINDOW_PADDING, pady=(0, 10))

        # Clear button
        clear_btn = tk.Button(
            control_frame,
            text="Clear",
            bg=self.BUTTON_COLOR,
            fg=self.TEXT_COLOR,
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            command=self._clear_transcript
        )
        clear_btn.pack(side=tk.LEFT)

        # Safe mode indicator
        self._safe_mode_label = tk.Label(
            control_frame,
            text="SAFE MODE",
            bg="#FF9800",
            fg="#000000",
            font=("Segoe UI", 8, "bold"),
            padx=5,
            pady=2
        )
        self._safe_mode_label.pack(side=tk.RIGHT)

    def _bind_events(self):
        """Bind keyboard and window events."""
        # Spacebar as alternative to button
        self._root.bind("<KeyPress-space>", self._on_record_start)
        self._root.bind("<KeyRelease-space>", self._on_record_stop)

        # Escape to close
        self._root.bind("<Escape>", lambda e: self._on_close())

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def _start_drag(self, event):
        """Start window drag."""
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag(self, event):
        """Handle window drag."""
        x = self._root.winfo_x() + event.x - self._drag_start_x
        y = self._root.winfo_y() + event.y - self._drag_start_y
        self._root.geometry(f"+{x}+{y}")

    def _on_close(self):
        """Handle window close."""
        logger.info("Closing overlay")
        self._root.destroy()

    def _on_minimize(self):
        """Handle window minimize."""
        self._root.iconify()

    def _on_record_start(self, event=None):
        """Handle record button press."""
        if not self._whisper_loaded:
            self._append_transcript("[Whisper not loaded yet]")
            return

        self._is_recording = True
        self._set_status(AgentStatus.LISTENING)
        self._record_btn.configure(bg=self.ACCENT_COLOR, text="Recording...")

        # Start recording in background
        self._start_recording()

        logger.debug("Recording started")

    def _on_record_stop(self, event=None):
        """Handle record button release."""
        if not self._is_recording:
            return

        self._is_recording = False
        self._set_status(AgentStatus.PROCESSING)
        self._record_btn.configure(bg=self.BUTTON_COLOR, text="Hold to Record")

        # Stop recording and transcribe
        self._stop_recording()

        logger.debug("Recording stopped")

    def _clear_transcript(self):
        """Clear the transcript area."""
        self._transcript_text.configure(state=tk.NORMAL)
        self._transcript_text.delete(1.0, tk.END)
        self._transcript_text.configure(state=tk.DISABLED)

    # =========================================================================
    # Status Management
    # =========================================================================

    def _set_status(self, status: AgentStatus):
        """Update the status indicator."""
        self._status = status

        # Update text
        self._status_label.configure(text=status.value)

        # Update color
        color = getattr(StatusColors, status.name, StatusColors.IDLE)
        self._status_dot.delete("all")
        self._status_dot.create_oval(2, 2, 10, 10, fill=color, outline="")

    def _append_transcript(self, text: str):
        """Append text to transcript area."""
        self._transcript_text.configure(state=tk.NORMAL)
        self._transcript_text.insert(tk.END, text + "\n")
        self._transcript_text.see(tk.END)
        self._transcript_text.configure(state=tk.DISABLED)

    # =========================================================================
    # Recording & Transcription
    # =========================================================================

    def _start_recording(self):
        """Start audio recording."""
        if self._transcriber:
            self._transcriber.start_recording()

    def _stop_recording(self):
        """Stop recording and process audio."""
        if self._transcriber:
            # Run transcription in background thread
            def transcribe():
                try:
                    text = self._transcriber.stop_and_transcribe()
                    self._message_queue.put(("transcription", text))
                except Exception as e:
                    self._message_queue.put(("error", str(e)))

            thread = threading.Thread(target=transcribe, daemon=True)
            thread.start()

    def _process_messages(self):
        """Process messages from background threads (runs in main thread)."""
        try:
            while True:
                msg_type, msg_data = self._message_queue.get_nowait()

                if msg_type == "transcription":
                    self._handle_transcription(msg_data)
                elif msg_type == "whisper_loaded":
                    self._whisper_loaded = True
                    self._set_status(AgentStatus.IDLE)
                    self._append_transcript("[Whisper model loaded]")
                elif msg_type == "error":
                    self._set_status(AgentStatus.ERROR)
                    self._append_transcript(f"[Error: {msg_data}]")
                elif msg_type == "status":
                    self._set_status(msg_data)
                # FIX TS-002: Handle command responses from background thread
                elif msg_type == "command_response":
                    self._handle_command_response(msg_data)
                elif msg_type == "command_error":
                    self._handle_command_error(msg_data)

        except queue.Empty:
            pass

        # Schedule next check
        self._root.after(100, self._process_messages)

    def _handle_transcription(self, text: str):
        """Handle completed transcription."""
        if not text or text.strip() == "":
            self._set_status(AgentStatus.IDLE)
            return

        # Display transcription
        self._append_transcript(f"> {text}")
        self._set_status(AgentStatus.EXECUTING)

        # FIX TS-002: Run command in background thread to prevent UI freeze
        # The command handler may perform slow P6 GUI operations
        if self._on_command:
            def execute_command():
                try:
                    response = self._on_command(text)
                    self._message_queue.put(("command_response", response))
                except Exception as e:
                    self._message_queue.put(("command_error", str(e)))

            thread = threading.Thread(target=execute_command, daemon=True)
            thread.start()
        else:
            self._set_status(AgentStatus.IDLE)

    def _handle_command_response(self, response: str):
        """Handle command response from background thread."""
        if response:
            self._append_transcript(f"< {response}")
        self._set_status(AgentStatus.SUCCESS)
        # Reset to idle after brief delay
        self._root.after(2000, lambda: self._set_status(AgentStatus.IDLE))

    def _handle_command_error(self, error: str):
        """Handle command error from background thread."""
        self._append_transcript(f"[Error: {error}]")
        self._set_status(AgentStatus.ERROR)
        # Reset to idle after brief delay
        self._root.after(2000, lambda: self._set_status(AgentStatus.IDLE))

    # =========================================================================
    # Public Interface
    # =========================================================================

    def set_transcriber(self, transcriber):
        """
        Set the Whisper transcriber.

        Per agents.md:
        "Initialize WhisperTranscriber on startup (show loading spinner)."

        Args:
            transcriber: WhisperTranscriber instance
        """
        self._transcriber = transcriber

        # Load Whisper in background
        def load_whisper():
            try:
                self._transcriber.load_model()
                self._message_queue.put(("whisper_loaded", None))
            except Exception as e:
                self._message_queue.put(("error", f"Failed to load Whisper: {e}"))

        thread = threading.Thread(target=load_whisper, daemon=True)
        thread.start()

    def set_safe_mode(self, enabled: bool):
        """Update safe mode indicator."""
        if enabled:
            self._safe_mode_label.configure(bg="#FF9800", text="SAFE MODE")
        else:
            self._safe_mode_label.configure(bg="#4CAF50", text="EDIT MODE")

    def set_command_handler(self, handler: Callable[[str], str]):
        """Set the command handler callback."""
        self._on_command = handler

    def run(self):
        """
        Start the overlay (blocking).

        This runs the Tkinter main loop.
        """
        logger.info("Starting overlay main loop")
        self._root.mainloop()

    def close(self):
        """Close the overlay."""
        if self._root:
            self._root.destroy()


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """
    Run the overlay standalone for testing.

    Per agents.md Verification:
    "Run python src/gui/overlay.py and verify a small window appears over P6."
    """
    print("=" * 60)
    print("P6 Voice Agent Overlay - Test Mode")
    print("=" * 60)
    print()
    print("Controls:")
    print("  - Hold SPACEBAR or click button to record")
    print("  - Release to transcribe")
    print("  - Press ESC to close")
    print()

    def mock_command_handler(text: str) -> str:
        """Mock command handler for testing."""
        print(f"[MOCK] Received command: {text}")
        return f"Would execute: {text}"

    # Create overlay
    overlay = P6VoiceOverlay(
        on_command=mock_command_handler,
        position="bottom-right"
    )

    # Note: In production, would set transcriber here
    # overlay.set_transcriber(WhisperTranscriber())

    print("Overlay window should now be visible.")
    print("(Whisper not loaded in test mode)")
    overlay._whisper_loaded = True  # Allow testing without Whisper
    overlay._set_status(AgentStatus.IDLE)

    # Run
    overlay.run()


if __name__ == "__main__":
    main()
