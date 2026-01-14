#!/usr/bin/env python3
"""
PDF Report Generator for P6 Planning Integration.

Generates professional PDF reports from P6 schedule data via DAO layer.

Supported Report Types:
- Schedule Summary Report: Executive-level project overview
- Critical Path Report: Detailed critical path analysis
- Health Check Report: Schedule quality validation (DCMA/AACE)
- Comprehensive Report: Multi-section combined report

Architecture:
- Uses Database/DAO approach (format-agnostic: XER, XML, MPX)
- Leverages existing SQLite DAOs and Schedule Analyzer
- Follows mining industry standards for thresholds and checks
"""

from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from io import BytesIO

import pandas as pd

from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    PageBreak,
    Image,
    KeepTogether,
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.barcharts import VerticalBarChart

from src.utils import logger, get_export_path
from src.dao.sqlite import SQLiteManager
from src.analyzers.schedule_analyzer import ScheduleAnalyzer

from .pdf_styles import (
    get_custom_styles,
    get_table_style,
    get_summary_box_style,
    get_health_color,
    get_float_color,
    get_severity_color,
    MARGIN_TOP,
    MARGIN_BOTTOM,
    MARGIN_LEFT,
    MARGIN_RIGHT,
    CORPORATE_PRIMARY,
    CORPORATE_SECONDARY,
    COLOR_CRITICAL,
    COLOR_HIGH,
    COLOR_MEDIUM,
    COLOR_LOW,
    COLOR_INFO,
    FONT_BODY,
    FONT_SMALL,
    THRESHOLD_CRITICAL_FLOAT,
    THRESHOLD_NEAR_CRITICAL,
    THRESHOLD_LOW_FLOAT,
    THRESHOLD_HIGH_DURATION,
    TARGET_LOGIC_DENSITY,
    TARGET_CONSTRAINT_PERCENT,
)


class PDFGenerator:
    """
    Generate PDF reports from P6 schedule data via DAO layer.

    Provides professional schedule reports:
    - Project summary reports
    - Critical path analysis
    - Schedule health checks
    - Comprehensive multi-section reports

    Example:
        >>> pdf_gen = PDFGenerator()
        >>> with SQLiteManager() as manager:
        ...     pdf_gen.set_manager(manager)
        ...     output = pdf_gen.generate_schedule_summary(project_id=123)
        >>> print(f"PDF created: {output}")
    """

    def __init__(
        self,
        page_size=letter,
        base_dir: str = "reports",
        landscape_mode: bool = False,
    ):
        """
        Initialize PDF Generator.

        Args:
            page_size: Page size (letter, A4, etc.)
            base_dir: Base directory for PDF output
            landscape_mode: Use landscape orientation
        """
        self.page_size = landscape(page_size) if landscape_mode else page_size
        self.base_dir = Path(base_dir)
        self.landscape_mode = landscape_mode

        # Ensure output directory exists
        self.pdf_dir = self.base_dir / "pdf"
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

        # Custom styles
        self.styles = get_custom_styles()

        # Database manager (set via set_manager or context)
        self._manager: Optional[SQLiteManager] = None

        logger.info(f"PDFGenerator initialized (output: {self.pdf_dir})")

    def set_manager(self, manager: SQLiteManager):
        """Set the SQLite manager for database queries."""
        self._manager = manager

    def _get_manager(self) -> SQLiteManager:
        """Get the database manager, raising if not set."""
        if self._manager is None:
            raise ValueError(
                "Database manager not set. Use set_manager() or provide manager via context."
            )
        return self._manager

    # =========================================================================
    # Schedule Summary Report
    # =========================================================================

    def generate_schedule_summary(
        self,
        project_id: int,
        output_filename: Optional[str] = None,
        include_activities: bool = True,
        include_critical_path: bool = True,
        max_activities: int = 50,
    ) -> Path:
        """
        Generate executive-level schedule summary PDF.

        Args:
            project_id: Project ObjectId from database
            output_filename: Optional custom filename
            include_activities: Include activity listing section
            include_critical_path: Include critical path section
            max_activities: Maximum activities to show in tables

        Returns:
            Path to generated PDF file
        """
        logger.info(f"Generating schedule summary for project {project_id}")

        manager = self._get_manager()

        # Get DAOs
        project_dao = manager.get_project_dao()
        activity_dao = manager.get_activity_dao()
        relationship_dao = manager.get_relationship_dao()

        # Query data
        project_df = project_dao.get_project_by_object_id(project_id)
        if project_df.empty:
            raise ValueError(f"Project {project_id} not found")

        project = project_df.iloc[0]
        activities_df = activity_dao.get_activities_for_project(project_id)
        critical_df = activity_dao.get_critical_activities(project_id)
        relationships_df = relationship_dao.get_relationships(project_id)

        # Generate filename
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = self._sanitize_filename(project['Name'])
            output_filename = f"schedule_summary_{safe_name}_{timestamp}.pdf"

        output_path = self.pdf_dir / output_filename

        # Build PDF
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=self.page_size,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            leftMargin=MARGIN_LEFT,
            rightMargin=MARGIN_RIGHT,
        )

        content = []

        # Title
        content.append(Paragraph("Schedule Summary Report", self.styles['ReportTitle']))
        content.append(Spacer(1, 12))

        # Project Header
        content.extend(self._build_project_header(project))

        # Statistics Section
        content.extend(
            self._build_statistics_section(
                activities_df, critical_df, relationships_df
            )
        )

        # Critical Path Section
        if include_critical_path and not critical_df.empty:
            content.append(Spacer(1, 12))
            content.extend(
                self._build_critical_path_section(critical_df, max_activities)
            )

        # Activity Listing
        if include_activities and not activities_df.empty:
            content.append(Spacer(1, 12))
            content.extend(
                self._build_activity_table(activities_df, max_activities)
            )

        # Build PDF
        doc.build(content, onFirstPage=self._add_footer, onLaterPages=self._add_footer)

        file_size = output_path.stat().st_size / 1024
        logger.info(f"Generated PDF: {output_path} ({file_size:.1f} KB)")

        return output_path

    # =========================================================================
    # Critical Path Report
    # =========================================================================

    def generate_critical_path_report(
        self,
        project_id: int,
        output_filename: Optional[str] = None,
        include_near_critical: bool = True,
        near_critical_threshold: float = 10.0,
    ) -> Path:
        """
        Generate detailed critical path analysis report.

        Args:
            project_id: Project ObjectId
            output_filename: Optional custom filename
            include_near_critical: Include near-critical activities
            near_critical_threshold: Float threshold for near-critical (days)

        Returns:
            Path to generated PDF
        """
        logger.info(f"Generating critical path report for project {project_id}")

        manager = self._get_manager()

        project_dao = manager.get_project_dao()
        activity_dao = manager.get_activity_dao()

        project_df = project_dao.get_project_by_object_id(project_id)
        if project_df.empty:
            raise ValueError(f"Project {project_id} not found")

        project = project_df.iloc[0]
        activities_df = activity_dao.get_activities_for_project(project_id)
        critical_df = activity_dao.get_critical_activities(project_id)
        near_critical_df = activity_dao.get_near_critical_activities(
            project_id, near_critical_threshold
        )

        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = self._sanitize_filename(project['Name'])
            output_filename = f"critical_path_{safe_name}_{timestamp}.pdf"

        output_path = self.pdf_dir / output_filename

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=self.page_size,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            leftMargin=MARGIN_LEFT,
            rightMargin=MARGIN_RIGHT,
        )

        content = []

        # Title
        content.append(Paragraph("Critical Path Analysis", self.styles['ReportTitle']))
        content.append(Spacer(1, 12))

        # Project Header
        content.extend(self._build_project_header(project))

        # Float Distribution Chart
        content.append(Spacer(1, 12))
        content.extend(self._build_float_distribution(activities_df))

        # Critical Activities
        content.append(Spacer(1, 12))
        content.append(
            Paragraph(
                f"Critical Activities (Float <= 0 days): {len(critical_df)}",
                self.styles['SectionHeading'],
            )
        )

        if not critical_df.empty:
            content.extend(self._build_critical_activity_table(critical_df))
        else:
            content.append(
                Paragraph("No critical activities found.", self.styles['BodyText'])
            )

        # Near-Critical Activities
        if include_near_critical:
            content.append(Spacer(1, 12))
            content.append(
                Paragraph(
                    f"Near-Critical Activities (Float 1-{int(near_critical_threshold)} days): {len(near_critical_df)}",
                    self.styles['SectionHeading'],
                )
            )

            if not near_critical_df.empty:
                content.extend(
                    self._build_critical_activity_table(near_critical_df.head(30))
                )
            else:
                content.append(
                    Paragraph(
                        "No near-critical activities found.", self.styles['BodyText']
                    )
                )

        doc.build(content, onFirstPage=self._add_footer, onLaterPages=self._add_footer)

        file_size = output_path.stat().st_size / 1024
        logger.info(f"Generated PDF: {output_path} ({file_size:.1f} KB)")

        return output_path

    # =========================================================================
    # Health Check Report
    # =========================================================================

    def generate_health_check_report(
        self,
        project_id: int,
        output_filename: Optional[str] = None,
    ) -> Path:
        """
        Generate schedule health check report (DCMA/AACE standards).

        Args:
            project_id: Project ObjectId
            output_filename: Optional custom filename

        Returns:
            Path to generated PDF
        """
        logger.info(f"Generating health check report for project {project_id}")

        manager = self._get_manager()

        project_dao = manager.get_project_dao()

        project_df = project_dao.get_project_by_object_id(project_id)
        if project_df.empty:
            raise ValueError(f"Project {project_id} not found")

        project = project_df.iloc[0]

        # Run health check analysis
        analyzer = ScheduleAnalyzer(manager)
        health_results = analyzer.run_health_check(project_id)

        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = self._sanitize_filename(project['Name'])
            output_filename = f"health_check_{safe_name}_{timestamp}.pdf"

        output_path = self.pdf_dir / output_filename

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=self.page_size,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            leftMargin=MARGIN_LEFT,
            rightMargin=MARGIN_RIGHT,
        )

        content = []

        # Title
        content.append(
            Paragraph("Schedule Health Check Report", self.styles['ReportTitle'])
        )
        content.append(Spacer(1, 12))

        # Project Header
        content.extend(self._build_project_header(project))

        # Overall Health Score
        content.append(Spacer(1, 12))
        content.extend(self._build_health_score_section(health_results))

        # Individual Checks
        content.append(Spacer(1, 12))
        content.extend(self._build_health_checks_detail(health_results))

        doc.build(content, onFirstPage=self._add_footer, onLaterPages=self._add_footer)

        file_size = output_path.stat().st_size / 1024
        logger.info(f"Generated PDF: {output_path} ({file_size:.1f} KB)")

        return output_path

    # =========================================================================
    # Comprehensive Report
    # =========================================================================

    def generate_comprehensive_report(
        self,
        project_id: int,
        output_filename: Optional[str] = None,
        sections: Optional[List[str]] = None,
    ) -> Path:
        """
        Generate multi-section comprehensive report.

        Args:
            project_id: Project ObjectId
            output_filename: Optional custom filename
            sections: List of sections to include
                     Options: 'summary', 'critical', 'health'
                     Default: all sections

        Returns:
            Path to generated PDF
        """
        if sections is None:
            sections = ['summary', 'critical', 'health']

        logger.info(
            f"Generating comprehensive report for project {project_id} "
            f"(sections: {sections})"
        )

        manager = self._get_manager()

        project_dao = manager.get_project_dao()
        activity_dao = manager.get_activity_dao()
        relationship_dao = manager.get_relationship_dao()

        project_df = project_dao.get_project_by_object_id(project_id)
        if project_df.empty:
            raise ValueError(f"Project {project_id} not found")

        project = project_df.iloc[0]
        activities_df = activity_dao.get_activities_for_project(project_id)
        critical_df = activity_dao.get_critical_activities(project_id)
        near_critical_df = activity_dao.get_near_critical_activities(project_id)
        relationships_df = relationship_dao.get_relationships(project_id)

        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = self._sanitize_filename(project['Name'])
            output_filename = f"comprehensive_{safe_name}_{timestamp}.pdf"

        output_path = self.pdf_dir / output_filename

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=self.page_size,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            leftMargin=MARGIN_LEFT,
            rightMargin=MARGIN_RIGHT,
        )

        content = []

        # Title
        content.append(
            Paragraph("Comprehensive Schedule Report", self.styles['ReportTitle'])
        )
        content.append(Spacer(1, 12))

        # Project Header
        content.extend(self._build_project_header(project))

        # Table of Contents
        content.append(Spacer(1, 12))
        toc_text = "Report Sections: " + ", ".join(
            s.replace('_', ' ').title() for s in sections
        )
        content.append(Paragraph(toc_text, self.styles['SmallText']))

        # Summary Section
        if 'summary' in sections:
            content.append(PageBreak())
            content.append(
                Paragraph("1. Schedule Summary", self.styles['SectionHeading'])
            )
            content.extend(
                self._build_statistics_section(
                    activities_df, critical_df, relationships_df
                )
            )
            content.extend(self._build_activity_table(activities_df, max_rows=30))

        # Critical Path Section
        if 'critical' in sections:
            content.append(PageBreak())
            content.append(
                Paragraph("2. Critical Path Analysis", self.styles['SectionHeading'])
            )
            content.extend(self._build_float_distribution(activities_df))
            content.append(Spacer(1, 12))

            content.append(
                Paragraph(
                    f"Critical Activities: {len(critical_df)}", self.styles['SubHeading']
                )
            )
            if not critical_df.empty:
                content.extend(self._build_critical_activity_table(critical_df.head(25)))

            content.append(Spacer(1, 12))
            content.append(
                Paragraph(
                    f"Near-Critical Activities: {len(near_critical_df)}",
                    self.styles['SubHeading'],
                )
            )
            if not near_critical_df.empty:
                content.extend(
                    self._build_critical_activity_table(near_critical_df.head(20))
                )

        # Health Check Section
        if 'health' in sections:
            content.append(PageBreak())
            content.append(
                Paragraph("3. Schedule Health Check", self.styles['SectionHeading'])
            )

            analyzer = ScheduleAnalyzer(manager)
            health_results = analyzer.run_health_check(project_id)

            content.extend(self._build_health_score_section(health_results))
            content.append(Spacer(1, 12))
            content.extend(self._build_health_checks_detail(health_results))

        doc.build(content, onFirstPage=self._add_footer, onLaterPages=self._add_footer)

        file_size = output_path.stat().st_size / 1024
        logger.info(f"Generated PDF: {output_path} ({file_size:.1f} KB)")

        return output_path

    # =========================================================================
    # Helper Methods - Content Builders
    # =========================================================================

    def _build_project_header(self, project: pd.Series) -> List:
        """Build project header section."""
        content = []

        header_data = [
            ['Project Name:', str(project.get('Name', 'N/A'))],
            ['Project ID:', str(project.get('Id', 'N/A'))],
            [
                'Report Generated:',
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ],
        ]

        # Add dates if available
        if 'PlannedStartDate' in project and project['PlannedStartDate']:
            header_data.append(
                ['Planned Start:', str(project['PlannedStartDate'])[:10]]
            )
        if 'PlannedFinishDate' in project and project['PlannedFinishDate']:
            header_data.append(
                ['Planned Finish:', str(project['PlannedFinishDate'])[:10]]
            )

        table = Table(header_data, colWidths=[1.5 * inch, 4 * inch])
        table.setStyle(
            TableStyle(
                [
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), FONT_BODY),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]
            )
        )

        content.append(table)
        content.append(Spacer(1, 12))

        return content

    def _build_statistics_section(
        self,
        activities_df: pd.DataFrame,
        critical_df: pd.DataFrame,
        relationships_df: pd.DataFrame,
    ) -> List:
        """Build statistics summary section."""
        content = []

        content.append(Paragraph("Schedule Statistics", self.styles['SectionHeading']))

        total_activities = len(activities_df)
        critical_count = len(critical_df)
        total_relationships = len(relationships_df)

        # Calculate status counts
        completed = len(activities_df[activities_df['Status'] == 'TK_Done'])
        in_progress = len(activities_df[activities_df['Status'] == 'TK_Active'])
        not_started = len(activities_df[activities_df['Status'] == 'TK_NotStart'])

        critical_pct = (
            (critical_count / total_activities * 100) if total_activities > 0 else 0
        )
        completed_pct = (
            (completed / total_activities * 100) if total_activities > 0 else 0
        )
        logic_density = (
            (total_relationships / total_activities) if total_activities > 0 else 0
        )

        stats_data = [
            [
                'Total Activities',
                'Critical',
                'Completed',
                'In Progress',
                'Not Started',
            ],
            [
                str(total_activities),
                f"{critical_count} ({critical_pct:.1f}%)",
                f"{completed} ({completed_pct:.1f}%)",
                str(in_progress),
                str(not_started),
            ],
        ]

        table = Table(stats_data, colWidths=[1.3 * inch] * 5)
        table.setStyle(get_table_style())

        content.append(table)
        content.append(Spacer(1, 8))

        # Logic density
        density_color = COLOR_LOW if logic_density >= TARGET_LOGIC_DENSITY else COLOR_HIGH
        density_text = (
            f"Logic Density: {logic_density:.2f} relationships per activity "
            f"(Target: >= {TARGET_LOGIC_DENSITY})"
        )
        content.append(Paragraph(density_text, self.styles['BodyText']))

        return content

    def _build_critical_path_section(
        self, critical_df: pd.DataFrame, max_rows: int = 20
    ) -> List:
        """Build critical path summary section."""
        content = []

        content.append(
            Paragraph(
                f"Critical Path Summary ({len(critical_df)} activities)",
                self.styles['SectionHeading'],
            )
        )

        if critical_df.empty:
            content.append(
                Paragraph("No critical activities found.", self.styles['BodyText'])
            )
            return content

        content.extend(self._build_critical_activity_table(critical_df.head(max_rows)))

        if len(critical_df) > max_rows:
            content.append(
                Paragraph(
                    f"... and {len(critical_df) - max_rows} more critical activities",
                    self.styles['SmallText'],
                )
            )

        return content

    def _build_critical_activity_table(self, df: pd.DataFrame) -> List:
        """Build table of critical/near-critical activities."""
        content = []

        if df.empty:
            return content

        headers = ['ID', 'Name', 'Duration', 'Start', 'Finish', 'Float']
        data = [headers]

        for _, row in df.iterrows():
            name = str(row.get('Name', ''))[:40]  # Truncate long names
            if len(str(row.get('Name', ''))) > 40:
                name += '...'

            start_date = str(row.get('StartDate', ''))[:10] if row.get('StartDate') else '-'
            finish_date = str(row.get('FinishDate', ''))[:10] if row.get('FinishDate') else '-'

            data.append(
                [
                    str(row.get('Id', '')),
                    name,
                    f"{row.get('PlannedDuration', 0):.1f}d",
                    start_date,
                    finish_date,
                    f"{row.get('TotalFloat', 0):.1f}d",
                ]
            )

        col_widths = [0.8 * inch, 2.5 * inch, 0.7 * inch, 0.9 * inch, 0.9 * inch, 0.6 * inch]
        table = Table(data, colWidths=col_widths)
        table.setStyle(get_table_style())

        content.append(table)

        return content

    def _build_activity_table(
        self, df: pd.DataFrame, max_rows: int = 50
    ) -> List:
        """Build general activity listing table."""
        content = []

        content.append(
            Paragraph(
                f"Activity Listing ({min(len(df), max_rows)} of {len(df)})",
                self.styles['SectionHeading'],
            )
        )

        if df.empty:
            content.append(Paragraph("No activities found.", self.styles['BodyText']))
            return content

        headers = ['ID', 'Name', 'Status', 'Duration', 'Float']
        data = [headers]

        for _, row in df.head(max_rows).iterrows():
            name = str(row.get('Name', ''))[:45]
            if len(str(row.get('Name', ''))) > 45:
                name += '...'

            status = str(row.get('Status', '')).replace('TK_', '')

            data.append(
                [
                    str(row.get('Id', '')),
                    name,
                    status,
                    f"{row.get('PlannedDuration', 0):.1f}d",
                    f"{row.get('TotalFloat', 0):.1f}d",
                ]
            )

        col_widths = [0.9 * inch, 3.0 * inch, 0.9 * inch, 0.8 * inch, 0.7 * inch]
        table = Table(data, colWidths=col_widths)
        table.setStyle(get_table_style())

        content.append(table)

        return content

    def _build_float_distribution(self, activities_df: pd.DataFrame) -> List:
        """Build float distribution summary."""
        content = []

        content.append(
            Paragraph("Float Distribution", self.styles['SectionHeading'])
        )

        if activities_df.empty:
            content.append(
                Paragraph("No activities available.", self.styles['BodyText'])
            )
            return content

        # Calculate distribution
        critical = len(activities_df[activities_df['TotalFloat'] <= 0])
        near_critical = len(
            activities_df[
                (activities_df['TotalFloat'] > 0)
                & (activities_df['TotalFloat'] <= THRESHOLD_NEAR_CRITICAL)
            ]
        )
        low_float = len(
            activities_df[
                (activities_df['TotalFloat'] > THRESHOLD_NEAR_CRITICAL)
                & (activities_df['TotalFloat'] <= THRESHOLD_LOW_FLOAT)
            ]
        )
        moderate_plus = len(
            activities_df[activities_df['TotalFloat'] > THRESHOLD_LOW_FLOAT]
        )

        total = len(activities_df)

        dist_data = [
            ['Category', 'Float Range', 'Count', 'Percentage'],
            [
                'Critical',
                '<= 0 days',
                str(critical),
                f"{critical/total*100:.1f}%" if total > 0 else "0%",
            ],
            [
                'Near-Critical',
                f'1-{THRESHOLD_NEAR_CRITICAL} days',
                str(near_critical),
                f"{near_critical/total*100:.1f}%" if total > 0 else "0%",
            ],
            [
                'Low Float',
                f'{THRESHOLD_NEAR_CRITICAL+1}-{THRESHOLD_LOW_FLOAT} days',
                str(low_float),
                f"{low_float/total*100:.1f}%" if total > 0 else "0%",
            ],
            [
                'Moderate+',
                f'> {THRESHOLD_LOW_FLOAT} days',
                str(moderate_plus),
                f"{moderate_plus/total*100:.1f}%" if total > 0 else "0%",
            ],
        ]

        table = Table(dist_data, colWidths=[1.2 * inch, 1.5 * inch, 0.8 * inch, 1.0 * inch])
        base_style = get_table_style()

        # Add color coding for categories
        style_commands = list(base_style.getCommands())
        style_commands.extend([
            ('BACKGROUND', (0, 1), (0, 1), COLOR_CRITICAL),
            ('TEXTCOLOR', (0, 1), (0, 1), colors.white),
            ('BACKGROUND', (0, 2), (0, 2), COLOR_HIGH),
            ('TEXTCOLOR', (0, 2), (0, 2), colors.white),
            ('BACKGROUND', (0, 3), (0, 3), COLOR_MEDIUM),
            ('BACKGROUND', (0, 4), (0, 4), COLOR_LOW),
            ('TEXTCOLOR', (0, 4), (0, 4), colors.white),
        ])

        table.setStyle(TableStyle(style_commands))
        content.append(table)

        return content

    def _build_health_score_section(self, health_results: Dict[str, Any]) -> List:
        """Build overall health score section."""
        content = []

        score = health_results.get('health_score', 0)
        score_color = get_health_color(score)

        content.append(Paragraph("Overall Health Score", self.styles['SectionHeading']))

        # Score display
        score_text = f"{score:.0f}/100"

        if score >= 90:
            rating = "Excellent"
        elif score >= 75:
            rating = "Good"
        elif score >= 50:
            rating = "Fair"
        else:
            rating = "Needs Improvement"

        score_data = [
            [score_text],
            [rating],
        ]

        table = Table(score_data, colWidths=[2 * inch])
        table.setStyle(
            TableStyle(
                [
                    ('BACKGROUND', (0, 0), (-1, -1), score_color),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
                    ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (0, 0), 24),
                    ('FONTSIZE', (0, 1), (0, 1), 12),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ]
            )
        )

        content.append(table)
        content.append(Spacer(1, 8))

        # Summary stats
        summary_text = (
            f"Total Activities: {health_results.get('total_activities', 0)} | "
            f"Total Relationships: {health_results.get('total_relationships', 0)}"
        )
        content.append(Paragraph(summary_text, self.styles['BodyText']))

        return content

    def _build_health_checks_detail(self, health_results: Dict[str, Any]) -> List:
        """Build detailed health check results."""
        content = []

        checks = health_results.get('checks', {})

        content.append(Paragraph("Check Results", self.styles['SectionHeading']))

        check_data = [['Check', 'Status', 'Count', 'Details']]

        # Open Ends
        open_ends = checks.get('open_ends', {})
        open_start = open_ends.get('open_start_count', 0)
        open_finish = open_ends.get('open_finish_count', 0)

        open_status = 'Pass' if (open_start == 0 and open_finish == 0) else 'Warning'
        check_data.append(
            [
                'Open Ends',
                open_status,
                f"{open_start + open_finish}",
                f"Start: {open_start}, Finish: {open_finish}",
            ]
        )

        # Constraints
        constraints = checks.get('constraints', {})
        hard_count = constraints.get('hard_constraint_count', 0)
        constraint_status = 'Pass' if hard_count == 0 else 'Warning'
        check_data.append(
            ['Hard Constraints', constraint_status, str(hard_count), 'Mandatory constraints']
        )

        # Float
        float_check = checks.get('float', {})
        neg_float = float_check.get('negative_float_count', 0)
        float_status = 'Pass' if neg_float == 0 else 'Critical'
        min_float = float_check.get('min_float', 0)
        check_data.append(
            [
                'Negative Float',
                float_status,
                str(neg_float),
                f"Min float: {min_float:.1f} days",
            ]
        )

        # Duration/Lag
        dur_lag = checks.get('duration_lag', {})
        high_dur = dur_lag.get('high_duration_count', 0)
        neg_lag = dur_lag.get('negative_lag_count', 0)

        dur_status = 'Pass' if high_dur == 0 else 'Info'
        check_data.append(
            [
                'High Duration',
                dur_status,
                str(high_dur),
                f"> {THRESHOLD_HIGH_DURATION} days",
            ]
        )

        lag_status = 'Pass' if neg_lag == 0 else 'Warning'
        check_data.append(['Negative Lag', lag_status, str(neg_lag), 'Lead relationships'])

        # Progress
        progress = checks.get('progress', {})
        missing_start = progress.get('missing_actual_start_count', 0)
        missing_finish = progress.get('missing_actual_finish_count', 0)

        prog_status = 'Pass' if (missing_start == 0 and missing_finish == 0) else 'Warning'
        check_data.append(
            [
                'Progress Integrity',
                prog_status,
                f"{missing_start + missing_finish}",
                f"Missing dates: start={missing_start}, finish={missing_finish}",
            ]
        )

        table = Table(
            check_data, colWidths=[1.3 * inch, 0.7 * inch, 0.6 * inch, 2.5 * inch]
        )

        style_commands = list(get_table_style().getCommands())

        # Color code status column
        for i, row in enumerate(check_data[1:], start=1):
            status = row[1]
            if status == 'Pass':
                style_commands.append(('BACKGROUND', (1, i), (1, i), COLOR_LOW))
                style_commands.append(('TEXTCOLOR', (1, i), (1, i), colors.white))
            elif status == 'Warning':
                style_commands.append(('BACKGROUND', (1, i), (1, i), COLOR_HIGH))
                style_commands.append(('TEXTCOLOR', (1, i), (1, i), colors.white))
            elif status == 'Critical':
                style_commands.append(('BACKGROUND', (1, i), (1, i), COLOR_CRITICAL))
                style_commands.append(('TEXTCOLOR', (1, i), (1, i), colors.white))
            else:  # Info
                style_commands.append(('BACKGROUND', (1, i), (1, i), COLOR_INFO))
                style_commands.append(('TEXTCOLOR', (1, i), (1, i), colors.white))

        table.setStyle(TableStyle(style_commands))
        content.append(table)

        return content

    # =========================================================================
    # Helper Methods - Utilities
    # =========================================================================

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use in filenames."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name.strip()[:50]  # Limit length

    def _add_footer(self, canvas, doc):
        """Add footer to each page."""
        canvas.saveState()

        # Footer text
        footer_text = (
            f"Generated by P6 Planning Integration | "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | "
            f"Page {canvas.getPageNumber()}"
        )

        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#999999'))
        canvas.drawCentredString(
            doc.pagesize[0] / 2,
            0.4 * inch,
            footer_text,
        )

        canvas.restoreState()


# =============================================================================
# Convenience Functions
# =============================================================================


def generate_pdf_report(
    project_id: int,
    report_type: str = 'summary',
    output_filename: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Path:
    """
    Convenience function to generate a PDF report.

    Args:
        project_id: Project ObjectId
        report_type: Type of report ('summary', 'critical', 'health', 'comprehensive')
        output_filename: Optional custom filename
        db_path: Optional database path (uses config default if not specified)

    Returns:
        Path to generated PDF

    Example:
        >>> path = generate_pdf_report(123, 'summary')
        >>> print(f"Report: {path}")
    """
    with SQLiteManager(db_path=db_path) as manager:
        pdf_gen = PDFGenerator()
        pdf_gen.set_manager(manager)

        if report_type == 'summary':
            return pdf_gen.generate_schedule_summary(project_id, output_filename)
        elif report_type == 'critical':
            return pdf_gen.generate_critical_path_report(project_id, output_filename)
        elif report_type == 'health':
            return pdf_gen.generate_health_check_report(project_id, output_filename)
        elif report_type == 'comprehensive':
            return pdf_gen.generate_comprehensive_report(project_id, output_filename)
        else:
            raise ValueError(
                f"Unknown report type: {report_type}. "
                f"Options: summary, critical, health, comprehensive"
            )
