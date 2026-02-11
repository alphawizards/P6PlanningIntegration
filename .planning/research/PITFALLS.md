# Common Pitfalls: P6 GUI Automation

## Executive Summary

This document catalogs common mistakes, gotchas, and failure modes when automating Oracle Primavera P6 Professional via GUI automation. Based on research into enterprise application automation, Java Swing challenges, and P6-specific quirks across versions 21-23.

---

## 1. P6 UI Architecture Quirks

### 1.1 Java Swing/AWT Rendering

#### Issue: Custom-Drawn Controls
**Symptom:** Controls exist visually but pywinauto can't find them
**Root Cause:** P6 uses owner-drawn Swing components that don't expose standard accessibility properties
**Impact:** 30-40% of P6 controls are inaccessible via standard automation

**Affected Controls:**
- Gantt chart canvas (entire drawing area)
- Custom toolbar buttons with icons
- Status bar segments
- Some grid cell contents
- Tree view icons/checkboxes

**Detection:**
```python
# Use Inspect.exe (Windows SDK) in UIA mode
# If control shows as generic "Pane" with no properties → custom-drawn
```

**Workarounds:**
1. Use OCR for text extraction (slow, 300-500ms)
2. Use screen coordinates + image recognition
3. Use keyboard shortcuts instead of clicking
4. Access data via database read (validation only)

**Example:**
```python
# BAD: Try to click Gantt bar
gantt_bar = window.child_window(title="Activity A1010")  # Won't work

# GOOD: Use toolbar button
window.child_window(title="Go To").click()
type_keys("A1010{ENTER}")

# BETTER: Use menu shortcut
window.type_keys("^G")  # Ctrl+G for Go To
type_keys("A1010{ENTER}")
```

---

#### Issue: Dynamic Control IDs
**Symptom:** automation_id changes between P6 launches
**Root Cause:** Java generates control IDs dynamically, not from resource files
**Impact:** Scripts break on P6 restart

**Example:**
```python
# BAD: Hardcode automation_id
button = window.child_window(auto_id="javax.swing.JButton42")

# GOOD: Use stable properties
button = window.child_window(title="OK", class_name="Button")

# BETTER: Use position/index
buttons = window.children(class_name="Button")
ok_button = buttons[2]  # Third button is always OK
```

**Best Practices:**
- Never rely on automation_id for Java apps
- Use title, class_name, control_type
- Use positional indexes (fragile but sometimes only option)
- Cache control references during session (don't re-search)

---

### 1.2 Tree View Challenges

#### Issue: Lazy Loading EPS Tree
**Symptom:** Project not found in tree even though it exists
**Root Cause:** P6 only loads visible tree nodes; child nodes load on expand
**Impact:** Must expand entire tree path to find deeply nested projects

**Problem Code:**
```python
# BAD: Assumes entire tree is loaded
project_item = tree.get_item(r"EPS\Region\Site\Project")  # Fails

# GOOD: Expand path step-by-step
eps_node = tree.get_item("EPS")
eps_node.expand()
time.sleep(0.5)  # Wait for children to load

region_node = eps_node.get_child("Region")
region_node.expand()
time.sleep(0.5)

site_node = region_node.get_child("Site")
site_node.expand()
time.sleep(0.5)

project_node = site_node.get_child("Project")
```

**Performance Impact:**
- 10-level EPS hierarchy = 10 × 0.5s = 5 seconds
- 1000 projects = must scroll tree, very slow

**Optimization:**
```python
# Use search dialog instead of tree navigation
window.type_keys("^F")  # Ctrl+F for Find
type_keys("Project Name{ENTER}")
# Much faster: 1-2 seconds vs 5-10 seconds
```

---

#### Issue: Tree Item Text Extraction
**Symptom:** get_item() returns weird text or fails
**Root Cause:** Tree items have icons, badges, dynamic status text
**Impact:** String matching fails

**Example Tree Item Text:**
```
" [✓] Project 19282 - Highway Expansion (Active) "
```

**Challenges:**
- Leading/trailing spaces
- Unicode icons
- Status suffixes change
- May include newlines

**Robust Matching:**
```python
import re

def find_project_in_tree(tree, project_id):
    """Find project by ID, ignoring status text"""

    for item in tree.descendants():
        text = item.window_text().strip()

        # Extract project ID with regex
        match = re.search(r'\b' + re.escape(project_id) + r'\b', text)
        if match:
            return item

    raise ProjectNotFoundError(f"Project {project_id} not in tree")
```

---

### 1.3 Grid/Spreadsheet Automation

#### Issue: Activity Spreadsheet Performance
**Symptom:** Reading 1000 activities takes 10+ minutes
**Root Cause:** Grid cells are individual controls; accessing each is slow (50-100ms)
**Impact:** Unacceptable for large projects

**Bad Pattern:**
```python
# Reading grid row-by-row
activities = []
for row in range(1000):
    activity_id = grid.get_cell(row, 0).text()    # 50ms
    activity_name = grid.get_cell(row, 1).text()  # 50ms
    start_date = grid.get_cell(row, 2).text()     # 50ms
    # Total: 1000 rows × 3 cols × 50ms = 150 seconds
```

**Alternative Approaches:**

1. **Export to Excel/CSV** (fastest)
```python
# 5 seconds vs 150 seconds
exporter.export_excel("temp.xlsx")
df = pandas.read_excel("temp.xlsx")
```

2. **Select All + Clipboard** (fast)
```python
grid.type_keys("^A")  # Select all
grid.type_keys("^C")  # Copy
import win32clipboard
clipboard_data = win32clipboard.GetClipboardData()
# Parse tab-delimited data
```

3. **Database Query** (fastest, read-only)
```python
# If dual-connection mode available
activities = dao.get_activities(project_id)
```

---

#### Issue: Grid Cell Editing
**Symptom:** Cell edit doesn't stick or triggers unexpected dialogs
**Root Cause:** P6 has complex cell edit behavior (inline vs dialog, validation, constraints)

**Cell Edit Modes:**
- Text cells: Click once → inline edit
- Date cells: Click twice → date picker dialog (sometimes)
- Dropdown cells: Click → dropdown appears
- Calculated cells: Read-only, clicking does nothing

**Safe Edit Pattern:**
```python
def edit_activity_cell(grid, row, col, value, expect_dialog=False):
    """Safely edit grid cell"""

    # Click cell to select
    cell = grid.get_cell(row, col)
    cell.click_input()
    time.sleep(0.2)

    # Check if editable
    if cell.get_properties()['enabled'] == False:
        raise ValueError(f"Cell ({row},{col}) is read-only")

    if expect_dialog:
        # Double-click to open dialog
        cell.double_click_input()
        time.sleep(0.5)

        # Handle dialog
        dialog = window.child_window(class_name="Dialog")
        dialog.child_window(class_name="Edit").set_text(value)
        dialog.child_window(title="OK").click()
    else:
        # Inline edit
        cell.type_keys("^A")  # Select all
        cell.type_keys(value)
        cell.type_keys("{ENTER}")

    # Wait for validation
    time.sleep(0.3)

    # Check for error dialogs
    try:
        error_dialog = window.child_window(title_re=".*Error.*", timeout=1)
        error_msg = error_dialog.texts()[1]  # Get error message
        error_dialog.close()
        raise ValidationError(f"P6 validation failed: {error_msg}")
    except ElementNotFoundError:
        pass  # No error, success
```

---

## 2. pywinauto Reliability Issues

### 2.1 Backend Inconsistencies

#### Issue: UIA Backend Hangs
**Symptom:** Script freezes when accessing certain controls
**Root Cause:** UIA provider deadlock in Java bridge
**Frequency:** 5-10% of operations on complex dialogs

**Mitigation:**
```python
from multiprocessing import Process, Queue
import queue

def access_control_with_timeout(control_spec, timeout=5):
    """Access control with timeout protection"""

    def worker(q):
        try:
            control = window.child_window(**control_spec)
            q.put(control.texts())
        except Exception as e:
            q.put(e)

    q = Queue()
    p = Process(target=worker, args=(q,))
    p.start()
    p.join(timeout=timeout)

    if p.is_alive():
        p.terminate()
        p.join()
        raise TimeoutError(f"Control access hung: {control_spec}")

    try:
        result = q.get_nowait()
        if isinstance(result, Exception):
            raise result
        return result
    except queue.Empty:
        raise TimeoutError("No result from worker")
```

---

#### Issue: Backend Selection Affects Results
**Symptom:** Same code finds different controls with win32 vs uia
**Root Cause:** Different automation APIs expose different control trees

**Example:**
```python
# UIA backend
app_uia = Application(backend='uia').connect(path='PM.exe')
buttons_uia = app_uia.main_window.children(class_name='Button')
# Returns: 15 buttons

# Win32 backend
app_win32 = Application(backend='win32').connect(path='PM.exe')
buttons_win32 = app_win32.main_window.children(class_name='Button')
# Returns: 8 buttons (Java buttons missing)
```

**Best Practice:**
- Test both backends during development
- Document which backend works for each operation
- Create backend-switching wrapper

```python
class BackendAdapter:
    """Try UIA, fallback to Win32"""

    def __init__(self):
        self.app_uia = Application(backend='uia').connect(path='PM.exe')
        self.app_win32 = Application(backend='win32').connect(path='PM.exe')

    def find_control(self, **kwargs):
        """Try both backends"""
        try:
            return self.app_uia.window(**kwargs)
        except ElementNotFoundError:
            return self.app_win32.window(**kwargs)
```

---

### 2.2 Timing & Synchronization

#### Issue: Element Exists But Not Yet Ready
**Symptom:** Control found but click fails or returns wrong data
**Root Cause:** P6 renders control before it's fully initialized

**Common with:**
- Combo boxes (items still loading)
- Tree views (children populating)
- Grids (rows rendering)
- Dialogs (controls initializing)

**Bad Pattern:**
```python
# BAD: Existence check isn't enough
if dialog.exists(timeout=5):
    dialog.OK.click()  # Might fail
```

**Good Pattern:**
```python
# GOOD: Wait for specific ready state
dialog = window.child_window(title="Export")
dialog.wait('ready', timeout=10)  # Wait for enabled + visible + stable

# BETTER: Wait for specific sub-control
ok_button = dialog.child_window(title="OK")
ok_button.wait('enabled', timeout=10)
ok_button.click()
```

**P6-Specific Waits:**
```python
def wait_for_project_loaded(window, timeout=60):
    """Wait until project fully loaded"""

    start = time.time()
    while time.time() - start < timeout:
        # Check title bar for project ID
        title = window.texts()[0]
        if "Project:" in title:
            # Additional wait for activities to load
            time.sleep(2)
            return True

        time.sleep(0.5)

    raise TimeoutError("Project did not load")

def wait_for_grid_populated(grid, min_rows=1, timeout=30):
    """Wait until grid has data"""

    start = time.time()
    while time.time() - start < timeout:
        try:
            row_count = grid.row_count()
            if row_count >= min_rows:
                # Additional settle time
                time.sleep(0.5)
                return row_count
        except:
            pass

        time.sleep(0.5)

    raise TimeoutError(f"Grid did not populate (need {min_rows} rows)")
```

---

### 2.3 Control Identification Failures

#### Issue: Multiple Controls With Same Title
**Symptom:** Wrong button clicked (e.g., OK in nested dialog)
**Root Cause:** P6 has nested dialogs, multiple "OK" buttons visible

**Example Scenario:**
```
Main Window
  └─ Print Dialog
      └─ Advanced Settings Dialog
          └─ OK Button  ← Want this
      └─ OK Button      ← Accidentally get this
```

**Bad Pattern:**
```python
# BAD: Gets first OK button found (wrong one)
window.child_window(title="OK").click()
```

**Good Pattern:**
```python
# GOOD: Specify parent dialog
advanced_dialog = window.child_window(title="Advanced Settings")
ok_button = advanced_dialog.child_window(title="OK", found_index=0)
ok_button.click()

# BETTER: Use control hierarchy
print_dialog = window.child_window(title="Print")
advanced_button = print_dialog.child_window(title="Advanced...")
advanced_button.click()

advanced_dialog = print_dialog.child_window(title="Advanced Settings")
advanced_dialog.child_window(title="OK").click()
```

---

## 3. Dialog Chain Failures

### 3.1 Modal Dialog Detection

#### Issue: Unexpected Modal Dialog Blocks Automation
**Symptom:** Script hangs waiting for element that's hidden behind dialog
**Root Cause:** P6 shows confirmation/error dialogs unpredictably

**Common Unexpected Dialogs:**
- "Scheduling Complete" (after F9)
- "Do you want to save changes?" (on project close)
- "Activity has constraint conflicts" (on date edit)
- "Circular logic detected" (on relationship add)
- "Export completed successfully" (after export)
- "File already exists, overwrite?" (on export)

**Detection Pattern:**
```python
def check_for_modal_dialogs(window):
    """Detect and return any modal dialogs"""

    modal_dialogs = []

    # Common Java dialog class names
    dialog_classes = ["SunAwtDialog", "Dialog", "#32770"]

    for class_name in dialog_classes:
        try:
            dialogs = window.app.windows(class_name=class_name)
            for dlg in dialogs:
                if dlg.is_visible() and dlg.is_enabled():
                    modal_dialogs.append({
                        'window': dlg,
                        'title': dlg.texts()[0] if dlg.texts() else "Unknown",
                        'class': class_name
                    })
        except:
            pass

    return modal_dialogs
```

**Background Monitor:**
```python
import threading

class DialogMonitor:
    """Background thread that watches for dialogs"""

    def __init__(self, window, callback):
        self.window = window
        self.callback = callback
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._monitor)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def _monitor(self):
        while self.running:
            dialogs = check_for_modal_dialogs(self.window)
            if dialogs:
                for dlg in dialogs:
                    self.callback(dlg)

            time.sleep(0.5)

# Usage
def handle_unexpected_dialog(dialog):
    title = dialog['title']
    logger.warning(f"Unexpected dialog: {title}")

    # Auto-handle common dialogs
    if "Scheduling Complete" in title:
        dialog['window'].close()
    elif "Error" in title:
        error_text = dialog['window'].texts()
        logger.error(f"P6 Error: {error_text}")
        dialog['window'].close()
        raise P6Error(error_text)

monitor = DialogMonitor(window, handle_unexpected_dialog)
monitor.start()
# ... perform operations ...
monitor.stop()
```

---

### 3.2 Dialog Chain Complexity

#### Issue: Multi-Step Wizard Dialogs
**Symptom:** Script fails partway through wizard
**Root Cause:** Each wizard step is a different window/dialog

**Example: XER Import Wizard**
1. File selection dialog
2. Import options dialog
3. EPS assignment dialog
4. Conflict resolution dialog (conditional)
5. Progress dialog
6. Completion dialog

**Fragile Pattern:**
```python
# BAD: Assumes linear flow
menu.select("File -> Import -> XER")
file_dialog = window.wait_for_window("Open")
file_dialog.Edit.set_text("C:\\data.xer")
file_dialog.OK.click()
options_dialog = window.wait_for_window("Import Options")
options_dialog.OK.click()
# ... breaks if unexpected dialog appears
```

**Robust Pattern:**
```python
def import_xer_wizard(file_path, eps_path):
    """Handle XER import wizard with error recovery"""

    # Step 1: File selection
    menu.select("File -> Import -> XER")
    file_dialog = window.wait_for_window("Open", timeout=10)
    file_dialog.Edit.set_text(file_path)
    file_dialog.OK.click()

    # Step 2: Import options
    options_dialog = window.wait_for_window("Import Options", timeout=10)
    options_dialog.child_window(title="OK").click()

    # Step 3: EPS assignment (may not appear)
    try:
        eps_dialog = window.wait_for_window("Select EPS", timeout=5)
        eps_tree = eps_dialog.child_window(class_name="Tree")
        eps_node = find_eps_node(eps_tree, eps_path)
        eps_node.click_input()
        eps_dialog.child_window(title="OK").click()
    except TimeoutError:
        # EPS auto-assigned, continue
        pass

    # Step 4: Check for conflict dialog
    try:
        conflict_dialog = window.wait_for_window("Conflict", timeout=3)
        # Handle based on conflict type
        handle_import_conflict(conflict_dialog)
    except TimeoutError:
        # No conflicts, continue
        pass

    # Step 5: Wait for progress to complete
    wait_for_import_complete(window, timeout=300)

    # Step 6: Close completion dialog
    complete_dialog = window.wait_for_window("Import Complete", timeout=5)
    complete_dialog.child_window(title="OK").click()
```

---

## 4. Data Integrity Risks

### 4.1 Schedule Corruption

#### Issue: Activity Date Edit Causes Invalid Schedule
**Symptom:** Dates become nonsensical, critical path breaks, activities show errors
**Root Cause:** Constraint conflicts not handled

**Dangerous Operations:**
1. Setting start date before predecessor finish
2. Setting finish date after successor start
3. Editing dates without suspending constraints
4. Batch updates without validation

**Example Problem:**
```python
# Activity A1020 has predecessor A1010 (FS relationship)
# A1010 finishes: 2024-03-15
# Try to set A1020 start: 2024-03-01 (before predecessor!)

# P6 behavior varies:
# - May show error dialog
# - May auto-adjust constraint to "Must Start On"
# - May break relationship
# - May corrupt schedule
```

**Safe Pattern:**
```python
def edit_activity_date_safe(activity_id, field, new_date):
    """Edit date with validation"""

    # 1. Read current relationships
    preds = get_predecessors(activity_id)
    succs = get_successors(activity_id)

    # 2. Validate new date
    if field == "start_date":
        for pred in preds:
            if pred.relationship == "FS":
                if new_date < pred.finish_date:
                    raise ValidationError(
                        f"Cannot start before predecessor {pred.id} finishes ({pred.finish_date})"
                    )

    # 3. Create backup
    backup_file = export_xer_backup()

    try:
        # 4. Edit date
        edit_date_in_grid(activity_id, field, new_date)

        # 5. Schedule to recalc
        schedule_project()

        # 6. Verify no errors
        check_schedule_errors()

    except Exception as e:
        # Rollback
        import_xer(backup_file)
        raise ScheduleCorruptionError(f"Date edit caused corruption: {e}")
```

---

### 4.2 Relationship Corruption

#### Issue: Circular Logic Created
**Symptom:** Schedule won't calculate, shows "Circular logic detected"
**Root Cause:** Added relationship creates loop

**Example:**
```
A → B → C → D
User adds: D → A
Result: A → B → C → D → A (circular!)
```

**Prevention:**
```python
def add_relationship_safe(pred_id, succ_id, rel_type="FS", lag=0):
    """Add relationship with cycle detection"""

    # 1. Check if would create cycle
    if would_create_cycle(pred_id, succ_id):
        raise CircularLogicError(
            f"Adding {pred_id} → {succ_id} would create circular logic"
        )

    # 2. Check if duplicate
    existing = get_relationships(pred_id)
    for rel in existing:
        if rel.successor_id == succ_id:
            raise DuplicateRelationshipError(
                f"Relationship {pred_id} → {succ_id} already exists"
            )

    # 3. Add relationship
    add_relationship_in_gui(pred_id, succ_id, rel_type, lag)

def would_create_cycle(pred_id, succ_id):
    """Check if adding relationship creates cycle"""

    # BFS from succ_id to see if we can reach pred_id
    visited = set()
    queue = [succ_id]

    while queue:
        current = queue.pop(0)
        if current == pred_id:
            return True  # Found cycle

        if current in visited:
            continue

        visited.add(current)

        # Get successors of current
        succs = get_successors(current)
        queue.extend(s.id for s in succs)

    return False
```

---

### 4.3 Baseline Corruption

#### Issue: Baseline Overwritten Accidentally
**Symptom:** Historical data lost, variance reports wrong
**Root Cause:** P6 allows overwriting baselines without confirmation (in some versions)

**Dangerous Pattern:**
```python
# BAD: Overwrites without checking
create_baseline("Baseline 1")  # Destroys existing Baseline 1!
```

**Safe Pattern:**
```python
def create_baseline_safe(baseline_name, overwrite=False):
    """Create baseline with protection"""

    # Check if baseline exists
    existing = list_baselines()
    if baseline_name in existing and not overwrite:
        raise BaselineExistsError(
            f"Baseline '{baseline_name}' already exists. Use overwrite=True to replace."
        )

    # Warn if overwriting
    if baseline_name in existing and overwrite:
        logger.warning(f"Overwriting baseline: {baseline_name}")
        # Could require explicit confirmation here

    # Create baseline
    create_baseline_in_gui(baseline_name)
```

---

## 5. Timing & Sync Issues

### 5.1 Large Project Loading

#### Issue: Timeout on Large Projects
**Symptom:** Script fails with timeout when opening 10,000+ activity project
**Root Cause:** Fixed timeout too short

**Problem:**
```python
# BAD: Fixed timeout
def open_project(project_id, timeout=30):
    # 30 seconds not enough for large project
```

**Solution:**
```python
def open_project(project_id, timeout=None):
    """Open project with adaptive timeout"""

    # If timeout not specified, estimate based on project size
    if timeout is None:
        # Get activity count from database (fast)
        activity_count = db.query(
            "SELECT COUNT(*) FROM TASK WHERE PROJECT_ID = ?",
            project_id
        )

        # Estimate: 1 second per 100 activities, min 10s, max 300s
        timeout = max(10, min(300, activity_count / 100))

    # Open with calculated timeout
    open_project_in_gui(project_id, timeout)
```

---

### 5.2 Scheduling Delays

#### Issue: F9 Schedule Takes Unpredictable Time
**Symptom:** Sometimes 5 seconds, sometimes 5 minutes
**Root Cause:** Depends on project size, complexity, leveling options

**Factors:**
- Activity count (100 vs 10,000)
- Relationship count (sparse vs dense)
- Resource loading enabled (slow)
- Leveling enabled (very slow)
- Baseline comparison (slow)

**Adaptive Wait:**
```python
def schedule_project_adaptive(max_wait=600):
    """Schedule with progress monitoring"""

    # Trigger F9
    window.type_keys("{F9}")

    start = time.time()
    last_progress = None

    while time.time() - start < max_wait:
        # Check for progress dialog
        try:
            progress_dlg = window.child_window(title_re=".*Progress.*")
            progress_text = progress_dlg.texts()

            # Extract percentage if available
            # "Scheduling... 45% complete"
            match = re.search(r'(\d+)%', str(progress_text))
            if match:
                current_progress = int(match.group(1))
                if current_progress != last_progress:
                    logger.info(f"Scheduling: {current_progress}%")
                    last_progress = current_progress

            time.sleep(1)
            continue

        except ElementNotFoundError:
            # No progress dialog, check for completion dialog
            try:
                complete_dlg = window.child_window(title="Scheduling Complete")
                complete_dlg.close()
                return time.time() - start  # Return duration

            except ElementNotFoundError:
                # Neither progress nor complete, might be done
                time.sleep(1)

    raise SchedulingTimeoutError(f"Scheduling did not complete in {max_wait}s")
```

---

## 6. P6 Version Differences

### 6.1 Version-Specific Features

#### Issue: Feature Doesn't Exist in Older Version
**Symptom:** Script works on P6 v22, fails on v21
**Root Cause:** Feature added in newer version

**Examples:**

| Feature | Minimum Version | Workaround for Older |
|---------|----------------|---------------------|
| Check Schedule Report | 22.12 | Export XER, analyze externally |
| Side-by-side Activities | 22.12 | Use single view |
| Time-of-day editing | 21.12 | Skip time, dates only |
| Copy/paste cell ranges | 22.12 | One cell at a time |
| XML import improvements | 21.12 | Use XER format |

**Version Detection:**
```python
def get_p6_version():
    """Detect P6 version from window title or executable"""

    # Try from window title
    # "Primavera P6 Professional 22.12.0.0"
    title = window.texts()[0]
    match = re.search(r'P6.*?(\d+)\.(\d+)', title)
    if match:
        major = int(match.group(1))
        minor = int(match.group(2))
        return (major, minor)

    # Fallback: read from executable
    import win32api
    exe_path = find_p6_executable()
    info = win32api.GetFileVersionInfo(exe_path, '\\')
    version = "%d.%d" % (
        info['FileVersionMS'] >> 16,
        info['FileVersionMS'] & 0xFFFF
    )
    return tuple(map(int, version.split('.')))

# Feature flag pattern
class P6Features:
    def __init__(self, version):
        self.version = version

    @property
    def has_check_schedule_report(self):
        return self.version >= (22, 12)

    @property
    def has_side_by_side_views(self):
        return self.version >= (22, 12)

    @property
    def has_multi_cell_copy(self):
        return self.version >= (22, 12)

# Usage
version = get_p6_version()
features = P6Features(version)

if features.has_check_schedule_report:
    run_check_schedule_report()
else:
    logger.warning("Check Schedule Report not available in this P6 version")
```

---

### 6.2 UI Layout Changes

#### Issue: Menu Paths Changed Between Versions
**Symptom:** Menu selection fails on different version
**Root Cause:** Oracle reorganized menus

**Example:**
- P6 v21: View → Activities
- P6 v22: View → Additional Activities View

**Robust Menu Selection:**
```python
class P6Menus:
    """Version-aware menu paths"""

    def __init__(self, version):
        self.version = version

    def get_activities_view_path(self):
        if self.version >= (22, 0):
            return "View -> Additional Activities View"
        else:
            return "View -> Activities"

    def get_export_xer_path(self):
        # Consistent across versions
        return "File -> Export -> XER"

# Usage
menus = P6Menus(version)
menu.select(menus.get_activities_view_path())
```

---

## 7. Resource & Performance Issues

### 7.1 Memory Leaks

#### Issue: P6 Memory Usage Grows Over Time
**Symptom:** P6 becomes sluggish after hours of automation
**Root Cause:** P6 has known memory leaks (Java heap)

**Impact:**
- Batch operations (exporting 100 projects)
- Long-running automation (overnight jobs)
- Repeated open/close cycles

**Mitigation:**
```python
class P6AutomationWithRestart:
    """Restart P6 periodically to prevent memory issues"""

    def __init__(self, restart_interval=50):
        self.restart_interval = restart_interval  # Operations before restart
        self.operation_count = 0
        self.automation = None

    def __enter__(self):
        self.automation = P6PrintAutomation().__enter__()
        return self

    def __exit__(self, *args):
        if self.automation:
            self.automation.__exit__(*args)

    def execute(self, operation):
        """Execute operation, restart if needed"""

        # Check if restart needed
        if self.operation_count >= self.restart_interval:
            logger.info("Restarting P6 to free memory")
            self.automation.__exit__(None, None, None)
            time.sleep(5)
            self.automation = P6PrintAutomation().__enter__()
            self.operation_count = 0

        # Execute operation
        result = operation(self.automation)
        self.operation_count += 1
        return result

# Usage
with P6AutomationWithRestart(restart_interval=25) as p6:
    for project_id in range(100):
        p6.execute(lambda auto: export_project(auto, project_id))
```

---

### 7.2 Database Lock Contention

#### Issue: Dual-Connection Mode Conflicts
**Symptom:** Automation hangs or gets stale data
**Root Cause:** Both GUI and direct DB access compete for locks

**Problem:**
```python
# BAD: GUI and DB access interleaved
gui.edit_activity_date(...)  # Writes via GUI
activity = db.get_activity(...)  # Reads via DB (stale!)
```

**Solution:**
```python
# GOOD: Separate read and write phases
# Write phase (GUI only)
gui.edit_activity_date(...)
gui.schedule_project()

# Wait for P6 to commit
time.sleep(2)

# Read phase (DB only)
activity = db.get_activity(...)
```

---

## 8. Environmental Issues

### 8.1 Display Scaling

#### Issue: Coordinates Wrong on High-DPI Displays
**Symptom:** Clicks miss targets on 4K monitors
**Root Cause:** Windows display scaling (150%, 200%)

**Detection:**
```python
import win32api

def get_display_scaling():
    """Get Windows display scaling percentage"""
    hdc = win32api.GetDC(0)
    dpi = win32api.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
    scaling = dpi / 96.0  # 96 DPI = 100%
    win32api.ReleaseDC(0, hdc)
    return scaling

scaling = get_display_scaling()
if scaling != 1.0:
    logger.warning(f"Display scaling detected: {scaling*100}% - may cause coordinate issues")
```

**Workaround:**
- Use UIA backend (DPI-aware)
- Avoid coordinate-based clicks
- Use control references instead

---

### 8.2 Anti-Virus Interference

#### Issue: Automation Intermittently Slow or Fails
**Symptom:** Same script takes 10× longer randomly
**Root Cause:** Anti-virus scanning Python process, XER files, etc.

**Detection:**
```python
import time

# Measure baseline performance
start = time.time()
for _ in range(100):
    window.child_window(title="OK").exists(timeout=0.1)
elapsed = time.time() - start

if elapsed > 5:  # Should be ~1-2 seconds
    logger.warning("Performance degradation detected - possible AV interference")
```

**Mitigation:**
- Add Python, P6, temp directory to AV exclusions
- Use network paths instead of local (not scanned)
- Run automation during off-hours

---

## 9. Lessons Learned Summary

### Top 10 Mistakes

1. **Hardcoding automation_id** for Java controls → Use title/class
2. **Not handling modal dialogs** → Background monitor + recovery
3. **Fixed timeouts for all operations** → Adaptive based on data size
4. **Reading grid cell-by-cell** → Export to file first
5. **No version detection** → Feature flags per version
6. **Assuming tree is fully loaded** → Expand path step-by-step
7. **Editing dates without constraint validation** → Pre-check logic
8. **No backup before destructive operations** → Export XER first
9. **Relying on UIA for performance** → Hybrid UIA/Win32 approach
10. **Not restarting P6 in long batches** → Periodic restart

### Best Practices Checklist

- [ ] Use UIA backend by default, Win32 as fallback
- [ ] Always wait for "ready" state, not just "exists"
- [ ] Implement dialog monitoring for unexpected modals
- [ ] Version-detect P6 and adjust features/menus
- [ ] Create XER backup before any write operations
- [ ] Use database reads to avoid slow grid access
- [ ] Implement adaptive timeouts based on data size
- [ ] Restart P6 every 25-50 operations in batch mode
- [ ] Log all operations with structured logging
- [ ] Test on multiple P6 versions (21, 22, 23)

---

## Sources & References

- [pywinauto Documentation](https://pywinauto.readthedocs.io/en/latest/)
- [Java Application Automation Challenges](https://groups.google.com/g/comp.lang.python/c/oa2BJNv8p1I)
- [UI Automation - Modal Dialog Issues](https://learn.microsoft.com/en-us/answers/questions/409327/ui-automation-modal-dialog-prevents-automation)
- [P6 Version Differences](https://www.p6consulting.ca/blog/what-are-the-differences-between-versions-of-primavera-p6/)
- [What's New in P6 v22.12](https://www.taradigm.com/whats-new-in-primavera-p6-professional-22-12/)
- [What's New in P6 v23](https://eastwoodharris.com/whats-new-in-oracle-primavera-p6-ppm-professional-version-23/)
- [Data Integrity in Automation](https://www.ibm.com/think/insights/data-integrity-strategy)
- [Common Data Integrity Issues](https://www.dataversity.net/common-data-integrity-issues-and-how-to-overcome-them/)
- [Tree View Automation Challenges](https://community.smartbear.com/kb/testcomplete-community-techarticles/ocr-in-ui-test-automation-extending-coverage-where-traditional-identification-br/279460)

---

**Document Version:** 1.0
**Last Updated:** 2026-02-07
**Based On:** Enterprise GUI automation research, Java Swing challenges, P6 versions 21-23
**Primary Lesson:** Expect the unexpected, validate everything, backup before writes
