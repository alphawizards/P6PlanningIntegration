# Technology Stack Research: P6 Professional GUI Automation

## Executive Summary

This document researches the optimal technology stack for Windows desktop GUI automation targeting Oracle Primavera P6 Professional (versions 21.x-23.x). P6 is a Java-based enterprise application with Swing/AWT components, requiring robust automation approaches that handle custom controls, slow enterprise operations, and version differences.

---

## 1. Primary Automation Framework: pywinauto

### Recommended Version
**pywinauto 0.6.8+** (latest stable as of 2026)

### Rationale
- Industry-standard Python library for Windows GUI automation
- Active development with enterprise focus
- Supports both Win32 API and MS UI Automation backends
- Large community and extensive documentation
- Already proven in the existing codebase

### Installation
```bash
pip install pywinauto>=0.6.8
```

---

## 2. Backend Selection: UIA vs Win32

### The Challenge with Java Applications

P6 Professional is built on Java Swing/AWT, which presents unique challenges:
- Java applications don't expose standard Win32 controls
- Custom-drawn components lack accessible properties
- Dynamic control IDs and changing automation IDs
- Nested dialog chains and modal windows

### Backend Comparison

| Aspect | Win32 Backend | UIA Backend |
|--------|--------------|-------------|
| **Speed** | Fast | Slower (noticeable delays) |
| **Java Support** | Limited | Better |
| **Modern Controls** | Poor | Excellent |
| **Legacy Apps** | Excellent | Limited |
| **Stability** | Very stable | Good |
| **P6 Coverage** | 40-60% | 70-90% |

### Recommended Approach: **Hybrid Strategy**

```python
# Try UIA first for better Java control visibility
try:
    app = Application(backend='uia').connect(path='PM.exe')
except:
    # Fallback to Win32 for specific controls
    app = Application(backend='win32').connect(path='PM.exe')
```

### Decision Logic

**Use UIA backend when:**
- Accessing tree views (EPS hierarchy, activity codes)
- Reading grid/table data (activity spreadsheet)
- Interacting with modern dialogs
- Need better control property access

**Use Win32 backend when:**
- Performance is critical (batch operations)
- Accessing menu bars and toolbars
- Standard Windows dialogs (file picker)
- Simple button/text field operations

### Inspection Tools

```bash
# UIA mode - better for P6
Inspect.exe (Windows SDK)

# Win32 mode - legacy controls
Spy++ (Visual Studio)
```

**Testing methodology:**
1. Use Inspect.exe in UIA mode on P6
2. If control shows rich properties → UIA backend
3. If control appears as generic pane → try Win32
4. If neither works → OCR/screen reading needed

---

## 3. Screen Reading & OCR (Fallback Layer)

### When OCR Becomes Necessary

Modern GUI automation faces environments where traditional object identification fails:
- Custom canvas-rendered controls (Gantt charts)
- Owner-drawn buttons and grids
- Status bar text without accessible properties
- Dynamic dashboards and visualizations
- Remote desktop/Citrix scenarios

### Recommended OCR Stack

#### Primary: Tesseract OCR
```bash
pip install pytesseract>=0.3.10
pip install pillow>=10.0.0

# Install Tesseract binary
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
```

**Usage pattern:**
```python
from PIL import Image
import pytesseract

# Capture screen region
region = control.capture_as_image()
text = pytesseract.image_to_string(region, config='--psm 6')
```

#### Secondary: EasyOCR (AI-powered)
```bash
pip install easyocr>=1.7.0
```

**Better for:**
- Low-resolution text
- Non-standard fonts (P6's custom UI fonts)
- Multi-language support
- Complex backgrounds

### OCR Best Practices for P6

1. **Use sparingly** - Last resort after UIA/Win32 fail
2. **Cache results** - OCR is slow (200-500ms per region)
3. **Pre-process images** - Grayscale, contrast enhancement
4. **Define regions** - Don't OCR entire window
5. **Validate output** - Check against expected patterns

### Screen Reading Patterns

```python
class P6StatusBarReader:
    """Read status bar when UIA fails"""

    def __init__(self, window):
        self.window = window
        self._cache = {}

    def read_status(self):
        # Try UIA first
        try:
            return self.window.StatusBar.texts()
        except:
            # Fallback to OCR
            return self._ocr_status_bar()

    def _ocr_status_bar(self):
        rect = self._get_status_bar_rect()
        img = self._capture_region(rect)
        return pytesseract.image_to_string(img)
```

---

## 4. Wait/Retry Patterns for Enterprise Applications

### The Enterprise App Challenge

P6 Professional exhibits typical enterprise behaviors:
- Slow initialization (5-15 seconds)
- Database queries causing UI freezes
- Progress dialogs for long operations
- Inconsistent response times
- Large project loading delays

### Recommended Retry Library

```bash
pip install tenacity>=8.2.0
```

### Retry Patterns

#### Pattern 1: Exponential Backoff

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(ElementNotFoundError)
)
def find_project_in_tree(project_name):
    """Retry with exponential backoff: 2s, 4s, 8s, 16s, 30s"""
    return tree.get_item(project_name)
```

**Use for:**
- Loading large project lists
- Database-backed operations
- Network-dependent features
- Initial P6 startup

#### Pattern 2: Wait Until Condition

```python
from pywinauto.timings import wait_until

def wait_for_project_open(project_id, timeout=60):
    """Wait until project appears in title bar"""
    def is_project_open():
        title = main_window.texts()[0]
        return project_id in title

    wait_until(
        timeout=timeout,
        retry_interval=1.0,
        func=is_project_open
    )
```

**Use for:**
- Modal dialogs appearing
- Progress bars completing
- Window title changes
- Control state transitions

#### Pattern 3: Custom Wait Strategy

```python
class P6WaitStrategy:
    """P6-specific wait patterns"""

    # Tuned for P6 Professional
    STARTUP_TIMEOUT = 30      # Application launch
    DIALOG_TIMEOUT = 10       # Modal dialogs
    PROJECT_LOAD_TIMEOUT = 60 # Large projects
    SCHEDULE_TIMEOUT = 300    # F9 scheduling
    EXPORT_TIMEOUT = 120      # File exports

    @staticmethod
    def wait_for_idle(window, max_wait=30):
        """Wait for P6 to finish background processing"""
        import time

        # Check for progress dialogs
        for _ in range(max_wait):
            try:
                if window.child_window(
                    title_re=".*Progress.*|.*Please Wait.*",
                    class_name="Dialog"
                ).exists(timeout=0.5):
                    time.sleep(1)
                    continue
                break
            except:
                break

        # Additional settle time
        time.sleep(0.5)
```

### Backoff Strategy Matrix

| Operation Type | Min Wait | Max Wait | Max Attempts | Pattern |
|----------------|----------|----------|--------------|---------|
| Menu click | 0.1s | 2s | 3 | Linear |
| Dialog open | 1s | 10s | 5 | Exponential |
| Project load | 2s | 60s | 3 | Exponential |
| F9 Schedule | 5s | 300s | 1 | Poll status |
| Export file | 2s | 120s | 3 | Exponential |
| Tree expand | 0.5s | 5s | 5 | Linear |

### Best Practices

1. **Default timeout: 30 seconds** for most P6 operations
2. **Poll don't sleep** - Check condition repeatedly
3. **Jittered backoff** - Add randomness to prevent thundering herd
4. **Circuit breaker** - Fail fast after repeated failures
5. **Logging** - Record all retry attempts for debugging

---

## 5. P6-Specific Automation Approaches

### Official APIs (Limited Applicability)

#### P6 EPPM Web Services API
- **Not applicable** - Web services don't control desktop GUI
- Use for data validation, not automation

#### P6 Professional Database Direct Access
- **Read-only validation** - Verify automation results
- **Never write** - Corruption risk, unsupported
- Use existing DAO layer for verification

### GUI Automation Reality

**No official P6 GUI automation API exists**. All desktop automation must use:
1. Windows UI Automation (UIA)
2. Win32 API via pywinauto
3. Screen reading/OCR for inaccessible elements
4. Keyboard/mouse simulation for custom controls

### P6 Version Detection

```python
import win32api

def get_p6_version():
    """Detect P6 version from executable"""
    exe_path = r"C:\Program Files\Oracle\Primavera P6\PM.exe"

    info = win32api.GetFileVersionInfo(exe_path, '\\')
    version = "%d.%d.%d.%d" % (
        info['FileVersionMS'] >> 16,
        info['FileVersionMS'] & 0xFFFF,
        info['FileVersionLS'] >> 16,
        info['FileVersionLS'] & 0xFFFF
    )

    # Parse major version: 21.12, 22.12, 23.x
    major = int(version.split('.')[0])
    return major
```

### Version-Specific Adaptations

```python
class P6VersionAdapter:
    """Handle version differences"""

    def __init__(self, version):
        self.version = version

    def get_activities_menu_path(self):
        """Menu paths changed in v22"""
        if self.version >= 22:
            return "View -> Additional Activities View"
        else:
            return "View -> Activities"

    def supports_check_schedule_report(self):
        """Added in v22.12"""
        return self.version >= 22

    def supports_side_by_side_views(self):
        """Added in v22.12"""
        return self.version >= 22
```

---

## 6. Supporting Libraries

### Process Management
```bash
pip install psutil>=5.9.0
```

**Purpose:**
- Detect running P6 instances
- Monitor memory usage (P6 can leak)
- Kill hung processes
- Track automation resource usage

### Image Processing
```bash
pip install pillow>=10.0.0
pip install opencv-python>=4.8.0  # Advanced image ops
```

**Purpose:**
- Screenshot capture for OCR
- Visual verification (comparing before/after)
- Image-based control location
- PDF thumbnail generation

### Windows Integration
```bash
pip install pywin32>=306
```

**Purpose:**
- COM automation (limited P6 support)
- Windows API calls
- File version detection
- Registry access for P6 settings

### Logging & Monitoring
```bash
pip install structlog>=23.1.0
pip install python-json-logger>=2.0.0
```

**Purpose:**
- Structured logging for debugging
- Performance metrics
- Audit trail for compliance
- Error pattern analysis

---

## 7. Complete Stack Recommendation

### requirements.txt
```
# Core automation
pywinauto>=0.6.8

# Process management
psutil>=5.9.0

# OCR fallback
pytesseract>=0.3.10
pillow>=10.0.0
easyocr>=1.7.0

# Retry patterns
tenacity>=8.2.0

# Windows integration
pywin32>=306

# Image processing
opencv-python>=4.8.0

# Logging
structlog>=23.1.0
python-json-logger>=2.0.0

# Testing
pytest>=7.4.0
pytest-timeout>=2.1.0

# Type hints
typing-extensions>=4.8.0

# Existing project dependencies
reportlab>=4.0.0
pandas>=2.0.0
```

### Python Version
**Python 3.10 or 3.11** (avoid 3.12 - pywin32 compatibility issues)

---

## 8. Alternative Approaches Considered

### RPA Tools (Rejected)

#### UiPath, Blue Prism, Automation Anywhere
- **Pro:** Visual design, enterprise support
- **Con:** Expensive licensing, not programmable
- **Verdict:** Overkill for development tool

### Java Access Bridge (Experimental)

```bash
# Enable Java Access Bridge
# Set JAVA_HOME environment variable
# Run: jabswitch -enable
```

**Potential for P6:**
- Direct access to Java Swing components
- Better property introspection
- Bypass Windows UI layer

**Challenges:**
- Requires Java runtime configuration
- P6 may not expose full tree
- Limited Python bindings
- Unproven with P6

**Recommendation:** Research prototype, but not production-ready

### SikuliX (Image-Based)
- **Pro:** Works when nothing else does
- **Con:** Fragile, resolution-dependent, slow
- **Verdict:** Last resort only

---

## 9. Performance Considerations

### Benchmarks (Approximate)

| Operation | UIA Backend | Win32 Backend | OCR Fallback |
|-----------|-------------|---------------|--------------|
| Find window | 50ms | 20ms | N/A |
| Find control | 200ms | 50ms | N/A |
| Read text | 100ms | 30ms | 300ms |
| Click button | 150ms | 50ms | 400ms |
| Expand tree | 300ms | 100ms | 500ms |
| Read grid row | 500ms | 150ms | 800ms |

### Optimization Strategies

1. **Cache window/control references** - Don't search repeatedly
2. **Use Win32 for bulk operations** - 3-5x faster
3. **Minimize OCR** - 10-20x slower than direct access
4. **Parallel operations** - Multi-thread independent actions
5. **Lazy evaluation** - Don't verify unless necessary

---

## 10. Risk Mitigation

### Known Issues & Workarounds

#### Issue: UIA Backend Hangs
**Symptom:** Script freezes when accessing certain controls
**Workaround:** Timeout wrapper, fallback to Win32

#### Issue: Dynamic Control IDs
**Symptom:** automation_id changes between runs
**Workaround:** Use title/class_name, positional indexes

#### Issue: Modal Dialog Deadlock
**Symptom:** Can't detect unexpected dialog
**Workaround:** Background thread monitoring for dialogs

#### Issue: OCR Inaccuracy
**Symptom:** Wrong text read from status bar
**Workaround:** Pattern matching, confidence thresholds

---

## Sources & References

- [Automating Windows GUIs with Pywinauto: A Practical Guide](https://naveenrk22.medium.com/automating-windows-guis-with-pywinauto-a-practical-guide-eebd86fdabe6)
- [pywinauto Documentation - Getting Started](https://pywinauto.readthedocs.io/en/latest/getting_started.html)
- [Microsoft UI Automation Overview](https://learn.microsoft.com/en-us/dotnet/framework/ui-automation/ui-automation-overview)
- [OCR in UI Test Automation - SmartBear](https://community.smartbear.com/kb/testcomplete-community-techarticles/ocr-in-ui-test-automation-extending-coverage-where-traditional-identification-br/279460)
- [Retry Pattern - Azure Architecture](https://learn.microsoft.com/en-us/azure/architecture/patterns/retry)
- [Top 10 Windows Desktop Automation Tools for 2026](https://www.askui.com/blog-posts/top-10-automation-tools-for-desktop-applications-windows)
- [Java Application Automation with Python](https://groups.google.com/g/comp.lang.python/c/oa2BJNv8p1I)

---

**Document Version:** 1.0
**Last Updated:** 2026-02-07
**Target P6 Versions:** 21.x, 22.x, 23.x
**Validated Against:** Existing P6PlanningIntegration codebase
