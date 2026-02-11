"""
XER File Utilities for P6 Schedule Generation

Shared utilities for reading and writing Primavera P6 XER format files.
Provides XERWriter for composing XER output, XERParser for reading XER
template files, and helper functions to eliminate repetitive table-writing
patterns.

Author: Senior Python Developer & P6 Data Engineer
Date: 2026-02-11
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Union

import pandas as pd

__all__ = ["XERWriter", "XERParser", "write_template_table"]

logger = logging.getLogger(__name__)


class XERWriter:
    """Helper class for writing Primavera P6 XER format files.

    Handles encoding, record formatting, and datetime conversion
    using the cp1252 encoding required by P6.
    """

    def __init__(self) -> None:
        self.encoding: str = "cp1252"  # Windows-1252 for P6 compatibility

    def write_table_header(self, table_name: str) -> str:
        """Generate an XER table header line.

        Args:
            table_name: Name of the P6 table (e.g. 'TASK', 'PROJECT').

        Returns:
            Formatted ``%T`` header line.
        """
        return f"%T\t{table_name}\n"

    def write_field_header(self, fields: list[str]) -> str:
        """Generate an XER field header line.

        Args:
            fields: List of field/column names for the table.

        Returns:
            Formatted ``%F`` field line.
        """
        return "%F\t" + "\t".join(fields) + "\n"

    def write_record(self, values: list[Any]) -> str:
        """Generate an XER data record line.

        Converts *None* and *NaN* values to empty strings so the
        output is valid for P6 import.

        Args:
            values: List of field values for one record.

        Returns:
            Formatted ``%R`` record line.
        """
        str_values: list[str] = []
        for v in values:
            if v is None or (isinstance(v, float) and pd.isna(v)):
                str_values.append("")
            else:
                str_values.append(str(v))
        return "%R\t" + "\t".join(str_values) + "\n"

    def format_datetime(self, dt: Union[datetime, str, None]) -> str:
        """Format a datetime value for P6 XER format (``YYYY-MM-DD HH:MM``).

        Accepts *datetime* objects, date strings parseable by pandas, or
        *None*.  Returns an empty string for missing / unparseable values.

        Args:
            dt: The datetime value to format.

        Returns:
            Formatted date string, or ``""`` if the value is missing or
            cannot be parsed.
        """
        if dt is None or (isinstance(dt, float) and pd.isna(dt)):
            return ""
        try:
            if pd.isna(dt):
                return ""
        except (ValueError, TypeError):
            pass
        if isinstance(dt, str):
            try:
                dt = pd.to_datetime(dt)
            except (ValueError, TypeError):
                return ""
        if isinstance(dt, datetime):
            return dt.strftime("%Y-%m-%d %H:%M")
        return ""


class XERParser:
    """Parser for Primavera P6 XER template files.

    Reads an XER file and extracts its tables into a structured dictionary.
    Supports cp1252 encoding with utf-8 fallback.
    """

    @staticmethod
    def parse(file_path: Path) -> dict[str, Any]:
        """Parse an XER file and return its tables.

        The returned dictionary maps table names to their contents:

        * ``'ERMHDR'`` maps to the raw header string.
        * All other keys map to ``{'fields': list[str], 'data': list[list[str]]}``.

        Args:
            file_path: Path to the XER file.

        Returns:
            Dictionary of parsed tables keyed by table name.
        """
        logger.info("Parsing template XER: %s", file_path)

        # Read file with fallback encoding
        try:
            with open(file_path, "r", encoding="cp1252") as f:
                content = f.read()
        except UnicodeDecodeError:
            logger.warning("cp1252 encoding failed, trying utf-8")
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

        lines = content.split("\n")
        tables: dict[str, Any] = {}

        current_table: str | None = None
        current_fields: list[str] = []
        current_data: list[list[str]] = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Table marker
            if line.startswith("%T"):
                # Save previous table
                if current_table and current_fields and current_data:
                    tables[current_table] = {
                        "fields": current_fields,
                        "data": current_data,
                    }
                    logger.debug(
                        "Extracted table '%s': %d rows",
                        current_table,
                        len(current_data),
                    )

                # Start new table
                parts = line.split("\t")
                current_table = parts[1] if len(parts) > 1 else line[2:].strip()
                current_fields = []
                current_data = []

            # Field marker
            elif line.startswith("%F"):
                parts = line.split("\t")
                current_fields = [p.strip() for p in parts[1:] if p.strip()]

            # Data row
            elif line.startswith("%R"):
                parts = line.split("\t")
                values = parts[1:]  # Skip %R marker

                # Pad or trim to match field count
                if len(values) < len(current_fields):
                    values.extend([""] * (len(current_fields) - len(values)))
                elif len(values) > len(current_fields):
                    values = values[: len(current_fields)]

                current_data.append(values)

            # Header line (ERMHDR)
            elif line.startswith("ERMHDR"):
                tables["ERMHDR"] = line

        # Save last table
        if current_table and current_fields and current_data:
            tables[current_table] = {
                "fields": current_fields,
                "data": current_data,
            }
            logger.debug(
                "Extracted table '%s': %d rows",
                current_table,
                len(current_data),
            )

        logger.info("Extracted %d tables from template", len(tables))
        logger.debug("Tables: %s", list(tables.keys()))

        return tables


def write_template_table(
    writer: XERWriter,
    table_name: str,
    table_data: dict[str, Any],
) -> str:
    """Write a single template table as an XER-formatted string.

    Combines the table header, field header, and all data records into
    a single string suitable for appending to an XER output file.

    Args:
        writer: An :class:`XERWriter` instance used for formatting.
        table_name: The P6 table name (e.g. ``'PROJECT'``, ``'CALENDAR'``).
        table_data: Dictionary with ``'fields'`` (list of column names) and
            ``'data'`` (list of row value lists).

    Returns:
        The complete XER text block for this table.
    """
    parts: list[str] = []
    parts.append(writer.write_table_header(table_name))
    parts.append(writer.write_field_header(table_data["fields"]))
    for row in table_data["data"]:
        parts.append(writer.write_record(row))
    return "".join(parts)
