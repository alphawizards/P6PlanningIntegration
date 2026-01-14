# P6 Report Automation - GUI Automation Roadmap

## Project Overview
Automate report printing from Primavera P6 Desktop using GUI automation (pywinauto) to trigger P6's native export features, then post-process the exported files.

**Tech Stack:** Python, pywinauto, psutil, reportlab, pandas

**Existing Dependencies:**
- pywinauto>=0.6.8
- psutil>=5.9.0
- reportlab>=4.0.0
- pandas>=2.0.0

---

## Phase 1: Environment Setup & P6 Discovery
**Goal:** Set up development environment and understand P6's UI structure

### Tasks:
1. Verify all dependencies are installed:
   ```bash
   pip install pywinauto psutil reportlab pandas
   ```
2. Launch P6 manually and document the exact workflow for exporting reports:
   - Menu paths (File > Print > Reports, etc.)
   - Dialog boxes that appear
   - Required inputs (project selection, date ranges, etc.)
   - Save locations and file naming
3. Use pywinauto's **inspect.exe** tool to explore P6's UI elements:
   - Window titles and class names
   - Button identifiers
   - Menu structure
4. Create screenshots of each step in the manual process
5. Test opening/closing P6 programmatically with psutil

**Deliverable:** Documented workflow + P6 UI element map

---

## Phase 2: P6 Process Control
**Goal:** Reliably launch, connect to, and close P6

### Tasks:
1. Write function to launch P6 executable:
   - Find P6 installation path
   - Handle different P6 versions if needed
   - Add startup wait time
2. Write function to connect to existing P6 instance (if already running)
3. Implement process detection using psutil:
   - Check if P6 is already running
   - Get P6 process ID
4. Create function to safely close P6:
   - Save any open projects
   - Handle "Save changes?" dialogs
   - Force kill if needed (with warning)
5. Add error handling for P6 crashes or freezes
6. Create retry logic for connection failures

**Deliverable:** `p6_process.py` - P6 lifecycle management module

---

## Phase 3: P6 Window & Dialog Automation
**Goal:** Build reliable functions to interact with P6's UI

### Tasks:
1. Create function to find and focus P6 main window
2. Implement menu navigation functions:
   - Access top menu bar (File, View, Tools, etc.)
   - Navigate through submenus
   - Handle dynamic menu states (grayed out options)
3. Build dialog box handlers:
   - "Open Project" dialog
   - "Print/Export" dialog
   - "Save As" dialog
   - Error message dialogs
4. Create wait functions for UI elements:
   - Wait for window to appear
   - Wait for button to become enabled
   - Timeout handling
5. Implement element verification (check if click succeeded)
6. Add screenshot capture on errors for debugging

**Deliverable:** `p6_ui_automation.py` - UI interaction functions

---

## Phase 4: Project Selection & Navigation
**Goal:** Automate opening specific projects and navigating to reports

### Tasks:
1. Create function to open a project by name:
   - Navigate to File > Open
   - Select project from list
   - Handle project not found errors
   - Wait for project to fully load
2. Implement project switching (if multiple projects needed)
3. Build navigation to Reports/Layouts section:
   - Access Reports menu
   - Select specific report type
   - Handle custom vs standard reports
4. Create functions for common P6 views:
   - Activity view
   - Gantt chart view
   - Resource usage view
5. Add date range/filter selection if needed
6. Handle project password/permissions dialogs

**Deliverable:** `p6_navigation.py` - Project and view navigation

---

## Phase 5: Report Export Automation
**Goal:** Automate the actual report export/print process

### Tasks:
1. Create function to trigger report export:
   - Navigate to File > Print or File > Export
   - Select output format (PDF/Excel)
   - Configure print settings
2. Implement file save dialog automation:
   - Set filename (with timestamp/project name)
   - Choose save location
   - Handle file exists prompts
3. Add report configuration options:
   - Page orientation (landscape/portrait)
   - Paper size
   - Headers/footers
   - Date ranges
4. Create function to verify export success:
   - Check if file was created
   - Verify file size > 0
   - Optional: Basic PDF/Excel validation
5. Handle export errors and retries
6. Add progress tracking for long-running exports

**Deliverable:** `p6_export.py` - Export automation functions

---

## Phase 6: Batch Processing Engine
**Goal:** Process multiple projects/reports in sequence

### Tasks:
1. Create configuration file format (JSON/YAML) for batch jobs:
   ```json
   {
     "projects": [
       {
         "name": "Project Alpha",
         "reports": ["Schedule", "Resources", "Cost"],
         "output_folder": "C:/Reports/Alpha"
       }
     ]
   }
   ```
2. Implement batch processing loop:
   - Read config file
   - Iterate through projects
   - Export each report
   - Handle failures gracefully
3. Add logging for each operation:
   - Timestamp each action
   - Log successes and failures
   - Create summary report at end
4. Implement error recovery:
   - Skip failed projects, continue with next
   - Restart P6 if it crashes
   - Save progress to resume if interrupted
5. Create email notification system (optional):
   - Send completion summary
   - Attach reports or provide links
   - Alert on failures

**Deliverable:** `batch_processor.py` + config template

---

## Phase 7: Post-Processing & Enhancement
**Goal:** Clean up and enhance exported reports

### Tasks:
1. Create file organization system:
   - Rename files with consistent naming (ProjectName_ReportType_Date.pdf)
   - Move to organized folder structure
   - Archive old reports
2. Implement PDF processing with reportlab:
   - Add cover page with summary
   - Add custom headers/footers
   - Merge multiple reports into single PDF
   - Add bookmarks/table of contents
3. Build Excel post-processing with pandas:
   - Clean up formatting
   - Add summary sheets
   - Create charts/graphs
   - Calculate additional metrics
4. Create report distribution system:
   - Copy to network shares
   - Upload to SharePoint/cloud
   - Email to stakeholders
5. Add report comparison features:
   - Compare current vs previous report
   - Highlight changes/differences

**Deliverable:** `post_processor.py` - Report enhancement module

---

## Phase 8: Reliability & Error Handling
**Goal:** Make the system robust and maintainable

### Tasks:
1. Implement comprehensive error handling:
   - Try-catch blocks around all P6 interactions
   - Graceful degradation
   - Clear error messages
2. Add retry mechanisms:
   - Retry failed operations (3 attempts)
   - Exponential backoff for waits
   - Circuit breaker for persistent failures
3. Create health check system:
   - Verify P6 is responsive before batch run
   - Check disk space for reports
   - Validate config files
4. Build recovery mechanisms:
   - Save state before each operation
   - Resume from last successful point
   - Manual intervention prompts when needed
5. Add timeout protections:
   - Maximum wait times for each operation
   - Kill and restart P6 if frozen
6. Implement screenshot debugging:
   - Capture screen on every error
   - Save to debug folder with timestamp
   - Include in error logs

**Deliverable:** Enhanced error handling across all modules

---

## Phase 9: Command-Line Interface & Scheduling
**Goal:** Easy execution and automation

### Tasks:
1. Create main CLI script using argparse:
   ```bash
   python main.py --config batch_config.json
   python main.py --project "Project Alpha" --report Schedule
   python main.py --all-projects
   ```
2. Add CLI options:
   - Config file path
   - Single project mode
   - Specific report selection
   - Output directory override
   - Dry-run mode (test without exporting)
   - Verbose/debug logging
3. Create Windows Task Scheduler setup:
   - Write .bat file for scheduled execution
   - Document Task Scheduler configuration
   - Handle running without user logged in
4. Add progress indicators:
   - Console progress bars
   - Estimated time remaining
   - Status updates
5. Create notification system:
   - Windows toast notifications
   - Email summaries
   - Slack/Teams webhooks (optional)

**Deliverable:** `main.py` + scheduling documentation

---

## Phase 10: Testing & Documentation
**Goal:** Ensure reliability and ease of use

### Tasks:
1. Create test suite:
   - Test P6 connection on/off
   - Test with mock P6 windows (if possible)
   - Test error scenarios
   - Test with different P6 versions
2. Perform integration testing:
   - Full batch run with test projects
   - Test all report types
   - Verify file outputs
   - Test recovery from failures
3. Load testing:
   - Run with 10+ projects
   - Check memory usage over time
   - Verify no resource leaks
4. Create user documentation:
   - Installation guide
   - Configuration guide with examples
   - Troubleshooting section
   - FAQ
5. Write developer documentation:
   - Code architecture overview
   - Function reference
   - How to add new report types
   - How to handle P6 UI changes
6. Create maintenance guide:
   - What to do when P6 updates
   - How to debug common issues
   - Log file locations and interpretation

**Deliverable:** Test suite + comprehensive documentation

---

## Phase 11: Monitoring & Maintenance (Ongoing)
**Goal:** Keep system running smoothly

### Tasks:
1. Set up monitoring:
   - Track success/failure rates
   - Monitor execution times
   - Alert on repeated failures
2. Create maintenance checklist:
   - Weekly: Review logs
   - Monthly: Test with latest P6 version
   - Quarterly: Update dependencies
3. Build UI change detection:
   - Test script after P6 updates
   - Document any UI changes needed
4. Maintain version compatibility matrix:
   - Document which P6 versions work
   - Test with new P6 releases
5. Continuous improvement:
   - Gather user feedback
   - Add new report types as needed
   - Optimize slow operations

**Deliverable:** Monitoring dashboard + maintenance procedures

---

## Working with Claude Code

### Starting a Session:
```
I'm working on P6 Report Automation (GUI automation approach).
Currently in Phase X: [phase name]
Working on: [specific task]
My P6 version: [version]
```

### Effective Prompts for Claude Code:

**For pywinauto help:**
- "Help me write a function to find and click the 'Export' button in P6"
- "How do I wait for a dialog box with title 'Save As' to appear?"
- "Debug why my menu navigation isn't working"

**For error handling:**
- "Add retry logic to this function with 3 attempts"
- "How should I handle the case where P6 crashes mid-export?"

**For testing:**
- "Write a test case for the project opening function"
- "How can I simulate P6 dialogs for testing?"

**For optimization:**
- "This wait time is too long, how can I make it smarter?"
- "Review this code for potential race conditions"

---

## Pro Tips for GUI Automation Success

### 🎯 Reliability Tips:
1. **Always use explicit waits** - Never use fixed time.sleep() if you can wait for specific UI elements
2. **Verify before proceeding** - Check that clicks/actions succeeded before moving to next step
3. **Handle the unexpected** - Always have error handlers for dialogs you don't expect
4. **Screenshot everything** - Capture screens on errors for easier debugging
5. **Start small** - Get one report working perfectly before automating all reports

### ⚙️ Development Tips:
1. **Use inspect.exe extensively** - Understand P6's UI structure before coding
2. **Test incrementally** - Run each function standalone before chaining
3. **Add verbose logging** - You'll thank yourself when debugging
4. **Keep P6 visible** - Watch automation run to catch issues early
5. **Version control** - Commit after each working feature

### 🛡️ Maintenance Tips:
1. **Document UI paths** - Write down exact menu paths (File > Reports > Custom > etc.)
2. **Take screenshots** - Visual documentation of expected UI state
3. **Test after P6 updates** - UI changes are the #1 cause of breakage
4. **Keep config external** - Easy to update without code changes
5. **Monitor execution times** - Sudden slowdowns indicate issues

---

## Known Limitations & Workarounds

### Limitation: Can't run while using computer
**Workaround:** Run on dedicated VM or after-hours schedule

### Limitation: Breaks with P6 UI changes
**Workaround:** Use element properties (not positions), maintain test suite

### Limitation: Occasional timing issues
**Workaround:** Smart waits with max timeouts, retry logic

### Limitation: Can't process reports P6 can't export
**Workaround:** Use post-processing to create custom formats

---

## Estimated Timeline

- **Phase 1-2:** 3-5 days (setup & P6 process control)
- **Phase 3-5:** 1-2 weeks (UI automation & export functions)
- **Phase 6-7:** 1 week (batch processing & post-processing)
- **Phase 8-9:** 3-5 days (reliability & CLI)
- **Phase 10:** 3-5 days (testing & documentation)

**Total:** 4-6 weeks for full implementation

**Quick MVP:** Phases 1-5 only = 2-3 weeks for basic single-report automation

---

## Success Criteria

✅ Successfully exports at least 3 report types  
✅ Handles 90%+ of runs without manual intervention  
✅ Completes batch job in under 2 hours  
✅ Recovers gracefully from common errors  
✅ Easy to add new report types  
✅ Clear logs for troubleshooting  

---

Good luck with your P6 automation! Remember: **start simple, test often, and handle errors gracefully**. 🚀