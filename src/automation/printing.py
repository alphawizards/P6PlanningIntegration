#!/usr/bin/env python3
"""
P6 Printing Module.

Provides comprehensive print and export automation for P6 Professional:
- Print preview navigation
- Page setup (orientation, size, margins)
- PDF printing via Microsoft Print to PDF
- Print dialog handling
"""

import time
from pathlib import Path
from typing import Optional, Dict, Tuple
from enum import Enum

try:
    from pywinauto import Desktop
    from pywinauto.findwindows import ElementNotFoundError
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

from src.config import PDF_PRINTER_NAME, PDF_OUTPUT_DIR
from src.utils import logger
from ..exceptions import (
    P6PrintError,
    P6TimeoutError,
    P6WindowNotFoundError
)
from ..utils import (
    retry,
    wait_for_condition,
    sanitize_filename,
    get_timestamp
)


class PageOrientation(Enum):
    """Page orientation options."""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class PageSize(Enum):
    """Common paper sizes."""
    LETTER = "Letter"
    LEGAL = "Legal"
    A4 = "A4"
    A3 = "A3"
    TABLOID = "Tabloid"


class P6PrintManager:
    """
    Manages P6 printing operations.
    
    Provides:
    - Print preview navigation
    - Page setup configuration
    - PDF printing
    - Print job monitoring
    
    Warning:
        This class is NOT thread-safe.
    """
    
    # Dialog patterns
    PRINT_PREVIEW_TITLE = "Print Preview"
    PRINT_DIALOG_TITLE = "Print"
    PAGE_SETUP_TITLE = "Page Setup"
    SAVE_DIALOG_TITLE = "Save Print Output As"
    
    # Timing
    DIALOG_TIMEOUT = 15
    PRINT_TIMEOUT = 30
    ACTION_DELAY = 0.5
    
    def __init__(
        self,
        main_window,
        pdf_printer: Optional[str] = None,
        output_dir: Optional[str] = None
    ):
        """
        Initialize print manager.
        
        Args:
            main_window: P6 main window wrapper
            pdf_printer: Name of PDF printer
            output_dir: Directory for PDF output
        """
        self._window = main_window
        self.pdf_printer = pdf_printer or PDF_PRINTER_NAME or "Microsoft Print to PDF"
        self.output_dir = Path(output_dir or PDF_OUTPUT_DIR or "reports/pdf")
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Track state
        self._in_print_preview = False
        
        logger.debug(f"P6PrintManager initialized")
        logger.debug(f"  PDF Printer: {self.pdf_printer}")
        logger.debug(f"  Output Dir: {self.output_dir}")
    
    # =========================================================================
    # Print Preview
    # =========================================================================
    
    def open_print_preview(self) -> bool:
        """
        Open P6 Print Preview.
        
        Returns:
            True if print preview opened successfully
        """
        logger.info("Opening print preview...")
        
        try:
            self._window.set_focus()
            time.sleep(self.ACTION_DELAY)
            
            # Use menu: File -> Print Preview
            self._window.menu_select("File->Print Preview")
            time.sleep(self.DIALOG_TIMEOUT)
            
            # Verify print preview window opened
            preview = self._find_print_preview_window()
            if preview:
                self._in_print_preview = True
                logger.info("✓ Print preview opened")
                return True
            else:
                raise P6PrintError("Print preview window not found")
                
        except Exception as e:
            raise P6PrintError(f"Failed to open print preview: {e}")
    
    def close_print_preview(self) -> bool:
        """
        Close print preview and return to main window.
        
        Returns:
            True if closed successfully
        """
        logger.debug("Closing print preview...")
        
        try:
            preview = self._find_print_preview_window()
            if preview:
                preview.close()
                time.sleep(self.ACTION_DELAY)
            
            self._in_print_preview = False
            logger.info("✓ Print preview closed")
            return True
            
        except Exception as e:
            logger.warning(f"Error closing print preview: {e}")
            return False
    
    def _find_print_preview_window(self):
        """Find the print preview window."""
        try:
            # Print preview may be part of main app or separate window
            preview = Desktop(backend="uia").window(
                title_re=f".*{self.PRINT_PREVIEW_TITLE}.*"
            )
            if preview.exists():
                return preview
        except Exception:
            pass
        
        # Try as child of main window
        try:
            return self._window.child_window(
                title_re=f".*{self.PRINT_PREVIEW_TITLE}.*"
            )
        except Exception:
            return None
    
    # =========================================================================
    # Page Setup
    # =========================================================================
    
    def open_page_setup(self) -> bool:
        """
        Open Page Setup dialog.
        
        Returns:
            True if dialog opened
        """
        logger.debug("Opening page setup...")
        
        try:
            self._window.set_focus()
            time.sleep(self.ACTION_DELAY)
            
            # File -> Page Setup
            self._window.menu_select("File->Page Setup...")
            time.sleep(self.ACTION_DELAY * 2)
            
            # Find page setup dialog
            dialog = Desktop(backend="uia").window(
                title_re=f".*{self.PAGE_SETUP_TITLE}.*"
            )
            dialog.wait("ready", timeout=self.DIALOG_TIMEOUT)
            
            logger.info("✓ Page setup dialog opened")
            return True
            
        except Exception as e:
            raise P6PrintError(f"Failed to open page setup: {e}")
    
    def set_page_orientation(self, orientation: PageOrientation) -> bool:
        """
        Set page orientation.
        
        Args:
            orientation: PageOrientation.PORTRAIT or PageOrientation.LANDSCAPE
            
        Returns:
            True if set successfully
        """
        logger.info(f"Setting orientation: {orientation.value}")
        
        try:
            dialog = Desktop(backend="uia").window(
                title_re=f".*{self.PAGE_SETUP_TITLE}.*"
            )
            
            if not dialog.exists():
                # Open page setup first
                self.open_page_setup()
                dialog = Desktop(backend="uia").window(
                    title_re=f".*{self.PAGE_SETUP_TITLE}.*"
                )
            
            # Find orientation radio buttons
            if orientation == PageOrientation.LANDSCAPE:
                radio = dialog.child_window(
                    title_re=".*Landscape.*",
                    control_type="RadioButton"
                )
            else:
                radio = dialog.child_window(
                    title_re=".*Portrait.*",
                    control_type="RadioButton"
                )
            
            radio.click_input()
            time.sleep(self.ACTION_DELAY)
            
            logger.info(f"✓ Orientation set to {orientation.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set orientation: {e}")
            return False
    
    def set_page_size(self, size: PageSize) -> bool:
        """
        Set page/paper size.
        
        Args:
            size: PageSize enum value
            
        Returns:
            True if set successfully
        """
        logger.info(f"Setting page size: {size.value}")
        
        try:
            dialog = Desktop(backend="uia").window(
                title_re=f".*{self.PAGE_SETUP_TITLE}.*"
            )
            
            if not dialog.exists():
                self.open_page_setup()
                dialog = Desktop(backend="uia").window(
                    title_re=f".*{self.PAGE_SETUP_TITLE}.*"
                )
            
            # Find paper size combo box
            paper_combo = dialog.child_window(
                control_type="ComboBox",
                found_index=0
            )
            paper_combo.select(size.value)
            time.sleep(self.ACTION_DELAY)
            
            logger.info(f"✓ Page size set to {size.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set page size: {e}")
            return False
    
    def apply_page_setup(self) -> bool:
        """
        Apply and close page setup dialog.
        
        Returns:
            True if applied successfully
        """
        try:
            dialog = Desktop(backend="uia").window(
                title_re=f".*{self.PAGE_SETUP_TITLE}.*"
            )
            
            if dialog.exists():
                ok_button = dialog.child_window(
                    title="OK",
                    control_type="Button"
                )
                ok_button.click_input()
                time.sleep(self.ACTION_DELAY)
                logger.info("✓ Page setup applied")
                return True
                
        except Exception as e:
            logger.error(f"Failed to apply page setup: {e}")
        
        return False
    
    def cancel_page_setup(self) -> bool:
        """Cancel and close page setup dialog."""
        try:
            dialog = Desktop(backend="uia").window(
                title_re=f".*{self.PAGE_SETUP_TITLE}.*"
            )
            
            if dialog.exists():
                cancel_button = dialog.child_window(
                    title="Cancel",
                    control_type="Button"
                )
                cancel_button.click_input()
                return True
                
        except Exception:
            pass
        
        return False
    
    # =========================================================================
    # Print to PDF
    # =========================================================================
    
    def print_to_pdf(
        self,
        output_filename: str,
        orientation: Optional[PageOrientation] = None,
        page_size: Optional[PageSize] = None,
        wait_for_completion: bool = True
    ) -> Path:
        """
        Print current view to PDF.
        
        Args:
            output_filename: Name for output PDF file
            orientation: Optional page orientation
            page_size: Optional paper size
            wait_for_completion: Wait for PDF to be created
            
        Returns:
            Path to generated PDF
            
        Raises:
            P6PrintError: If print fails
        """
        # Ensure .pdf extension
        if not output_filename.lower().endswith('.pdf'):
            output_filename += '.pdf'
        
        output_path = self.output_dir / output_filename
        
        logger.info(f"Printing to PDF: {output_path}")
        
        # Apply page setup if specified
        if orientation or page_size:
            self.open_page_setup()
            if orientation:
                self.set_page_orientation(orientation)
            if page_size:
                self.set_page_size(page_size)
            self.apply_page_setup()
        
        # Open print dialog
        self._window.set_focus()
        time.sleep(self.ACTION_DELAY)
        
        # Ctrl+P to open print dialog
        self._window.type_keys("^P")
        time.sleep(self.DIALOG_TIMEOUT)
        
        # Handle print dialog
        try:
            self._handle_print_dialog(output_path)
        except Exception as e:
            raise P6PrintError(f"Print dialog error: {e}")
        
        # Wait for PDF
        if wait_for_completion:
            if self._wait_for_pdf(output_path):
                file_size = output_path.stat().st_size / 1024
                logger.info(f"✓ PDF created: {output_path} ({file_size:.1f} KB)")
            else:
                logger.warning(f"⚠ PDF may not have been created: {output_path}")
        
        return output_path
    
    def _handle_print_dialog(self, output_path: Path):
        """Handle the print dialog."""
        print_dialog = Desktop(backend="uia").window(
            title=self.PRINT_DIALOG_TITLE
        )
        print_dialog.wait("ready", timeout=self.DIALOG_TIMEOUT)
        logger.debug("Print dialog opened")
        
        # Select PDF printer
        self._select_pdf_printer(print_dialog)
        
        # Click Print button
        print_button = print_dialog.child_window(
            title="Print",
            control_type="Button"
        )
        print_button.click_input()
        logger.debug("Clicked Print button")
        time.sleep(self.DIALOG_TIMEOUT)
        
        # Handle Save dialog
        self._handle_save_dialog(output_path)
    
    def _select_pdf_printer(self, dialog) -> bool:
        """Select PDF printer in print dialog."""
        try:
            printer_combo = dialog.child_window(
                control_type="ComboBox",
                found_index=0
            )
            printer_combo.select(self.pdf_printer)
            logger.debug(f"Selected printer: {self.pdf_printer}")
            time.sleep(self.ACTION_DELAY)
            return True
        except Exception as e:
            logger.warning(f"Could not select printer '{self.pdf_printer}': {e}")
            return False
    
    def _handle_save_dialog(self, output_path: Path):
        """Handle the Save Print Output As dialog."""
        save_dialog = Desktop(backend="uia").window(
            title=self.SAVE_DIALOG_TITLE
        )
        save_dialog.wait("ready", timeout=self.DIALOG_TIMEOUT)
        logger.debug("Save dialog opened")
        
        # Enter filename
        filename_edit = save_dialog.child_window(
            control_type="Edit",
            found_index=0
        )
        filename_edit.set_text(str(output_path))
        logger.debug(f"Set filename: {output_path}")
        time.sleep(self.ACTION_DELAY)
        
        # Click Save
        save_button = save_dialog.child_window(
            title="Save",
            control_type="Button"
        )
        save_button.click_input()
        logger.debug("Clicked Save button")
    
    def _wait_for_pdf(self, output_path: Path, timeout: float = None) -> bool:
        """Wait for PDF file to be created."""
        timeout = timeout or self.PRINT_TIMEOUT
        
        return wait_for_condition(
            condition=lambda: output_path.exists() and output_path.stat().st_size > 0,
            timeout=timeout,
            poll_interval=1.0,
            description=f"PDF creation: {output_path.name}"
        )
    
    # =========================================================================
    # Quick Print Methods
    # =========================================================================
    
    def quick_print_pdf(
        self,
        output_filename: str,
        landscape: bool = True
    ) -> Path:
        """
        Quick print to PDF with common settings.
        
        Args:
            output_filename: Output filename
            landscape: Use landscape orientation (default True for Gantt)
            
        Returns:
            Path to generated PDF
        """
        orientation = PageOrientation.LANDSCAPE if landscape else PageOrientation.PORTRAIT
        return self.print_to_pdf(
            output_filename=output_filename,
            orientation=orientation
        )
    
    def print_gantt_pdf(
        self,
        output_filename: str,
        page_size: PageSize = PageSize.A3
    ) -> Path:
        """
        Print Gantt chart to PDF with optimal settings.
        
        Args:
            output_filename: Output filename
            page_size: Paper size (A3 recommended for Gantt)
            
        Returns:
            Path to generated PDF
        """
        return self.print_to_pdf(
            output_filename=output_filename,
            orientation=PageOrientation.LANDSCAPE,
            page_size=page_size
        )
