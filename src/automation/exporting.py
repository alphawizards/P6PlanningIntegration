#!/usr/bin/env python3
"""
P6 Export Module.

Provides export automation for P6 Professional:
- XER export (Primavera native format)
- Excel/Spreadsheet export
- XML export
- CSV export
"""

import time
from pathlib import Path
from typing import Optional, List, Dict
from enum import Enum

try:
    from pywinauto import Desktop
    from pywinauto.findwindows import ElementNotFoundError
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

from src.config import PDF_OUTPUT_DIR
from src.utils import logger
from .exceptions import (
    P6ExportError,
    P6TimeoutError,
    P6WindowNotFoundError
)
from .utils import (
    retry,
    wait_for_condition,
    sanitize_filename,
    get_timestamp
)


class ExportFormat(Enum):
    """Supported export formats."""
    XER = "xer"
    XML = "xml"
    EXCEL = "xlsx"
    CSV = "csv"
    MPX = "mpx"


class P6ExportManager:
    """
    Manages P6 export operations.
    
    Provides:
    - XER export (full project data)
    - XML export
    - Excel/Spreadsheet export
    - Export wizard automation
    
    Warning:
        This class is NOT thread-safe.
    """
    
    # Dialog patterns
    EXPORT_WIZARD_TITLE = "Export"
    EXPORT_FORMAT_TITLE = "Select Export Type"
    SAVE_DIALOG_TITLE = "Save As"
    
    # Export types in P6 wizard
    EXPORT_TYPES = {
        ExportFormat.XER: "Primavera PM",
        ExportFormat.XML: "Primavera XML",
        ExportFormat.EXCEL: "Spreadsheet",
        ExportFormat.CSV: "Spreadsheet",
        ExportFormat.MPX: "Microsoft Project"
    }
    
    # Timing
    DIALOG_TIMEOUT = 15
    EXPORT_TIMEOUT = 60  # Large projects take time
    ACTION_DELAY = 0.5
    
    def __init__(
        self,
        main_window,
        output_dir: Optional[str] = None
    ):
        """
        Initialize export manager.
        
        Args:
            main_window: P6 main window wrapper
            output_dir: Directory for exports
        """
        self._window = main_window
        self.output_dir = Path(output_dir or PDF_OUTPUT_DIR or "reports/exports")
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"P6ExportManager initialized")
        logger.debug(f"  Output Dir: {self.output_dir}")
    
    # =========================================================================
    # Export Menu
    # =========================================================================
    
    def open_export_wizard(self) -> bool:
        """
        Open the P6 Export wizard.
        
        Returns:
            True if wizard opened
        """
        logger.info("Opening export wizard...")
        
        try:
            self._window.set_focus()
            time.sleep(self.ACTION_DELAY)
            
            # Tools -> Export
            self._window.menu_select("File->Export...")
            time.sleep(self.ACTION_DELAY * 2)
            
            # Wait for export wizard
            wizard = Desktop(backend="uia").window(
                title_re=f".*{self.EXPORT_WIZARD_TITLE}.*"
            )
            wizard.wait("ready", timeout=self.DIALOG_TIMEOUT)
            
            logger.info("✓ Export wizard opened")
            return True
            
        except Exception as e:
            raise P6ExportError(f"Failed to open export wizard: {e}")
    
    # =========================================================================
    # XER Export
    # =========================================================================
    
    def export_to_xer(
        self,
        output_filename: str,
        include_baselines: bool = True,
        include_resources: bool = True
    ) -> Path:
        """
        Export project to XER format.
        
        Args:
            output_filename: Output filename (without extension)
            include_baselines: Include baseline data
            include_resources: Include resource data
            
        Returns:
            Path to exported XER file
        """
        if not output_filename.lower().endswith('.xer'):
            output_filename += '.xer'
        
        output_path = self.output_dir / output_filename
        
        logger.info(f"Exporting to XER: {output_path}")
        
        try:
            # Open export wizard
            self.open_export_wizard()
            
            # Select Primavera PM (XER) format
            self._select_export_type(ExportFormat.XER)
            
            # Navigate wizard
            self._click_next()
            time.sleep(self.ACTION_DELAY)
            
            # Project selection (usually pre-selected)
            self._click_next()
            time.sleep(self.ACTION_DELAY)
            
            # Export options
            # TODO: Handle baseline/resource checkboxes
            self._click_next()
            time.sleep(self.ACTION_DELAY)
            
            # File selection
            self._set_export_path(output_path)
            
            # Complete export
            self._click_finish()
            
            # Wait for export
            if self._wait_for_export(output_path):
                file_size = output_path.stat().st_size / 1024
                logger.info(f"✓ XER exported: {output_path} ({file_size:.1f} KB)")
            else:
                logger.warning(f"⚠ XER may not have been exported: {output_path}")
            
            return output_path
            
        except Exception as e:
            raise P6ExportError(f"XER export failed: {e}")
    
    # =========================================================================
    # XML Export
    # =========================================================================
    
    def export_to_xml(
        self,
        output_filename: str
    ) -> Path:
        """
        Export project to Primavera XML format.
        
        Args:
            output_filename: Output filename
            
        Returns:
            Path to exported XML file
        """
        if not output_filename.lower().endswith('.xml'):
            output_filename += '.xml'
        
        output_path = self.output_dir / output_filename
        
        logger.info(f"Exporting to XML: {output_path}")
        
        try:
            self.open_export_wizard()
            self._select_export_type(ExportFormat.XML)
            
            # Navigate wizard
            self._click_next()
            time.sleep(self.ACTION_DELAY)
            self._click_next()
            time.sleep(self.ACTION_DELAY)
            
            self._set_export_path(output_path)
            self._click_finish()
            
            if self._wait_for_export(output_path):
                file_size = output_path.stat().st_size / 1024
                logger.info(f"✓ XML exported: {output_path} ({file_size:.1f} KB)")
            
            return output_path
            
        except Exception as e:
            raise P6ExportError(f"XML export failed: {e}")
    
    # =========================================================================
    # Excel Export
    # =========================================================================
    
    def export_to_excel(
        self,
        output_filename: str,
        include_headers: bool = True
    ) -> Path:
        """
        Export current view to Excel/Spreadsheet.
        
        Args:
            output_filename: Output filename
            include_headers: Include column headers
            
        Returns:
            Path to exported Excel file
        """
        if not output_filename.lower().endswith(('.xlsx', '.xls')):
            output_filename += '.xlsx'
        
        output_path = self.output_dir / output_filename
        
        logger.info(f"Exporting to Excel: {output_path}")
        
        try:
            self.open_export_wizard()
            self._select_export_type(ExportFormat.EXCEL)
            
            # Navigate wizard
            self._click_next()
            time.sleep(self.ACTION_DELAY)
            
            # Select spreadsheet format options
            self._click_next()
            time.sleep(self.ACTION_DELAY)
            
            self._set_export_path(output_path)
            self._click_finish()
            
            if self._wait_for_export(output_path):
                file_size = output_path.stat().st_size / 1024
                logger.info(f"✓ Excel exported: {output_path} ({file_size:.1f} KB)")
            
            return output_path
            
        except Exception as e:
            raise P6ExportError(f"Excel export failed: {e}")
    
    # =========================================================================
    # Wizard Helpers
    # =========================================================================
    
    def _select_export_type(self, format: ExportFormat) -> bool:
        """Select export type in wizard."""
        type_name = self.EXPORT_TYPES.get(format, format.value)
        logger.debug(f"Selecting export type: {type_name}")
        
        try:
            wizard = Desktop(backend="uia").window(
                title_re=f".*{self.EXPORT_WIZARD_TITLE}.*"
            )
            
            # Find and select the export type in list
            type_list = wizard.child_window(
                control_type="List"
            )
            
            # Try to find the item
            try:
                item = type_list.child_window(
                    title_re=f".*{type_name}.*"
                )
                item.click_input()
            except Exception:
                # Try by select
                type_list.select(type_name)
            
            time.sleep(self.ACTION_DELAY)
            return True
            
        except Exception as e:
            logger.error(f"Failed to select export type: {e}")
            return False
    
    def _click_next(self) -> bool:
        """Click Next button in wizard."""
        try:
            wizard = Desktop(backend="uia").window(
                title_re=f".*{self.EXPORT_WIZARD_TITLE}.*"
            )
            next_button = wizard.child_window(
                title_re=".*Next.*|.*>.*",
                control_type="Button"
            )
            next_button.click_input()
            return True
        except Exception as e:
            logger.debug(f"Next button error: {e}")
            return False
    
    def _click_finish(self) -> bool:
        """Click Finish button in wizard."""
        try:
            wizard = Desktop(backend="uia").window(
                title_re=f".*{self.EXPORT_WIZARD_TITLE}.*"
            )
            finish_button = wizard.child_window(
                title_re=".*Finish.*|.*Export.*",
                control_type="Button"
            )
            finish_button.click_input()
            time.sleep(self.ACTION_DELAY)
            return True
        except Exception as e:
            logger.debug(f"Finish button error: {e}")
            return False
    
    def _set_export_path(self, output_path: Path) -> bool:
        """Set export file path in wizard."""
        try:
            wizard = Desktop(backend="uia").window(
                title_re=f".*{self.EXPORT_WIZARD_TITLE}.*"
            )
            
            # Find file path edit box
            path_edit = wizard.child_window(
                control_type="Edit"
            )
            path_edit.set_text(str(output_path))
            time.sleep(self.ACTION_DELAY)
            return True
            
        except Exception as e:
            logger.error(f"Failed to set export path: {e}")
            return False
    
    def _wait_for_export(self, output_path: Path, timeout: float = None) -> bool:
        """Wait for export file to be created."""
        timeout = timeout or self.EXPORT_TIMEOUT
        
        return wait_for_condition(
            condition=lambda: output_path.exists() and output_path.stat().st_size > 0,
            timeout=timeout,
            poll_interval=1.0,
            description=f"Export: {output_path.name}"
        )
    
    def cancel_export(self) -> bool:
        """Cancel the export wizard."""
        try:
            wizard = Desktop(backend="uia").window(
                title_re=f".*{self.EXPORT_WIZARD_TITLE}.*"
            )
            if wizard.exists():
                cancel = wizard.child_window(
                    title="Cancel",
                    control_type="Button"
                )
                cancel.click_input()
                return True
        except Exception:
            pass
        return False
    
    # =========================================================================
    # Batch Export
    # =========================================================================
    
    def batch_export(
        self,
        format: ExportFormat,
        projects: List[str],
        output_prefix: str = ""
    ) -> Dict[str, Optional[Path]]:
        """
        Export multiple projects.
        
        Args:
            format: Export format
            projects: List of project names
            output_prefix: Prefix for filenames
            
        Returns:
            Dict mapping project names to output paths
        """
        results = {}
        timestamp = get_timestamp()
        
        logger.info(f"Batch exporting {len(projects)} projects to {format.value}")
        
        for project in projects:
            safe_name = sanitize_filename(project)
            extension = format.value
            filename = f"{output_prefix}{safe_name}_{timestamp}.{extension}"
            
            try:
                if format == ExportFormat.XER:
                    path = self.export_to_xer(filename)
                elif format == ExportFormat.XML:
                    path = self.export_to_xml(filename)
                elif format in (ExportFormat.EXCEL, ExportFormat.CSV):
                    path = self.export_to_excel(filename)
                else:
                    raise P6ExportError(f"Unsupported format: {format}")
                
                results[project] = path
                
            except Exception as e:
                logger.error(f"Export failed for '{project}': {e}")
                results[project] = None
        
        successful = sum(1 for v in results.values() if v is not None)
        logger.info(f"✓ Batch export complete: {successful}/{len(projects)}")
        
        return results
