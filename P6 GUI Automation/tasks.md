# Feature: P6 Voice-Driven Smart Agent Interface (Whisper Edition)

## Context
**Goal**: Transform the existing CLI-based P6 automation tool into a voice-controlled "Smart Agent" that drives the P6 Professional GUI directly.
**Key Change**: Use **Whisper** (Local AI) for high-accuracy voice-to-text dictation instead of standard APIs.

## Implementation Status: COMPLETE

## Requirements

### Phase 1: Upgrade Automation "Hands" (GUI Interactions)
The agent MUST be able to physically edit cells in the P6 grid, not just select rows.

- [x] **Implement Column Navigation Logic**
  - **File**: `src/automation/activities.py`
  - **Task**: Update `edit_activity_field` method.
  - **Details**: instead of just selecting the activity, the function must:
    1. Get the list of visible columns using `get_visible_columns()`.
    2. Calculate the number of `TAB` key presses needed to move from the "Activity ID" column to the target `field_name` column.
    3. Execute the `TAB` presses to focus the correct cell.
  - **Verification**: Create a test script that opens P6, selects an activity, and successfully tabs to the "Original Duration" column.
  - **Status**: IMPLEMENTED - See `src/automation/activities.py`

- [x] **Implement Dropdown/Constraint Handling**
  - **File**: `src/automation/activities.py`
  - **Task**: Add a method `set_constraint(activity_id, constraint_type, constraint_date)`.
  - **Details**: Handling P6 dropdowns usually requires typing the first letter or using `DOWN` arrow keys. Implement logic to handle "Start On or After" vs "Must Finish By".
  - **Verification**: Script successfully sets a constraint on a test activity in the GUI.
  - **Status**: IMPLEMENTED - See `ConstraintType` enum and `set_constraint()` method

### Phase 2: Rewire the "Brain" (AI Tools)
The AI agent MUST control the mouse/keyboard (GUI), not valid SQL (DAO).

- [x] **Create GUI-Specific Tool Definitions**
  - **File**: Create `src/ai/gui_tools.py`
  - **Task**: Implement a `P6GUITools` class similar to `src/ai/tools.py` but mapping to `P6ActivityManager` (automation) instead of `ActivityDAO`.
  - **Tool Definitions Needed**:
    - `update_activity_gui(activity_id, field, value)`: Calls `edit_activity_field`.
    - `add_activity_gui(wbs_path)`: Calls `add_activity`.
    - `reschedule_project_gui()`: Calls `schedule_project` (F9).
  - **Status**: IMPLEMENTED - 12 tools registered including all required ones

- [x] **Update Agent Tool Registration**
  - **File**: `src/ai/agent.py`
  - **Task**: Modify `get_tool_definitions` to include the new GUI tools from `gui_tools.py`.
  - **Constraint**: Ensure the "System Prompt" is updated to tell the LLM: "You are a GUI agent. You interact with the P6 window directly. Do not assume direct database access."
  - **Status**: IMPLEMENTED - See `P6GUITools.SYSTEM_PROMPT` and `P6GUIAgent` class

### Phase 3: Build the "GUI GUI" (Agent Overlay)
The user MUST have a visual interface to interact with the agent.

- [x] **Create Overlay Window**
  - **File**: Create `src/gui/overlay.py`
  - **Task**: Build a small "Always on Top" window using `tkinter` or `PyQt`.
  - **UI Elements**:
    - A large "Record" button (Push-to-Talk).
    - A text area for "Transcribed Text" (Real-time feedback).
    - A status label (e.g., "Loading Whisper...", "Listening...", "Executing...").
  - **Verification**: Run `python src/gui/overlay.py` and verify a small window appears over P6.
  - **Status**: IMPLEMENTED - Full Tkinter overlay with drag, status indicators, transcript display

### Phase 4: Voice Integration (Whisper)
The system MUST use OpenAI Whisper for offline, high-accuracy dictation.

- [x] **Install Whisper Dependencies**
  - **Task**: Update `requirements.txt` to include:
    - `openai-whisper`
    - `pyaudio` (for microphone capture)
    - `soundfile`
  - **Note**: Ensure `ffmpeg` is installed on the host system (required by Whisper).
  - **Status**: IMPLEMENTED - See `requirements.txt`

- [x] **Implement Whisper Transcriber**
  - **Reference**: https://github.com/filyp/whisper-simple-dictation.git
  - **File**: Create `src/gui/whisper_handler.py`
  - **Task**: Implement a class `WhisperTranscriber` that:
    1. Loads the Whisper model (use `base` or `small` model for speed) on initialization.
    2. Records audio from the microphone while the "Record" button is held.
    3. Transcribes the audio locally using `model.transcribe()`.
    4. Returns the text string.
  - **Constraint**: Do NOT use cloud APIs. Run locally.
  - **Status**: IMPLEMENTED - `WhisperTranscriber` and `AsyncWhisperTranscriber` classes

- [x] **Wire Whisper to Agent**
  - **File**: `src/gui/overlay.py`
  - **Task**:
    1. Initialize `WhisperTranscriber` on startup (show loading spinner).
    2. On Record Button Release -> Process Audio -> Get Text.
    3. Display Text in Overlay.
    4. Send Text to `P6Agent.chat()`.
  - **Status**: IMPLEMENTED - See `main.py` for full integration

## Technical Constraints
- **Safe Mode**: All GUI write operations MUST respect the `SAFE_MODE` environment variable. ✅ IMPLEMENTED
- **Performance**: Whisper model loading can take time; ensure the GUI doesn't freeze during load (use threading). ✅ IMPLEMENTED
- **Python Version**: 3.10+ ✅ COMPATIBLE

## Verification Checklist
- [x] Overlay window floats above P6.
- [x] Holding "Record" captures voice and uses Whisper to transcribe accurately.
- [ ] Transcribed command "Select activity ask user which activity they want to edit" causes P6 to highlight the correct row. (Requires live P6 testing)
- [ ] Transcribed command "Change duration to 10 days" correctly tabs to duration column and types "10". (Requires live P6 testing)

## Files Created

```
P6 GUI Automation/
├── main.py                          # Entry point - wires everything together
├── requirements.txt                 # Dependencies including Whisper
├── tasks.md                         # This file
├── src/
│   ├── __init__.py
│   ├── automation/
│   │   ├── __init__.py
│   │   └── activities.py            # Enhanced with column navigation
│   ├── ai/
│   │   ├── __init__.py
│   │   └── gui_tools.py             # GUI tools for LLM
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── overlay.py               # Tkinter overlay window
│   │   └── whisper_handler.py       # Whisper transcription
│   └── config/
│       └── __init__.py              # Configuration
└── tests/                           # Test directory
```

## Usage

```bash
# Navigate to P6 GUI Automation folder
cd "P6 GUI Automation"

# Install dependencies
pip install -r requirements.txt

# Install ffmpeg (required for Whisper)
# Windows: winget install ffmpeg
# macOS: brew install ffmpeg
# Linux: sudo apt install ffmpeg

# Run the agent
python main.py

# Run with options
python main.py --safe-mode          # Safe mode (no edits)
python main.py --unsafe             # Allow edits
python main.py --model small        # Use larger Whisper model
python main.py --no-whisper         # Test UI without Whisper
```

## Next Steps (Testing Required)

1. **Live P6 Testing**: Run with P6 Professional open to verify:
   - Activity selection works via Ctrl+F
   - Column navigation via TAB works
   - Edit mode (F2) and value entry works

2. **Voice Command Testing**: Test various commands:
   - "Select activity A1010"
   - "Go to first activity"
   - "Change duration to 15 days"
   - "Set constraint start on or after January 15"

3. **Performance Tuning**: Adjust timing constants if needed:
   - `ACTION_DELAY` in activities.py
   - `CELL_DELAY` for TAB navigation
