#!/usr/bin/env python3
"""
Data Exporters
Handles exporting DataFrames to various formats (CSV, Excel, JSON).
"""

from pathlib import Path
from typing import Optional, Union
import pandas as pd

from src.utils import logger, get_export_path


class DataExporter:
    """
    Export DataFrames to various formats.
    
    Handles:
    - CSV export
    - Excel export with formatting
    - JSON export with datetime serialization for AI context
    """
    
    def __init__(self, base_dir: str = "reports"):
        """
        Initialize DataExporter.
        
        Args:
            base_dir: Base directory for exports (default: "reports")
        """
        self.base_dir = base_dir
        logger.info(f"DataExporter initialized with base_dir: {base_dir}")
    
    def to_csv(
        self,
        df: pd.DataFrame,
        filename: str,
        subfolder: Optional[str] = None,
        index: bool = False
    ) -> Path:
        """
        Export DataFrame to CSV.
        
        VERIFICATION POINT 1: Output Paths
        Uses get_export_path which ensures directory exists.
        
        Args:
            df: DataFrame to export
            filename: Output filename (e.g., "projects.csv")
            subfolder: Optional subfolder within base_dir
            index: Whether to include DataFrame index (default: False)
            
        Returns:
            Path: Path to exported file
        """
        try:
            # Get export path (automatically creates directory)
            output_path = get_export_path(
                filename=filename,
                subfolder=subfolder,
                base_dir=self.base_dir
            )
            
            logger.info(f"Exporting DataFrame to CSV: {output_path}")
            logger.debug(f"DataFrame shape: {df.shape}")
            
            # Export to CSV
            df.to_csv(output_path, index=index, encoding='utf-8')
            
            logger.info(f"✓ Successfully exported to CSV: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            raise RuntimeError(f"Failed to export to CSV: {e}") from e
    
    def to_excel(
        self,
        df: pd.DataFrame,
        filename: str,
        subfolder: Optional[str] = None,
        sheet_name: str = "Sheet1",
        index: bool = False
    ) -> Path:
        """
        Export DataFrame to Excel with date formatting.
        
        VERIFICATION POINT 4: Excel Formatting
        Uses pandas.ExcelWriter for proper formatting.
        
        VERIFICATION POINT 1: Output Paths
        Uses get_export_path which ensures directory exists.
        
        Args:
            df: DataFrame to export
            filename: Output filename (e.g., "projects.xlsx")
            subfolder: Optional subfolder within base_dir
            sheet_name: Excel sheet name (default: "Sheet1")
            index: Whether to include DataFrame index (default: False)
            
        Returns:
            Path: Path to exported file
        """
        try:
            # Get export path (automatically creates directory)
            output_path = get_export_path(
                filename=filename,
                subfolder=subfolder,
                base_dir=self.base_dir
            )
            
            logger.info(f"Exporting DataFrame to Excel: {output_path}")
            logger.debug(f"DataFrame shape: {df.shape}")
            
            # VERIFICATION POINT 4: Excel Formatting
            # Use pandas.ExcelWriter for proper date formatting
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(
                    writer,
                    sheet_name=sheet_name,
                    index=index
                )
                
                # Get worksheet for formatting
                worksheet = writer.sheets[sheet_name]
                
                # Auto-adjust column widths
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(str(col))
                    )
                    # Add some padding
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[chr(65 + idx)].width = adjusted_width
            
            logger.info(f"✓ Successfully exported to Excel: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to export to Excel: {e}")
            raise RuntimeError(f"Failed to export to Excel: {e}") from e
    
    def to_json_context(
        self,
        df: pd.DataFrame,
        filename: Optional[str] = None,
        subfolder: Optional[str] = None,
        max_rows: Optional[int] = None
    ) -> Union[str, Path]:
        """
        Export DataFrame to JSON with datetime serialization for AI context.
        
        VERIFICATION POINT 2: Serialization
        Converts datetime objects to ISO format strings using date_format='iso'.
        
        VERIFICATION POINT 3: Context Limits
        Supports max_rows parameter to limit output size.
        
        Args:
            df: DataFrame to export
            filename: Optional output filename (if None, returns JSON string)
            subfolder: Optional subfolder within base_dir
            max_rows: Optional maximum number of rows to export
            
        Returns:
            str or Path: JSON string if filename is None, otherwise Path to file
        """
        try:
            # VERIFICATION POINT 3: Context Limits
            # Apply row limit if specified
            if max_rows is not None and len(df) > max_rows:
                logger.warning(f"Limiting DataFrame from {len(df)} to {max_rows} rows for AI context")
                df = df.head(max_rows)
            
            logger.info(f"Converting DataFrame to JSON context (shape: {df.shape})")
            
            # VERIFICATION POINT 2: Serialization
            # Convert datetime objects to ISO format strings
            json_str = df.to_json(
                orient='records',
                date_format='iso',
                indent=2
            )
            
            # If filename provided, write to file
            if filename:
                output_path = get_export_path(
                    filename=filename,
                    subfolder=subfolder,
                    base_dir=self.base_dir
                )
                
                logger.info(f"Writing JSON context to file: {output_path}")
                output_path.write_text(json_str, encoding='utf-8')
                logger.info(f"✓ Successfully exported JSON context: {output_path}")
                return output_path
            else:
                # Return JSON string for in-memory use
                logger.info("✓ Successfully generated JSON context string")
                return json_str
            
        except Exception as e:
            logger.error(f"Failed to export to JSON context: {e}")
            raise RuntimeError(f"Failed to export to JSON context: {e}") from e
    
    def to_json_file(
        self,
        df: pd.DataFrame,
        filename: str,
        subfolder: Optional[str] = None,
        orient: str = 'records',
        indent: int = 2
    ) -> Path:
        """
        Export DataFrame to JSON file.
        
        Args:
            df: DataFrame to export
            filename: Output filename (e.g., "projects.json")
            subfolder: Optional subfolder within base_dir
            orient: JSON orientation (default: 'records')
            indent: JSON indentation (default: 2)
            
        Returns:
            Path: Path to exported file
        """
        try:
            output_path = get_export_path(
                filename=filename,
                subfolder=subfolder,
                base_dir=self.base_dir
            )
            
            logger.info(f"Exporting DataFrame to JSON: {output_path}")
            
            # Convert to JSON with ISO date format
            json_str = df.to_json(
                orient=orient,
                date_format='iso',
                indent=indent
            )
            
            output_path.write_text(json_str, encoding='utf-8')
            
            logger.info(f"✓ Successfully exported to JSON: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
            raise RuntimeError(f"Failed to export to JSON: {e}") from e
    
    def export_multiple(
        self,
        dataframes: dict,
        filename_base: str,
        formats: list = ['csv', 'excel'],
        subfolder: Optional[str] = None
    ) -> dict:
        """
        Export multiple DataFrames to multiple formats.
        
        Args:
            dataframes: Dict of {name: DataFrame}
            filename_base: Base filename (e.g., "project_data")
            formats: List of formats to export ('csv', 'excel', 'json')
            subfolder: Optional subfolder within base_dir
            
        Returns:
            dict: Dict of {format: {name: path}}
        """
        results = {}
        
        try:
            for format_type in formats:
                results[format_type] = {}
                
                for name, df in dataframes.items():
                    if format_type == 'csv':
                        filename = f"{filename_base}_{name}.csv"
                        path = self.to_csv(df, filename, subfolder)
                    elif format_type == 'excel':
                        filename = f"{filename_base}_{name}.xlsx"
                        path = self.to_excel(df, filename, subfolder, sheet_name=name)
                    elif format_type == 'json':
                        filename = f"{filename_base}_{name}.json"
                        path = self.to_json_file(df, filename, subfolder)
                    else:
                        logger.warning(f"Unknown format: {format_type}")
                        continue
                    
                    results[format_type][name] = path
            
            logger.info(f"✓ Successfully exported {len(dataframes)} DataFrames to {len(formats)} formats")
            return results
            
        except Exception as e:
            logger.error(f"Failed to export multiple DataFrames: {e}")
            raise RuntimeError(f"Failed to export multiple: {e}") from e
