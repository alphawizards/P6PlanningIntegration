#!/usr/bin/env python3
"""
P6 Batch Operations Module.

Provides batch processing capabilities:
- Batch print to PDF
- Batch export (XER, XML, Excel)
- Batch schedule operations
- Progress tracking and error recovery
"""

import time
from pathlib import Path
from typing import Optional, List, Dict, Callable, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from src.utils import logger
from src.config import PDF_OUTPUT_DIR
from ..exceptions import (
    P6PrintError,
    P6ExportError,
    P6ScheduleError,
    P6ProjectNotFoundError
)
from ..utils import (
    sanitize_filename,
    get_timestamp
)


class BatchStatus(Enum):
    """Status of batch operation."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchResult:
    """Result of a single batch item."""
    item_name: str
    status: BatchStatus
    output_path: Optional[Path] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class BatchSummary:
    """Summary of batch operation."""
    total: int = 0
    successful: int = 0
    failed: int = 0
    cancelled: int = 0
    results: List[BatchResult] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def duration(self) -> float:
        """Get total duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.total == 0:
            return 0.0
        return (self.successful / self.total) * 100


class P6BatchProcessor:
    """
    Orchestrates batch operations across multiple projects.
    
    Provides:
    - Batch print to PDF
    - Batch export
    - Batch schedule
    - Progress callbacks
    - Error recovery
    
    Warning:
        Batch operations can take significant time.
        Use progress callbacks to monitor status.
    """
    
    # Timing
    INTER_OPERATION_DELAY = 2.0  # Delay between projects
    
    def __init__(
        self,
        project_manager,
        layout_manager,
        print_manager=None,
        export_manager=None,
        schedule_manager=None,
        output_dir: Optional[str] = None
    ):
        """
        Initialize batch processor.
        
        Args:
            project_manager: P6ProjectManager instance
            layout_manager: P6LayoutManager instance
            print_manager: Optional P6PrintManager instance
            export_manager: Optional P6ExportManager instance
            schedule_manager: Optional P6ScheduleManager instance
            output_dir: Output directory for batch results
        """
        self.projects = project_manager
        self.layouts = layout_manager
        self.printer = print_manager
        self.exporter = export_manager
        self.scheduler = schedule_manager
        self.output_dir = Path(output_dir or PDF_OUTPUT_DIR or "reports/batch")
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._cancelled = False
        
        logger.debug("P6BatchProcessor initialized")
    
    def cancel(self):
        """Cancel the current batch operation."""
        self._cancelled = True
        logger.warning("Batch operation cancelled")
    
    def _reset(self):
        """Reset state for new batch."""
        self._cancelled = False
    
    # =========================================================================
    # Batch Print
    # =========================================================================
    
    def batch_print(
        self,
        project_names: List[str],
        layout_name: str,
        output_prefix: str = "",
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        on_error: Optional[Callable[[str, Exception], bool]] = None
    ) -> BatchSummary:
        """
        Print multiple projects to PDF.
        
        Args:
            project_names: List of project names
            layout_name: Layout to apply before printing
            output_prefix: Prefix for output filenames
            on_progress: Callback(current, total, project_name)
            on_error: Callback(project_name, exception) -> continue?
            
        Returns:
            BatchSummary with results
        """
        if not self.printer:
            raise ValueError("P6PrintManager required for batch print")
        
        self._reset()
        summary = BatchSummary(
            total=len(project_names),
            start_time=datetime.now()
        )
        
        timestamp = get_timestamp()
        logger.info(f"Starting batch print: {len(project_names)} projects")
        
        for i, project_name in enumerate(project_names, 1):
            if self._cancelled:
                summary.cancelled = len(project_names) - i + 1
                break
            
            result = BatchResult(item_name=project_name, status=BatchStatus.RUNNING)
            start = datetime.now()
            
            if on_progress:
                on_progress(i, len(project_names), project_name)
            
            try:
                # Open project
                self.projects.open_project(project_name)
                time.sleep(self.INTER_OPERATION_DELAY)
                
                # Apply layout
                self.layouts.open_layout(layout_name)
                time.sleep(self.INTER_OPERATION_DELAY / 2)
                
                # Generate filename
                safe_name = sanitize_filename(project_name)
                filename = f"{output_prefix}{safe_name}_{timestamp}.pdf"
                output_path = self.output_dir / filename
                
                # Print
                self.printer.print_to_pdf(filename)
                
                result.status = BatchStatus.COMPLETED
                result.output_path = output_path
                summary.successful += 1
                logger.info(f"  [{i}/{len(project_names)}] ✓ {project_name}")
                
            except Exception as e:
                result.status = BatchStatus.FAILED
                result.error = str(e)
                summary.failed += 1
                logger.error(f"  [{i}/{len(project_names)}] ✗ {project_name}: {e}")
                
                # Ask error handler if we should continue
                if on_error and not on_error(project_name, e):
                    self._cancelled = True
            
            result.duration_seconds = (datetime.now() - start).total_seconds()
            summary.results.append(result)
            
            time.sleep(self.INTER_OPERATION_DELAY)
        
        summary.end_time = datetime.now()
        logger.info(f"Batch print complete: {summary.successful}/{summary.total} successful")
        
        return summary
    
    # =========================================================================
    # Batch Export
    # =========================================================================
    
    def batch_export(
        self,
        project_names: List[str],
        format: str = "xer",
        output_prefix: str = "",
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        on_error: Optional[Callable[[str, Exception], bool]] = None
    ) -> BatchSummary:
        """
        Export multiple projects.
        
        Args:
            project_names: List of project names
            format: Export format (xer, xml, xlsx)
            output_prefix: Prefix for output filenames
            on_progress: Progress callback
            on_error: Error callback
            
        Returns:
            BatchSummary with results
        """
        if not self.exporter:
            raise ValueError("P6ExportManager required for batch export")
        
        self._reset()
        summary = BatchSummary(
            total=len(project_names),
            start_time=datetime.now()
        )
        
        timestamp = get_timestamp()
        logger.info(f"Starting batch export ({format}): {len(project_names)} projects")
        
        for i, project_name in enumerate(project_names, 1):
            if self._cancelled:
                summary.cancelled = len(project_names) - i + 1
                break
            
            result = BatchResult(item_name=project_name, status=BatchStatus.RUNNING)
            start = datetime.now()
            
            if on_progress:
                on_progress(i, len(project_names), project_name)
            
            try:
                # Open project
                self.projects.open_project(project_name)
                time.sleep(self.INTER_OPERATION_DELAY)
                
                # Generate filename
                safe_name = sanitize_filename(project_name)
                filename = f"{output_prefix}{safe_name}_{timestamp}.{format}"
                
                # Export
                if format.lower() == "xer":
                    output_path = self.exporter.export_to_xer(filename)
                elif format.lower() == "xml":
                    output_path = self.exporter.export_to_xml(filename)
                else:
                    output_path = self.exporter.export_to_excel(filename)
                
                result.status = BatchStatus.COMPLETED
                result.output_path = output_path
                summary.successful += 1
                
            except Exception as e:
                result.status = BatchStatus.FAILED
                result.error = str(e)
                summary.failed += 1
                
                if on_error and not on_error(project_name, e):
                    self._cancelled = True
            
            result.duration_seconds = (datetime.now() - start).total_seconds()
            summary.results.append(result)
            
            time.sleep(self.INTER_OPERATION_DELAY)
        
        summary.end_time = datetime.now()
        logger.info(f"Batch export complete: {summary.successful}/{summary.total}")
        
        return summary
    
    # =========================================================================
    # Batch Schedule
    # =========================================================================
    
    def batch_schedule(
        self,
        project_names: List[str],
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        on_error: Optional[Callable[[str, Exception], bool]] = None
    ) -> BatchSummary:
        """
        Schedule multiple projects (F9).
        
        Args:
            project_names: List of project names
            on_progress: Progress callback
            on_error: Error callback
            
        Returns:
            BatchSummary with results
        """
        if not self.scheduler:
            raise ValueError("P6ScheduleManager required for batch schedule")
        
        self._reset()
        summary = BatchSummary(
            total=len(project_names),
            start_time=datetime.now()
        )
        
        logger.info(f"Starting batch schedule: {len(project_names)} projects")
        
        for i, project_name in enumerate(project_names, 1):
            if self._cancelled:
                summary.cancelled = len(project_names) - i + 1
                break
            
            result = BatchResult(item_name=project_name, status=BatchStatus.RUNNING)
            start = datetime.now()
            
            if on_progress:
                on_progress(i, len(project_names), project_name)
            
            try:
                # Open project
                self.projects.open_project(project_name)
                time.sleep(self.INTER_OPERATION_DELAY)
                
                # Schedule (F9)
                self.scheduler.schedule_project()
                
                result.status = BatchStatus.COMPLETED
                summary.successful += 1
                
            except Exception as e:
                result.status = BatchStatus.FAILED
                result.error = str(e)
                summary.failed += 1
                
                if on_error and not on_error(project_name, e):
                    self._cancelled = True
            
            result.duration_seconds = (datetime.now() - start).total_seconds()
            summary.results.append(result)
            
            time.sleep(self.INTER_OPERATION_DELAY)
        
        summary.end_time = datetime.now()
        logger.info(f"Batch schedule complete: {summary.successful}/{summary.total}")
        
        return summary
    
    # =========================================================================
    # Combined Operations
    # =========================================================================
    
    def batch_schedule_and_print(
        self,
        project_names: List[str],
        layout_name: str,
        on_progress: Optional[Callable[[int, int, str], None]] = None
    ) -> BatchSummary:
        """
        Schedule and then print each project.
        
        Useful for monthly reporting workflows.
        """
        if not self.scheduler or not self.printer:
            raise ValueError("Both scheduler and printer required")
        
        self._reset()
        summary = BatchSummary(
            total=len(project_names),
            start_time=datetime.now()
        )
        
        timestamp = get_timestamp()
        logger.info(f"Batch schedule+print: {len(project_names)} projects")
        
        for i, project_name in enumerate(project_names, 1):
            if self._cancelled:
                break
            
            result = BatchResult(item_name=project_name, status=BatchStatus.RUNNING)
            start = datetime.now()
            
            if on_progress:
                on_progress(i, len(project_names), project_name)
            
            try:
                # Open
                self.projects.open_project(project_name)
                time.sleep(self.INTER_OPERATION_DELAY)
                
                # Schedule
                self.scheduler.schedule_project()
                time.sleep(self.INTER_OPERATION_DELAY)
                
                # Apply layout
                self.layouts.open_layout(layout_name)
                
                # Print
                safe_name = sanitize_filename(project_name)
                filename = f"scheduled_{safe_name}_{timestamp}.pdf"
                self.printer.print_to_pdf(filename)
                
                result.status = BatchStatus.COMPLETED
                result.output_path = self.output_dir / filename
                summary.successful += 1
                
            except Exception as e:
                result.status = BatchStatus.FAILED
                result.error = str(e)
                summary.failed += 1
            
            result.duration_seconds = (datetime.now() - start).total_seconds()
            summary.results.append(result)
        
        summary.end_time = datetime.now()
        return summary
    
    # =========================================================================
    # Reporting
    # =========================================================================
    
    def generate_report(self, summary: BatchSummary, output_path: Optional[Path] = None) -> Path:
        """
        Generate a batch report.
        
        Args:
            summary: BatchSummary from batch operation
            output_path: Optional output path for report
            
        Returns:
            Path to generated report
        """
        if not output_path:
            output_path = self.output_dir / f"batch_report_{get_timestamp()}.txt"
        
        lines = [
            "=" * 60,
            "P6 BATCH OPERATION REPORT",
            "=" * 60,
            f"Start Time: {summary.start_time}",
            f"End Time: {summary.end_time}",
            f"Duration: {summary.duration:.1f} seconds",
            "",
            f"Total: {summary.total}",
            f"Successful: {summary.successful}",
            f"Failed: {summary.failed}",
            f"Cancelled: {summary.cancelled}",
            f"Success Rate: {summary.success_rate:.1f}%",
            "",
            "-" * 60,
            "DETAILS",
            "-" * 60,
        ]
        
        for result in summary.results:
            status = "✓" if result.status == BatchStatus.COMPLETED else "✗"
            lines.append(f"{status} {result.item_name}")
            if result.output_path:
                lines.append(f"    Output: {result.output_path}")
            if result.error:
                lines.append(f"    Error: {result.error}")
            lines.append(f"    Duration: {result.duration_seconds:.1f}s")
        
        lines.append("=" * 60)
        
        output_path.write_text("\n".join(lines))
        logger.info(f"Batch report saved: {output_path}")
        
        return output_path
