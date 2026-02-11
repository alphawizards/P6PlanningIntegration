#!/usr/bin/env python3
"""
Generate P6 Summary Schedule from Excel Data

This script generates a high-level P6 Summary Schedule in XER format by:
1. Loading summary data from an Excel file (WBS Summary.xlsx)
2. Parsing a template XER file to extract headers, project, and WBS structure
3. Creating new TASK entries from the Excel data
4. Writing a new XER file with the summary schedule

Author: Senior Python Developer & P6 Data Engineer
Date: 2026-01-20
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from xer_utils import XERParser, XERWriter, write_template_table

# Setup standalone logger to avoid config dependencies
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('summary_schedule_generator')


class SummaryScheduleGenerator:
    """Generates P6 Summary Schedule from Excel data and template XER file."""

    def __init__(
        self,
        template_xer: Path,
        summary_excel: Path,
        output_xer: Path,
    ) -> None:
        """Initialize the generator.

        Args:
            template_xer: Path to template XER file.
            summary_excel: Path to Excel file with summary data.
            output_xer: Path for output XER file.
        """
        self.template_xer: Path = template_xer
        self.summary_excel: Path = summary_excel
        self.output_xer: Path = output_xer
        self.writer: XERWriter = XERWriter()

        # Data containers
        self.template_tables: dict[str, Any] = {}
        self.summary_df: Optional[pd.DataFrame] = None
        self.proj_id: Optional[str] = None
        self.root_wbs_id: Optional[str] = None
        self.default_calendar_id: Optional[str] = None

    def run(self) -> None:
        """Main execution flow."""
        logger.info("=" * 80)
        logger.info("P6 Summary Schedule Generator")
        logger.info("=" * 80)

        try:
            # Step 1: Load and filter summary data
            self._load_summary_data()

            # Step 2: Parse template XER
            self.template_tables = XERParser.parse(self.template_xer)

            # Step 3: Extract project metadata
            self._extract_project_metadata()

            # Step 4: Generate tasks from summary data
            tasks_df = self._generate_tasks()

            # Step 5: Write output XER
            self._write_output_xer(tasks_df)

            # Step 6: Validate output dates match input dates
            self._validate_output_dates(tasks_df)

            logger.info("=" * 80)
            logger.info(f"✓ Successfully generated summary schedule: {self.output_xer}")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"Failed to generate summary schedule: {e}")
            raise

    def _load_summary_data(self) -> None:
        """Load and filter summary data from Excel."""
        logger.info(f"Loading summary data from: {self.summary_excel}")

        # Read Excel file
        self.summary_df = pd.read_excel(self.summary_excel)

        logger.info(f"Loaded {len(self.summary_df)} rows from Excel")
        logger.debug(f"Columns: {self.summary_df.columns.tolist()}")

        # Generate automatic Activity Codes (A1000, A1010, A1020, etc.)
        # Starting at A1000, incrementing by 10 for each row
        activity_codes = [f"A{1000 + (i * 10)}" for i in range(len(self.summary_df))]
        self.summary_df['Activity Code'] = activity_codes
        logger.info(f"Generated {len(activity_codes)} activity codes (A1000 to A{1000 + (len(self.summary_df)-1) * 10})")

        # Filter out rows with empty WBS names
        original_count = len(self.summary_df)
        self.summary_df = self.summary_df[
            self.summary_df['WBS'].notna() &
            (self.summary_df['WBS'].astype(str).str.strip() != '')
        ]
        filtered_count = len(self.summary_df)
        removed_count = original_count - filtered_count

        if removed_count > 0:
            logger.info(f"Filtered out {removed_count} rows with empty WBS names")
        logger.info(f"Total rows to process: {filtered_count}")

        # Parse Start and Finish dates
        self.summary_df['Start'] = pd.to_datetime(
            self.summary_df['Start'],
            errors='coerce'
        )
        self.summary_df['Finish'] = pd.to_datetime(
            self.summary_df['Finish'],
            errors='coerce'
        )

        # Log any rows with invalid dates
        invalid_start = self.summary_df['Start'].isna().sum()
        invalid_finish = self.summary_df['Finish'].isna().sum()

        if invalid_start > 0:
            logger.warning(f"{invalid_start} rows have invalid Start dates")
        if invalid_finish > 0:
            logger.warning(f"{invalid_finish} rows have invalid Finish dates")

    def _extract_project_metadata(self) -> None:
        """Extract project ID, root WBS ID, and default calendar from template."""
        logger.info("Extracting project metadata from template")

        # Extract Project ID
        if 'PROJECT' in self.template_tables:
            project_data = self.template_tables['PROJECT']['data']
            if project_data:
                fields = self.template_tables['PROJECT']['fields']
                proj_id_idx = fields.index('proj_id')
                self.proj_id = project_data[0][proj_id_idx]
                logger.info(f"Project ID: {self.proj_id}")

        # Extract Root WBS ID (parent_wbs_id is empty for root)
        if 'PROJWBS' in self.template_tables:
            wbs_data = self.template_tables['PROJWBS']['data']
            fields = self.template_tables['PROJWBS']['fields']

            wbs_id_idx = fields.index('wbs_id')
            proj_node_idx = fields.index('proj_node_flag')

            # Find root WBS (proj_node_flag = 'Y')
            for row in wbs_data:
                if row[proj_node_idx] == 'Y':
                    self.root_wbs_id = row[wbs_id_idx]
                    logger.info(f"Root WBS ID: {self.root_wbs_id}")
                    break

        # Extract default calendar (from first CALENDAR or PROJECT clndr_id)
        if 'PROJECT' in self.template_tables:
            project_data = self.template_tables['PROJECT']['data']
            if project_data:
                fields = self.template_tables['PROJECT']['fields']
                clndr_id_idx = fields.index('clndr_id')
                self.default_calendar_id = project_data[0][clndr_id_idx]
                logger.info(f"Default Calendar ID: {self.default_calendar_id}")

        if not self.proj_id or not self.root_wbs_id:
            raise ValueError("Could not extract required project metadata from template")

    def _generate_tasks(self) -> pd.DataFrame:
        """Generate TASK table from summary data.

        Returns:
            DataFrame with task data.
        """
        logger.info("Generating tasks from summary data")

        tasks: list[dict[str, Any]] = []
        base_task_id: int = 4600000  # Start with a high ID to avoid conflicts

        for idx, row in self.summary_df.iterrows():
            task_id = base_task_id + idx

            # Determine task status based on dates
            start_date = row['Start']
            finish_date = row['Finish']

            if pd.notna(start_date) and start_date <= datetime.now():
                status_code = 'TK_Active'  # In Progress
            else:
                status_code = 'TK_NotStart'  # Not Started

            # Calculate duration in hours (assume 8-hour workday)
            if pd.notna(start_date) and pd.notna(finish_date):
                duration_days = (finish_date - start_date).days
                target_drtn_hr_cnt = duration_days * 8
            else:
                target_drtn_hr_cnt = 0

            # Build task record
            task: dict[str, Any] = {
                'task_id': task_id,
                'proj_id': self.proj_id,
                'wbs_id': self.root_wbs_id,  # All tasks under root WBS
                'clndr_id': self.default_calendar_id,
                'task_code': str(row['Activity Code']),
                'task_name': str(row['WBS']),
                'task_type': 'TT_Task',  # Task Dependent
                'duration_type': 'DT_FixedDUR2',  # Fixed Duration
                'status_code': status_code,
                'target_start_date': self.writer.format_datetime(start_date),
                'target_end_date': self.writer.format_datetime(finish_date),
                'early_start_date': self.writer.format_datetime(start_date),
                'early_end_date': self.writer.format_datetime(finish_date),
                'late_start_date': self.writer.format_datetime(start_date),
                'late_end_date': self.writer.format_datetime(finish_date),
                'target_drtn_hr_cnt': target_drtn_hr_cnt,
                'remain_drtn_hr_cnt': target_drtn_hr_cnt if status_code == 'TK_NotStart' else 0,
                'act_start_date': self.writer.format_datetime(start_date) if status_code == 'TK_Active' else '',
                'act_end_date': '',
                'phys_complete_pct': 0,
                'complete_pct_type': 'CP_Phys',
                'priority_type': 'PT_Normal',
                'free_float_hr_cnt': 0,
                'total_float_hr_cnt': 0,
            }

            tasks.append(task)

        tasks_df = pd.DataFrame(tasks)
        logger.info(f"Generated {len(tasks_df)} tasks from summary data")

        return tasks_df

    def _validate_output_dates(self, tasks_df: pd.DataFrame) -> None:
        """Validate that output XER dates match the input Excel dates.

        Args:
            tasks_df: DataFrame with generated task data.
        """
        logger.info("Validating output dates against input Excel data...")

        # Read the generated XER file to extract task dates
        try:
            with open(self.output_xer, 'r', encoding='cp1252') as f:
                xer_content = f.read()
        except Exception as e:
            logger.error(f"Could not read output XER for validation: {e}")
            return

        # Parse TASK table from XER
        xer_tasks: dict[str, dict[str, str]] = {}
        in_task_table = False
        task_fields: list[str] = []

        for line in xer_content.split('\n'):
            line = line.strip()
            if line.startswith('%T') and 'TASK' in line:
                in_task_table = True
                continue
            if in_task_table and line.startswith('%F'):
                task_fields = [f.strip() for f in line.split('\t')[1:]]
                continue
            if in_task_table and line.startswith('%T'):
                break  # End of TASK table
            if in_task_table and line.startswith('%R'):
                values = line.split('\t')[1:]
                if len(values) >= len(task_fields):
                    task_dict = dict(zip(task_fields, values))
                    task_code = task_dict.get('task_code', '')
                    xer_tasks[task_code] = {
                        'target_start_date': task_dict.get('target_start_date', ''),
                        'target_end_date': task_dict.get('target_end_date', '')
                    }

        # Compare with source data
        matches: int = 0
        mismatches: int = 0

        for _, row in self.summary_df.iterrows():
            activity_code = str(row['Activity Code'])
            excel_start = self.writer.format_datetime(row['Start'])
            excel_finish = self.writer.format_datetime(row['Finish'])

            if activity_code in xer_tasks:
                xer_start = xer_tasks[activity_code]['target_start_date']
                xer_finish = xer_tasks[activity_code]['target_end_date']

                start_match = excel_start == xer_start
                finish_match = excel_finish == xer_finish

                if start_match and finish_match:
                    matches += 1
                else:
                    mismatches += 1
                    logger.warning(
                        f"Date mismatch for {activity_code}: "
                        f"Excel Start={excel_start} vs XER Start={xer_start}, "
                        f"Excel Finish={excel_finish} vs XER Finish={xer_finish}"
                    )
            else:
                mismatches += 1
                logger.warning(f"Activity {activity_code} not found in XER output")

        # Report results
        total = matches + mismatches
        logger.info(f"Date Validation Complete: {matches}/{total} activities matched")
        if mismatches == 0:
            logger.info("✓ All dates validated successfully!")
        else:
            logger.warning(f"⚠ {mismatches} activities had date mismatches")

    def _write_output_xer(self, tasks_df: pd.DataFrame) -> None:
        """Write the output XER file.

        Args:
            tasks_df: DataFrame with task data.
        """
        logger.info(f"Writing output XER: {self.output_xer}")

        output_lines: list[str] = []

        # 1. Write ERMHDR
        if 'ERMHDR' in self.template_tables:
            output_lines.append(self.template_tables['ERMHDR'] + '\n')

        # 2. Write template tables using shared helper
        template_table_order: list[str] = [
            'CURRTYPE', 'FINTMPL', 'NONWORK', 'OBS', 'PCATTYPE',
            'UDFTYPE', 'PCATVAL', 'PROJECT', 'CALENDAR', 'PROJPCAT',
            'SCHEDOPTIONS', 'PROJWBS',
        ]
        for table_name in template_table_order:
            if table_name in self.template_tables:
                output_lines.append(
                    write_template_table(self.writer, table_name, self.template_tables[table_name])
                )

        # 3. Write TASK table (our generated tasks)
        output_lines.append(self.writer.write_table_header('TASK'))

        # Define the fields for TASK table based on P6 XER standard
        task_fields: list[str] = [
            'task_id', 'proj_id', 'wbs_id', 'clndr_id', 'phys_complete_pct',
            'rev_fdbk_flag', 'est_wt', 'lock_plan_flag', 'auto_compute_act_flag',
            'complete_pct_type', 'task_type', 'duration_type', 'status_code',
            'task_code', 'task_name', 'rsrc_id', 'total_float_hr_cnt',
            'free_float_hr_cnt', 'remain_drtn_hr_cnt', 'act_work_qty',
            'remain_work_qty', 'target_work_qty', 'target_drtn_hr_cnt',
            'target_equip_qty', 'act_equip_qty', 'remain_equip_qty',
            'cstr_date', 'act_start_date', 'act_end_date', 'late_start_date',
            'late_end_date', 'expect_end_date', 'early_start_date', 'early_end_date',
            'restart_date', 'reend_date', 'target_start_date', 'target_end_date',
            'rem_late_start_date', 'rem_late_end_date', 'cstr_type', 'priority_type'
        ]

        output_lines.append(self.writer.write_field_header(task_fields))

        # Write task records
        for _, task in tasks_df.iterrows():
            values: list[Any] = []
            for field in task_fields:
                if field in task:
                    values.append(task[field])
                else:
                    # Default values for missing fields
                    if field in ['rev_fdbk_flag', 'lock_plan_flag', 'auto_compute_act_flag']:
                        values.append('N')
                    elif field == 'est_wt':
                        values.append('1')
                    elif field in ['rsrc_id', 'act_work_qty', 'remain_work_qty',
                                   'target_work_qty', 'target_equip_qty', 'act_equip_qty',
                                   'remain_equip_qty']:
                        values.append('0')
                    else:
                        values.append('')

            output_lines.append(self.writer.write_record(values))

        # 4. Write empty TASKPRED table (no logic links)
        output_lines.append(self.writer.write_table_header('TASKPRED'))
        output_lines.append(self.writer.write_field_header([
            'task_pred_id', 'task_id', 'pred_task_id', 'pred_type', 'lag_hr_cnt'
        ]))
        # No records - empty table

        # Write to file
        output_content = ''.join(output_lines)

        with open(self.output_xer, 'w', encoding='cp1252', newline='') as f:
            f.write(output_content)

        logger.info(f"Wrote {len(tasks_df)} tasks to output XER file")


def main() -> None:
    """Main entry point."""
    # Define file paths using organized folder structure
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent

    # Input/Output paths
    template_xer = base_dir / "templates" / "19282-FS-Summary-FS-EXE.xer"
    summary_excel = base_dir / "input" / "WBS Summary.xlsx"

    # Generate date stamp for output filename (format: DD_Mon_YYYY)
    date_stamp = datetime.now().strftime("%d_%b_%Y")
    output_xer = base_dir / "output" / f"19282_Summary_Schedule_Generated_{date_stamp}.xer"

    # Verify input files exist
    if not template_xer.exists():
        logger.error(f"Template XER not found: {template_xer}")
        sys.exit(1)

    if not summary_excel.exists():
        logger.error(f"Summary Excel not found: {summary_excel}")
        sys.exit(1)

    # Run generator
    generator = SummaryScheduleGenerator(
        template_xer=template_xer,
        summary_excel=summary_excel,
        output_xer=output_xer
    )

    generator.run()


if __name__ == '__main__':
    main()
