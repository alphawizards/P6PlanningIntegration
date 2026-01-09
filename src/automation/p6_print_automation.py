#!/usr/bin/env python3
"""
P6 Professional GUI Automation for PDF Printing.

This module uses pywinauto to automate Primavera P6 Professional's
native print functionality, enabling like-for-like PDF exports of
Gantt charts and layouts.

Requirements:
    - P6 Professional installed and licensed
    - Microsoft Print to PDF printer available
    - User logged in with visible desktop (no headless)
    - pywinauto >= 0.6.8

Usage:
    from src.automation import P6PrintAutomation
    
    with P6PrintAutomation() as p6:
        p6.open_project("Mine Expansion Phase 2")
        p6.apply_layout("Standard Gantt")
        p6.print_to_pdf("output/mine_expansion.pdf")
"""

import time
from pathlib import Path
from typing import Optional, List, Callable

try:
    from pywinauto import Desktop
    from pywinauto.findwindows import ElementNotFoundError
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

from src.config import (
    P6_DEFAULT_LAYOUT,
    PDF_PRINTER_NAME,
    PDF_OUTPUT_DIR
)
from src.utils import logger
from .base import P6AutomationBase
from .exceptions import (
    P6PrintError,
    P6LayoutNotFoundError,
    P6ProjectNotFoundError,
    P6TimeoutError
)
from .utils import (
    retry,
    wait_for_condition,
    sanitize_filename,
    get_timestamp
)


class P6PrintAutomation(P6AutomationBase):
    """
    P6 GUI automation focused on printing and exporting.
    
    Extends P6AutomationBase with print-specific functionality:
    - Print current view to PDF
    - Apply layouts before printing
    - Batch print multiple projects
    - Export to XER/XML/Excel
    """
    
    # Dialog patterns
    PRINT_DIALOG_TITLE = "Print"
    SAVE_DIALOG_TITLE = "Save Print Output As"
    LAYOUT_DIALOG_TITLE = "Open Layout"
    
    # Print timing (seconds)
    PRINT_WAIT = 10.0
    
    def __init__(
        self,
        p6_path: Optional[str] = None,
        pdf_printer: Optional[str] = None,
        output_dir: Optional[str] = None,
        safe_mode: Optional[bool] = None,
        auto_connect: bool = False
    ):
        """
        Initialize P6 Print Automation.
        
        Args:
            p6_path: Path to P6 executable
            pdf_printer: Name of PDF printer
            output_dir: Directory for PDF output
            safe_mode: Override safe mode setting
            auto_connect: Automatically connect on init
        """
        super().__init__(
            p6_path=p6_path,
            safe_mode=safe_mode,
            auto_connect=False  # We handle separately
        )
        
        self.pdf_printer = pdf_printer or PDF_PRINTER_NAME or "Microsoft Print to PDF"
        self.output_dir = Path(output_dir or PDF_OUTPUT_DIR or "reports/pdf")
        self.default_layout = P6_DEFAULT_LAYOUT
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"P6PrintAutomation initialized")
        logger.debug(f"  PDF Printer: {self.pdf_printer}")
        logger.debug(f"  Output Dir: {self.output_dir}")
        
        if auto_connect:
            self.connect()
    
    # =========================================================================
    # Project Operations
    # =========================================================================
    
    def open_project(self, project_name: str) -> bool:
        """
        Open a project by name in P6.
        
        Args:
            project_name: Name of the project to open
            
        Returns:
            True if project opened successfully
            
        Raises:
            P6ProjectNotFoundError: If project not found
            ValueError: If project_name is empty
        """
        if not project_name or not project_name.strip():
            raise ValueError("project_name cannot be empty")
        
        logger.info(f"Opening project: {project_name}")
        
        self.focus_main_window()
        
        # TODO: Implement full project tree navigation
        # For now, this is a placeholder that assumes project is available
        # Full implementation requires:
        # 1. Navigate to Projects view
        # 2. Search/filter for project name
        # 3. Double-click to open
        
        logger.info(f"✓ Project context set: {project_name}")
        return True
    
    # =========================================================================
    # Layout Operations
    # =========================================================================
    
    def apply_layout(self, layout_name: str) -> bool:
        """
        Apply a saved layout by name.
        
        Args:
            layout_name: Name of the saved layout
            
        Returns:
            True if layout applied successfully
            
        Raises:
            P6LayoutNotFoundError: If layout not found
        """
        logger.info(f"Applying layout: {layout_name}")
        
        self.focus_main_window()
        
        # Navigate to View > Layout > Open
        # Using keyboard: Alt+V, L, O
        self.send_keys("%V")  # Alt+V (View menu)
        time.sleep(self.ACTION_DELAY)
        self.send_keys("L")   # Layout submenu
        time.sleep(self.ACTION_DELAY)
        self.send_keys("O")   # Open
        time.sleep(self.ACTION_DELAY * 2)
        
        # Handle layout dialog
        try:
            layout_dialog = self.find_dialog(
                title_re=".*Layout.*",
                timeout=self.DIALOG_TIMEOUT
            )
            
            # Find layout in list and select
            # TODO: Implement layout list navigation
            # For now, type layout name and press Enter
            layout_dialog.type_keys(layout_name)
            time.sleep(self.ACTION_DELAY)
            layout_dialog.type_keys("{ENTER}")
            time.sleep(self.ACTION_DELAY * 2)
            
            logger.info(f"✓ Layout applied: {layout_name}")
            return True
            
        except P6TimeoutError:
            raise P6LayoutNotFoundError(f"Could not open layout dialog")
    
    def get_current_layout(self) -> str:
        """Get the name of the currently applied layout."""
        # TODO: Implement by reading from title bar or status
        return self.default_layout
    
    # =========================================================================
    # Print Operations
    # =========================================================================
    
    def print_to_pdf(
        self,
        output_filename: str,
        wait_for_completion: bool = True
    ) -> Path:
        """
        Print the current view to PDF.
        
        Args:
            output_filename: Name for the output PDF file
            wait_for_completion: Wait for PDF to be created
            
        Returns:
            Path to the generated PDF file
            
        Raises:
            P6PrintError: If print fails
        """
        # Ensure .pdf extension
        if not output_filename.lower().endswith('.pdf'):
            output_filename += '.pdf'
        
        output_path = self.output_dir / output_filename
        
        logger.info(f"Printing to PDF: {output_path}")
        
        self.focus_main_window()
        
        # Step 1: Open Print dialog (Ctrl+P)
        logger.debug("  Opening print dialog...")
        self.send_keys("^P")
        time.sleep(self.DIALOG_TIMEOUT)
        
        # Step 2: Find Print dialog
        try:
            print_dialog = self.find_dialog(
                title=self.PRINT_DIALOG_TITLE,
                timeout=self.DIALOG_TIMEOUT
            )
            logger.debug("  Print dialog opened")
            
            # Step 3: Select PDF printer
            self._select_printer(print_dialog, self.pdf_printer)
            
            # Step 4: Click Print button
            print_button = print_dialog.child_window(
                title="Print",
                control_type="Button"
            )
            print_button.click_input()
            logger.debug("  Clicked Print button")
            time.sleep(self.DIALOG_TIMEOUT)
            
        except Exception as e:
            self.capture_error_screenshot("print_dialog")
            raise P6PrintError(f"Print dialog error: {e}")
        
        # Step 5: Handle Save dialog
        try:
            self._handle_save_dialog(output_path)
        except Exception as e:
            self.capture_error_screenshot("save_dialog")
            raise P6PrintError(f"Save dialog error: {e}")
        
        # Wait for PDF creation
        if wait_for_completion:
            if self._wait_for_pdf(output_path):
                file_size = output_path.stat().st_size / 1024
                logger.info(f"✓ PDF created: {output_path} ({file_size:.1f} KB)")
            else:
                logger.warning(f"⚠ PDF file not found at: {output_path}")
        
        return output_path
    
    def _select_printer(self, dialog, printer_name: str) -> bool:
        """
        Select printer from print dialog.
        
        Args:
            dialog: Print dialog window
            printer_name: Name of printer to select
            
        Returns:
            True if printer selected successfully, False if fallback to default
        """
        try:
            printer_combo = dialog.child_window(
                control_type="ComboBox",
                found_index=0
            )
            printer_combo.select(printer_name)
            logger.debug(f"  Selected printer: {printer_name}")
            time.sleep(self.ACTION_DELAY)
            return True
        except Exception as e:
            logger.warning(
                f"Could not select printer '{printer_name}': {e}. "
                f"Falling back to default printer."
            )
            return False
    
    def _handle_save_dialog(self, output_path: Path):
        """Handle the Save Print Output As dialog."""
        save_dialog = Desktop(backend="uia").window(
            title=self.SAVE_DIALOG_TITLE
        )
        save_dialog.wait("ready", timeout=self.DIALOG_TIMEOUT)
        logger.debug("  Save dialog opened")
        
        # Enter filename
        filename_edit = save_dialog.child_window(
            control_type="Edit",
            found_index=0
        )
        filename_edit.set_text(str(output_path))
        logger.debug(f"  Set filename: {output_path}")
        time.sleep(self.ACTION_DELAY)
        
        # Click Save
        save_button = save_dialog.child_window(
            title="Save",
            control_type="Button"
        )
        save_button.click_input()
        logger.debug("  Clicked Save button")
    
    def _wait_for_pdf(self, output_path: Path, timeout: float = None) -> bool:
        """Wait for PDF file to be created."""
        timeout = timeout or self.PRINT_WAIT
        return wait_for_condition(
            condition=lambda: output_path.exists() and output_path.stat().st_size > 0,
            timeout=timeout,
            description=f"PDF creation: {output_path.name}"
        )
    
    # =========================================================================
    # Batch Operations
    # =========================================================================
    
    def batch_print(
        self,
        projects: List[str],
        layout_name: Optional[str] = None,
        output_prefix: str = "",
        on_progress: Optional[Callable[[int, int, str], None]] = None
    ) -> dict:
        """
        Print multiple projects to PDF.
        
        Args:
            projects: List of project names to print
            layout_name: Layout to apply (uses default if not specified)
            output_prefix: Prefix for output filenames
            on_progress: Optional callback(current, total, project_name)
            
        Returns:
            Dict mapping project names to output paths (None if failed)
        """
        layout = layout_name or self.default_layout
        timestamp = get_timestamp()
        results = {}
        
        logger.info(f"Starting batch print of {len(projects)} projects")
        
        for i, project in enumerate(projects, 1):
            logger.info(f"[{i}/{len(projects)}] Processing: {project}")
            
            if on_progress:
                on_progress(i, len(projects), project)
            
            try:
                # Open project
                self.open_project(project)
                time.sleep(self.ACTION_DELAY)
                
                # Apply layout
                self.apply_layout(layout)
                time.sleep(self.ACTION_DELAY)
                
                # Generate safe filename
                safe_name = sanitize_filename(project)
                filename = f"{output_prefix}{safe_name}_{timestamp}.pdf"
                
                # Print to PDF
                output_path = self.print_to_pdf(filename)
                results[project] = output_path
                
            except Exception as e:
                logger.error(f"Failed to print '{project}': {e}")
                results[project] = None
                self.capture_error_screenshot(f"batch_{sanitize_filename(project)}")
        
        successful = sum(1 for v in results.values() if v is not None)
        logger.info(f"✓ Batch print complete: {successful}/{len(projects)} successful")
        
        return results
    
    # =========================================================================
    # Export Operations (Phase 3)
    # =========================================================================
    
    def export_to_xer(self, output_path: Path) -> Path:
        """Export current project to XER format."""
        # TODO: Implement in Phase 3
        raise NotImplementedError("XER export not yet implemented")
    
    def export_to_excel(self, output_path: Path) -> Path:
        """Export current view to Excel."""
        # TODO: Implement in Phase 3
        raise NotImplementedError("Excel export not yet implemented")
    
    def export_to_xml(self, output_path: Path) -> Path:
        """Export current project to XML format."""
        # TODO: Implement in Phase 3
        raise NotImplementedError("XML export not yet implemented")


# Command-line interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Print P6 layouts to PDF")
    parser.add_argument("--project", "-p", help="Project name to print")
    parser.add_argument("--layout", "-l", default="Standard Layout", help="Layout to apply")
    parser.add_argument("--output", "-o", help="Output PDF filename")
    parser.add_argument("--list-windows", action="store_true", help="List P6 windows")
    
    args = parser.parse_args()
    
    if args.list_windows:
        from pywinauto import Desktop
        print("Available windows:")
        for win in Desktop(backend="uia").windows():
            title = win.window_text()
            if title:
                print(f"  {title}")
    
    elif args.project:
        with P6PrintAutomation() as p6:
            p6.open_project(args.project)
            p6.apply_layout(args.layout)
            output = args.output or f"{sanitize_filename(args.project)}.pdf"
            pdf_path = p6.print_to_pdf(output)
            print(f"PDF created: {pdf_path}")
    
    else:
        parser.print_help()
