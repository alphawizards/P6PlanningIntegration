#!/usr/bin/env python3
"""
Generate P6 Summary Schedule from Excel Data - Rev 2

This script generates a high-level P6 Summary Schedule in XER format by:
1. Loading summary data from a P6 XLSX Import file (TASK sheet format)
2. Parsing a template XER file to extract headers, project, and WBS structure
3. Creating new TASK entries from the Excel data
4. Writing a new XER file with the summary schedule

Rev 2: Modified to read from P6 XLSX Import format (TASK sheet with task_code,
       status_code, task_name, start_date, end_date columns)

Author: Senior Python Developer & P6 Data Engineer
Date: 2026-01-20
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import pandas as pd
import uuid

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup standalone logger to avoid config dependencies
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('summary_schedule_generator')


class XERWriter:
    """Helper class for writing XER format files."""

    def __init__(self):
        self.encoding = 'cp1252'  # Windows-1252 for P6 compatibility

    def write_table_header(self, table_name: str) -> str:
        """Generate table header line."""
        return f"%T\t{table_name}\n"

    def write_field_header(self, fields: List[str]) -> str:
        """Generate field header line."""
        return "%F\t" + "\t".join(fields) + "\n"

    def write_record(self, values: List) -> str:
        """Generate data record line."""
        # Convert None to empty string, handle all types
        str_values = []
        for v in values:
            if v is None or (isinstance(v, float) and pd.isna(v)):
                str_values.append("")
            else:
                str_values.append(str(v))
        return "%R\t" + "\t".join(str_values) + "\n"

    def format_datetime(self, dt) -> str:
        """Format datetime for P6 XER format (YYYY-MM-DD HH:MM)."""
        if pd.isna(dt):
            return ""
        if isinstance(dt, str):
            # Try to parse if it's a string
            try:
                dt = pd.to_datetime(dt)
            except:
                return ""
        if isinstance(dt, datetime):
            return dt.strftime("%Y-%m-%d %H:%M")
        return ""


class SummaryScheduleGenerator:
    """
    Generates P6 Summary Schedule from Excel data and template XER file.
    """

    def __init__(self, template_xer: Path, summary_excel: Path, output_xer: Path):
        """
        Initialize the generator.

        Args:
            template_xer: Path to template XER file
            summary_excel: Path to Excel file with summary data
            output_xer: Path for output XER file
        """
        self.template_xer = template_xer
        self.summary_excel = summary_excel
        self.output_xer = output_xer
        self.writer = XERWriter()

        # Data containers
        self.template_tables = {}
        self.summary_df = None
        self.proj_id = None
        self.root_wbs_id = None
        self.default_calendar_id = None

    def run(self):
        """Main execution flow."""
        logger.info("="*80)
        logger.info("P6 Summary Schedule Generator")
        logger.info("="*80)

        try:
            # Step 1: Load and filter summary data
            self._load_summary_data()

            # Step 2: Parse template XER
            self._parse_template_xer()

            # Step 3: Extract project metadata
            self._extract_project_metadata()

            # Step 4: Generate tasks from summary data
            tasks_df = self._generate_tasks()

            # Step 5: Write output XER
            self._write_output_xer(tasks_df)

            # Step 6: Validate output dates match input dates
            self._validate_output_dates(tasks_df)

            logger.info("="*80)
            logger.info(f"✓ Successfully generated summary schedule: {self.output_xer}")
            logger.info("="*80)

        except Exception as e:
            logger.error(f"Failed to generate summary schedule: {e}")
            raise

    def _load_summary_data(self):
        """Load and filter summary data from P6 XLSX Import file (TASK sheet)."""
        logger.info(f"Loading summary data from: {self.summary_excel}")

        # Read Excel file - specifically the TASK sheet for P6 Import format
        try:
            self.summary_df = pd.read_excel(self.summary_excel, sheet_name='TASK')
            logger.info("Reading from TASK sheet (P6 Import format)")
        except ValueError:
            # Fallback to first sheet if TASK doesn't exist
            self.summary_df = pd.read_excel(self.summary_excel)
            logger.info("Reading from first sheet (no TASK sheet found)")

        logger.info(f"Loaded {len(self.summary_df)} rows from Excel")
        logger.debug(f"Columns: {self.summary_df.columns.tolist()}")

        # Map P6 Import columns to internal names
        # P6 Import format: task_code, status_code, wbs_id, task_name, remain_drtn_hr_cnt, start_date, end_date
        column_mapping = {
            'task_code': 'Activity Code',
            'task_name': 'WBS',
            'start_date': 'Start',
            'end_date': 'Finish',
            'status_code': 'Status'
        }
        
        # Rename columns if they exist
        for old_col, new_col in column_mapping.items():
            if old_col in self.summary_df.columns:
                self.summary_df[new_col] = self.summary_df[old_col]
                logger.debug(f"Mapped column '{old_col}' -> '{new_col}'")

        # Use Activity Code from file if available, otherwise generate
        if 'Activity Code' not in self.summary_df.columns:
            activity_codes = [f"A{1000 + (i * 10)}" for i in range(len(self.summary_df))]
            self.summary_df['Activity Code'] = activity_codes
            logger.info(f"Generated {len(activity_codes)} activity codes (A1000 to A{1000 + (len(self.summary_df)-1) * 10})")
        else:
            logger.info(f"Using existing Activity Codes from file")

        # Filter out rows with empty activity names
        original_count = len(self.summary_df)
        self.summary_df = self.summary_df[
            self.summary_df['WBS'].notna() & 
            (self.summary_df['WBS'].astype(str).str.strip() != '')
        ]
        filtered_count = len(self.summary_df)
        removed_count = original_count - filtered_count

        if removed_count > 0:
            logger.info(f"Filtered out {removed_count} rows with empty activity names")
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

    def _parse_template_xer(self):
        """Parse the template XER file to extract tables."""
        logger.info(f"Parsing template XER: {self.template_xer}")

        # Read file with fallback encoding
        try:
            with open(self.template_xer, 'r', encoding='cp1252') as f:
                content = f.read()
        except UnicodeDecodeError:
            logger.warning("cp1252 encoding failed, trying utf-8")
            with open(self.template_xer, 'r', encoding='utf-8') as f:
                content = f.read()

        lines = content.split('\n')

        # Extract tables
        current_table = None
        current_fields = []
        current_data = []

        for line in lines:
            line = line.strip()

            if not line:
                continue

            # Table marker
            if line.startswith('%T'):
                # Save previous table
                if current_table and current_fields and current_data:
                    self.template_tables[current_table] = {
                        'fields': current_fields,
                        'data': current_data
                    }
                    logger.debug(f"Extracted table '{current_table}': {len(current_data)} rows")

                # Start new table
                parts = line.split('\t')
                current_table = parts[1] if len(parts) > 1 else line[2:].strip()
                current_fields = []
                current_data = []

            # Field marker
            elif line.startswith('%F'):
                parts = line.split('\t')
                current_fields = [p.strip() for p in parts[1:] if p.strip()]

            # Data row
            elif line.startswith('%R'):
                parts = line.split('\t')
                values = parts[1:]  # Skip %R marker

                # Pad or trim to match field count
                if len(values) < len(current_fields):
                    values.extend([''] * (len(current_fields) - len(values)))
                elif len(values) > len(current_fields):
                    values = values[:len(current_fields)]

                current_data.append(values)

            # Header line (ERMHDR)
            elif line.startswith('ERMHDR'):
                self.template_tables['ERMHDR'] = line

        # Save last table
        if current_table and current_fields and current_data:
            self.template_tables[current_table] = {
                'fields': current_fields,
                'data': current_data
            }
            logger.debug(f"Extracted table '{current_table}': {len(current_data)} rows")

        logger.info(f"Extracted {len(self.template_tables)} tables from template")
        logger.debug(f"Tables: {list(self.template_tables.keys())}")

    def _extract_project_metadata(self):
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
            parent_wbs_idx = fields.index('parent_wbs_id')
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
        """
        Generate TASK table from summary data.

        Returns:
            pd.DataFrame with task data
        """
        logger.info("Generating tasks from summary data")

        tasks = []
        base_task_id = 4600000  # Start with a high ID to avoid conflicts

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
            task = {
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

    def _validate_output_dates(self, tasks_df: pd.DataFrame):
        """
        Validate that output XER dates match the input Excel dates.
        
        Args:
            tasks_df: DataFrame with generated task data
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
        xer_tasks = {}
        in_task_table = False
        task_fields = []
        
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
        matches = 0
        mismatches = 0
        
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

    def _write_output_xer(self, tasks_df: pd.DataFrame):
        """
        Write the output XER file.

        Args:
            tasks_df: DataFrame with task data
        """
        logger.info(f"Writing output XER: {self.output_xer}")

        output_lines = []

        # 1. Write ERMHDR
        if 'ERMHDR' in self.template_tables:
            output_lines.append(self.template_tables['ERMHDR'] + '\n')

        # 2. Write CURRTYPE table (currency definitions)
        if 'CURRTYPE' in self.template_tables:
            output_lines.append(self.writer.write_table_header('CURRTYPE'))
            output_lines.append(self.writer.write_field_header(
                self.template_tables['CURRTYPE']['fields']
            ))
            for row in self.template_tables['CURRTYPE']['data']:
                output_lines.append(self.writer.write_record(row))

        # 3. Write other metadata tables (FINTMPL, NONWORK, OBS, PCATTYPE, etc.)
        metadata_tables = ['FINTMPL', 'NONWORK', 'OBS', 'PCATTYPE', 'UDFTYPE', 'PCATVAL']
        for table_name in metadata_tables:
            if table_name in self.template_tables:
                output_lines.append(self.writer.write_table_header(table_name))
                output_lines.append(self.writer.write_field_header(
                    self.template_tables[table_name]['fields']
                ))
                for row in self.template_tables[table_name]['data']:
                    output_lines.append(self.writer.write_record(row))

        # 4. Write PROJECT table
        if 'PROJECT' in self.template_tables:
            output_lines.append(self.writer.write_table_header('PROJECT'))
            output_lines.append(self.writer.write_field_header(
                self.template_tables['PROJECT']['fields']
            ))
            for row in self.template_tables['PROJECT']['data']:
                output_lines.append(self.writer.write_record(row))

        # 5. Write CALENDAR table
        if 'CALENDAR' in self.template_tables:
            output_lines.append(self.writer.write_table_header('CALENDAR'))
            output_lines.append(self.writer.write_field_header(
                self.template_tables['CALENDAR']['fields']
            ))
            for row in self.template_tables['CALENDAR']['data']:
                output_lines.append(self.writer.write_record(row))

        # 6. Write PROJPCAT table
        if 'PROJPCAT' in self.template_tables:
            output_lines.append(self.writer.write_table_header('PROJPCAT'))
            output_lines.append(self.writer.write_field_header(
                self.template_tables['PROJPCAT']['fields']
            ))
            for row in self.template_tables['PROJPCAT']['data']:
                output_lines.append(self.writer.write_record(row))

        # 7. Write SCHEDOPTIONS table
        if 'SCHEDOPTIONS' in self.template_tables:
            output_lines.append(self.writer.write_table_header('SCHEDOPTIONS'))
            output_lines.append(self.writer.write_field_header(
                self.template_tables['SCHEDOPTIONS']['fields']
            ))
            for row in self.template_tables['SCHEDOPTIONS']['data']:
                output_lines.append(self.writer.write_record(row))

        # 8. Write PROJWBS table
        if 'PROJWBS' in self.template_tables:
            output_lines.append(self.writer.write_table_header('PROJWBS'))
            output_lines.append(self.writer.write_field_header(
                self.template_tables['PROJWBS']['fields']
            ))
            for row in self.template_tables['PROJWBS']['data']:
                output_lines.append(self.writer.write_record(row))

        # 9. Write TASK table (our generated tasks)
        output_lines.append(self.writer.write_table_header('TASK'))

        # Define the fields for TASK table based on P6 XER standard
        task_fields = [
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
            values = []
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

        # 10. Write empty TASKPRED table (no logic links)
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


def main():
    """Main entry point."""
    # Define file paths using organized folder structure
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent

    # Input/Output paths
    template_xer = base_dir / "templates" / "19282-FS-Summary-FS-EXE.xer"
    # Rev 2: Use P6 XLSX Import file as source
    summary_excel = base_dir / "output" / "19282_Summary_Schedule_Import_2026-01-20.xlsx"
    
    # Generate date stamp for output filename (format: DD_Mon_YYYY)
    date_stamp = datetime.now().strftime("%d_%b_%Y")
    output_xer = base_dir / "output" / f"19282_Summary_Schedule_Rev2_{date_stamp}.xer"

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
