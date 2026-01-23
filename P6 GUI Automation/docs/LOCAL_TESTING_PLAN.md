# P6 Voice-Driven GUI Agent - Local Testing Plan

**Version:** 1.0
**Date:** 2026-01-23
**Purpose:** Step-by-step testing guide for the P6 Voice Agent

---

## Prerequisites

### Hardware Requirements
- Windows 10/11 PC
- Microphone (USB or built-in)
- Oracle Primavera P6 Professional installed

### Software Requirements
```bash
# Navigate to the P6 GUI Automation folder
cd "P6 GUI Automation"

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install ffmpeg (required for Whisper)
winget install ffmpeg
# OR download from https://ffmpeg.org/download.html
```

### Verify Installation
```bash
# Check Python version (3.10+ required)
python --version

# Check ffmpeg
ffmpeg -version

# Test imports
python -c "import pywinauto; import whisper; print('OK')"
```

---

## Test Execution

### Phase 1: Component Tests (No P6 Required)

#### Test 1.1: Overlay Window Launch
**Purpose:** Verify the overlay window displays correctly

```bash
cd "P6 GUI Automation"
python src/gui/overlay.py
```

**Expected Results:**
- [ ] Window appears in bottom-right corner
- [ ] Title bar shows "P6 Voice Agent"
- [ ] Status shows "Ready" (green dot)
- [ ] "SAFE MODE" indicator visible (orange)
- [ ] Window is draggable by title bar
- [ ] Close (X) and Minimize (_) buttons work
- [ ] ESC key closes window

**Pass Criteria:** All checkboxes pass

---

#### Test 1.2: Whisper Model Loading
**Purpose:** Verify Whisper loads without errors

```bash
cd "P6 GUI Automation"
python src/gui/whisper_handler.py
```

**Expected Results:**
- [ ] Model downloads/loads (may take 1-2 minutes first time)
- [ ] "Model loaded!" message appears
- [ ] Recording starts when prompted
- [ ] Transcription completes after 5 seconds
- [ ] Text output is reasonably accurate

**Pass Criteria:** Transcription produces readable text

---

#### Test 1.3: UI Responsiveness During Recording
**Purpose:** Verify FIX TS-002 - UI doesn't freeze

```bash
cd "P6 GUI Automation"
python main.py --no-whisper
```

**Steps:**
1. Click and hold "Hold to Record" button
2. While holding, try to:
   - Drag the window
   - Click "Clear" button
   - Press ESC (should close)

**Expected Results:**
- [ ] Window remains draggable during "recording"
- [ ] Buttons remain clickable
- [ ] No lag or freezing

**Pass Criteria:** UI responds within 200ms during operations

---

### Phase 2: Integration Tests (P6 Required)

#### Test 2.1: P6 Connection
**Purpose:** Verify agent detects P6 window

**Prerequisites:** Open Oracle Primavera P6 Professional

```bash
cd "P6 GUI Automation"
python main.py --safe-mode
```

**Expected Results:**
- [ ] Console shows "Found P6 window: [window title]"
- [ ] No "P6 window not found" warning

**Pass Criteria:** P6 window detected

---

#### Test 2.2: SAFE_MODE Enforcement (FIX SM-001)
**Purpose:** Verify all write operations are blocked in safe mode

```bash
cd "P6 GUI Automation"
python main.py --safe-mode
```

**Test Commands (speak into microphone):**
1. "Change duration of A1010 to 15 days"
2. "Delete activity A1010"
3. "Schedule the project"

**Expected Results:**
- [ ] Command 1: Response contains "[SAFE_MODE] Blocked"
- [ ] Command 2: Response contains "[SAFE_MODE] Blocked"
- [ ] Command 3: Response contains "[SAFE_MODE] Blocked" (FIX SM-001)
- [ ] NO changes made to P6 data

**Pass Criteria:** All three commands blocked, P6 data unchanged

---

#### Test 2.3: Activity Selection (Read Operation)
**Purpose:** Verify read operations work in safe mode

**Prerequisites:**
- P6 open with a project containing activity "A1010" (or similar)
- Agent running in safe mode

**Test Commands:**
1. "Select activity A1010"
2. "Go to first activity"
3. "Go to last activity"

**Expected Results:**
- [ ] Command 1: Activity highlighted in P6 grid
- [ ] Command 2: First activity selected
- [ ] Command 3: Last activity selected
- [ ] Overlay shows "Selected activity: [ID]"

**Pass Criteria:** Navigation works without modifying data

---

#### Test 2.4: Field Validation (FIX AI-001)
**Purpose:** Verify invalid field names are rejected

```bash
cd "P6 GUI Automation"
python main.py --unsafe
```

**Test Command:** "Change the Budget Cost of A1010 to 5000"

**Expected Results:**
- [ ] If "Budget Cost" is not a visible column, error message shows available fields
- [ ] No attempt to edit non-existent column

**Pass Criteria:** Invalid field names rejected with helpful error

---

### Phase 3: Edit Operations (UNSAFE MODE - Use Test Project!)

> **WARNING:** These tests modify P6 data. Use a TEST PROJECT only!

#### Test 3.1: Duration Edit
**Purpose:** Verify activity field editing works

```bash
cd "P6 GUI Automation"
python main.py --unsafe
```

**Prerequisites:**
- Test project with activity "A1010"
- Note original duration value

**Test Command:** "Change the Original Duration of A1010 to 15"

**Expected Results:**
- [ ] Activity A1010 is selected
- [ ] Cursor navigates to Original Duration column
- [ ] Value changes to "15"
- [ ] Overlay shows "Updated A1010.Original Duration = 15"

**Pass Criteria:** Duration value changed in P6

**Cleanup:** Manually restore original duration

---

#### Test 3.2: Project Scheduling (F9)
**Purpose:** Verify scheduling works in unsafe mode

**Test Command:** "Schedule the project"

**Expected Results:**
- [ ] F9 key sent to P6
- [ ] Scheduling dialog appears (if configured)
- [ ] Schedule completes
- [ ] Overlay shows "Project scheduled (F9)"

**Pass Criteria:** Schedule runs without errors

---

### Phase 4: Error Recovery Tests

#### Test 4.1: Dialog Interference
**Purpose:** Verify graceful failure when P6 has unexpected dialogs

**Steps:**
1. Open P6 Print Preview or another modal dialog
2. Say "Select activity A1010"

**Expected Results:**
- [ ] Agent reports error (does not hang)
- [ ] No crash or exception
- [ ] After closing dialog, agent works again

**Pass Criteria:** Graceful error handling, no hangs

---

#### Test 4.2: Audio Recording Cancellation
**Purpose:** Verify FIX TS-001 - race condition fixed

**Steps:**
1. Press and hold SPACEBAR to start recording
2. Quickly release after 0.5 seconds
3. Immediately press SPACEBAR again

**Expected Results:**
- [ ] No errors in console
- [ ] Transcription completes normally
- [ ] Second recording works correctly

**Pass Criteria:** No race condition errors

---

## Test Results Summary

| Test ID | Test Name | Status | Notes |
|---------|-----------|--------|-------|
| 1.1 | Overlay Window Launch | [ ] Pass / [ ] Fail | |
| 1.2 | Whisper Model Loading | [ ] Pass / [ ] Fail | |
| 1.3 | UI Responsiveness | [ ] Pass / [ ] Fail | |
| 2.1 | P6 Connection | [ ] Pass / [ ] Fail | |
| 2.2 | SAFE_MODE Enforcement | [ ] Pass / [ ] Fail | |
| 2.3 | Activity Selection | [ ] Pass / [ ] Fail | |
| 2.4 | Field Validation | [ ] Pass / [ ] Fail | |
| 3.1 | Duration Edit | [ ] Pass / [ ] Fail | |
| 3.2 | Project Scheduling | [ ] Pass / [ ] Fail | |
| 4.1 | Dialog Interference | [ ] Pass / [ ] Fail | |
| 4.2 | Audio Recording Cancellation | [ ] Pass / [ ] Fail | |
| 5.1 | Auto-Launch P6 | [ ] Pass / [ ] Fail | |
| 5.2 | Launcher Standalone | [ ] Pass / [ ] Fail | |
| 5.3 | Launch When Already Running | [ ] Pass / [ ] Fail | |

---

## Phase 5: P6 Launcher Tests (NEW)

#### Test 5.1: Auto-Launch P6 from Executable
**Purpose:** Verify P6 launches and logs in automatically

**Prerequisites:** P6 Professional is closed

```bash
cd "P6 GUI Automation"
python main.py --launch --password admin --safe-mode
```

**Expected Sequence:**
- [ ] Console shows "Launching P6 Professional..."
- [ ] P6 login dialog appears
- [ ] Password is entered automatically
- [ ] Connect button is clicked
- [ ] "Industry not selected" warning is dismissed (OK clicked)
- [ ] P6 main window loads
- [ ] Voice agent overlay appears

**Pass Criteria:** Full login sequence completes automatically

---

#### Test 5.2: Launch P6 Standalone (No Voice Agent)
**Purpose:** Test launcher module independently

```bash
cd "P6 GUI Automation"
python src/automation/p6_launcher.py --password admin
```

**Expected Results:**
- [ ] P6 launches
- [ ] Login succeeds
- [ ] Console shows "SUCCESS! P6 is ready."

**Pass Criteria:** P6 main window visible and ready

---

#### Test 5.3: Launch When P6 Already Running
**Purpose:** Verify launcher handles already-open P6

**Prerequisites:** P6 already open and logged in

```bash
python main.py --launch --password admin
```

**Expected Results:**
- [ ] Console shows "P6 is already running"
- [ ] Finds existing main window
- [ ] Voice agent starts normally

**Pass Criteria:** No duplicate P6 instances, agent connects to existing window

---

## Quick Reference: Agent Commands

### Safe Mode Commands (Read-Only)
- "Select activity [ID]"
- "Go to first activity"
- "Go to last activity"
- "Show columns" / "Get visible columns"
- "Help"

### Unsafe Mode Commands (Modify Data)
- "Change [field] of [activity] to [value]"
- "Set constraint [type] on [activity] to [date]"
- "Clear constraint on [activity]"
- "Add activity"
- "Delete activity [ID]"
- "Schedule the project" / "Press F9"

### Example Voice Commands
```
"Select activity A1010"
"Change the Original Duration of A1010 to 20 days"
"Set constraint Start On or After on A1010 to January 15"
"Schedule the project"
```

---

## Troubleshooting

### "P6 window not found"
- Ensure P6 Professional is open (not just P6 login screen)
- Try maximizing P6 window
- Check if P6 title contains "Primavera P6"

### "Whisper model failed to load"
- Install ffmpeg: `winget install ffmpeg`
- Check internet connection (first download)
- Try smaller model: `python main.py --model tiny`

### "PyAudio not installed"
```bash
pip install pipwin
pipwin install pyaudio
```

### Voice not recognized
- Check microphone permissions in Windows Settings
- Speak clearly and close to microphone
- Try longer phrases (1-3 seconds minimum)

---

## Fixes Applied in This Version

| Fix ID | Issue | Status |
|--------|-------|--------|
| SM-001 | SAFE_MODE bypass in reschedule | FIXED |
| TS-002 | UI freeze in command handler | FIXED |
| TS-001 | Race condition in audio callback | FIXED |
| SM-002 | Double execution risk in retry | FIXED |
| AI-001 | Field validation for LLM | FIXED |
