#!/usr/bin/env python3
"""
File Management Utilities
Handles directory creation and export path generation.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional

from src.utils import logger


def ensure_directory(path: Path) -> Path:
    """
    Ensure directory exists, create if missing.
    
    VERIFICATION POINT 1: Output Paths
    Creates directory structure before writing files.
    
    Args:
        path: Directory path to ensure exists
        
    Returns:
        Path: The directory path (created if needed)
    """
    try:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory exists: {path}")
        return path
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        raise RuntimeError(f"Failed to create directory: {e}") from e


def get_export_path(
    filename: str,
    subfolder: Optional[str] = None,
    base_dir: str = "reports",
    use_timestamp: bool = True
) -> Path:
    """
    Generate timestamped export path.
    
    VERIFICATION POINT 1: Output Paths
    Automatically creates directory structure with date organization.
    
    Args:
        filename: Base filename (e.g., "projects.csv")
        subfolder: Optional subfolder within base_dir
        base_dir: Base directory for exports (default: "reports")
        use_timestamp: Whether to include timestamp in path (default: True)
        
    Returns:
        Path: Full path for export file
        
    Example:
        get_export_path("projects.csv") 
        -> reports/2026-01-07/projects.csv
        
        get_export_path("activities.csv", subfolder="project_A")
        -> reports/2026-01-07/project_A/activities.csv
    """
    try:
        # Build base path
        base_path = Path(base_dir)
        
        # Add timestamp folder if requested
        if use_timestamp:
            timestamp_folder = datetime.now().strftime("%Y-%m-%d")
            base_path = base_path / timestamp_folder
        
        # Add subfolder if provided
        if subfolder:
            base_path = base_path / subfolder
        
        # Ensure directory exists
        ensure_directory(base_path)
        
        # Construct full path
        full_path = base_path / filename
        
        logger.debug(f"Generated export path: {full_path}")
        return full_path
        
    except Exception as e:
        logger.error(f"Failed to generate export path: {e}")
        raise RuntimeError(f"Failed to generate export path: {e}") from e


def get_timestamped_filename(base_name: str, extension: str) -> str:
    """
    Generate filename with timestamp.
    
    Args:
        base_name: Base name without extension (e.g., "project_report")
        extension: File extension without dot (e.g., "csv")
        
    Returns:
        str: Timestamped filename
        
    Example:
        get_timestamped_filename("project_report", "csv")
        -> "project_report_20260107_143022.csv"
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{timestamp}.{extension}"


def cleanup_old_exports(base_dir: str = "reports", days_to_keep: int = 30):
    """
    Clean up export files older than specified days.
    
    Args:
        base_dir: Base directory containing exports
        days_to_keep: Number of days to keep (default: 30)
    """
    try:
        base_path = Path(base_dir)
        if not base_path.exists():
            logger.debug(f"Export directory does not exist: {base_dir}")
            return
        
        cutoff_date = datetime.now().timestamp() - (days_to_keep * 86400)
        deleted_count = 0
        
        for item in base_path.rglob("*"):
            if item.is_file():
                if item.stat().st_mtime < cutoff_date:
                    item.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old export: {item}")
        
        logger.info(f"Cleaned up {deleted_count} old export files")
        
    except Exception as e:
        logger.warning(f"Failed to cleanup old exports: {e}")
