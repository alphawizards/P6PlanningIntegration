"""
Tests for PDF Generator module.

Tests cover:
- PDF styles and configuration
- Schedule summary report generation
- Critical path report generation
- Health check report generation
- Comprehensive report generation
"""

import pytest
import pandas as pd
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

from src.reporting.pdf_generator import PDFGenerator, generate_pdf_report
from src.reporting.pdf_styles import (
    get_custom_styles,
    get_table_style,
    get_health_color,
    get_float_color,
    get_severity_color,
    CORPORATE_PRIMARY,
    COLOR_CRITICAL,
    COLOR_LOW,
    THRESHOLD_NEAR_CRITICAL,
)


# =============================================================================
# Unit Tests - No Database Required
# =============================================================================


class TestPDFStyles:
    """Test PDF styling configuration."""

    def test_get_custom_styles_returns_dict(self):
        """Test that custom styles returns a dictionary."""
        styles = get_custom_styles()
        assert isinstance(styles, dict)

    def test_custom_styles_has_required_keys(self):
        """Test that required style keys are present."""
        styles = get_custom_styles()
        required_keys = [
            'ReportTitle',
            'SectionHeading',
            'SubHeading',
            'BodyText',
            'SmallText',
            'TableHeader',
            'TableCell',
        ]
        for key in required_keys:
            assert key in styles, f"Missing style: {key}"

    def test_get_table_style_returns_style(self):
        """Test that table style returns a valid style."""
        style = get_table_style()
        # TableStyle from ReportLab
        assert hasattr(style, 'getCommands')

    def test_get_health_color_excellent(self):
        """Test health color for excellent score."""
        color = get_health_color(95)
        assert color == COLOR_LOW  # Green

    def test_get_health_color_poor(self):
        """Test health color for poor score."""
        color = get_health_color(30)
        assert color == COLOR_CRITICAL  # Red

    def test_get_float_color_critical(self):
        """Test float color for critical activities."""
        color = get_float_color(-5)
        # Should be critical (red)
        assert color is not None

    def test_get_float_color_moderate(self):
        """Test float color for moderate float."""
        color = get_float_color(45)
        # Should be moderate (light green)
        assert color is not None

    def test_get_severity_color_returns_valid(self):
        """Test severity color lookup."""
        for severity in ['critical', 'high', 'medium', 'low', 'info']:
            color = get_severity_color(severity)
            assert color is not None


class TestPDFGeneratorInit:
    """Test PDF generator initialization."""

    def test_init_creates_output_directory(self):
        """Test that initialization creates the PDF output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_gen = PDFGenerator(base_dir=tmpdir)
            assert pdf_gen.pdf_dir.exists()

    def test_init_default_page_size(self):
        """Test default page size is letter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_gen = PDFGenerator(base_dir=tmpdir)
            # Letter size is (612, 792) points
            assert pdf_gen.page_size[0] == 612
            assert pdf_gen.page_size[1] == 792

    def test_init_landscape_mode(self):
        """Test landscape mode swaps dimensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_gen = PDFGenerator(base_dir=tmpdir, landscape_mode=True)
            # Landscape swaps width and height
            assert pdf_gen.page_size[0] == 792
            assert pdf_gen.page_size[1] == 612

    def test_styles_loaded(self):
        """Test that custom styles are loaded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_gen = PDFGenerator(base_dir=tmpdir)
            assert isinstance(pdf_gen.styles, dict)
            assert 'ReportTitle' in pdf_gen.styles

    def test_manager_not_set_raises_error(self):
        """Test that using generator without manager raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_gen = PDFGenerator(base_dir=tmpdir)
            with pytest.raises(ValueError, match="Database manager not set"):
                pdf_gen._get_manager()


class TestPDFGeneratorHelpers:
    """Test PDF generator helper methods."""

    def test_sanitize_filename_removes_invalid_chars(self):
        """Test filename sanitization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_gen = PDFGenerator(base_dir=tmpdir)

            # Test various invalid characters
            result = pdf_gen._sanitize_filename("Project: Test/Name")
            assert ':' not in result
            assert '/' not in result

    def test_sanitize_filename_limits_length(self):
        """Test that filename is limited to 50 chars."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_gen = PDFGenerator(base_dir=tmpdir)

            long_name = "A" * 100
            result = pdf_gen._sanitize_filename(long_name)
            assert len(result) <= 50


# =============================================================================
# Integration Tests - Require Database
# =============================================================================


@pytest.mark.integration
class TestPDFGeneratorWithDatabase:
    """Integration tests for PDF generation with live database."""

    @pytest.fixture
    def pdf_generator(self, sqlite_manager):
        """Create PDF generator with manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_gen = PDFGenerator(base_dir=tmpdir)
            pdf_gen.set_manager(sqlite_manager)
            yield pdf_gen
            # Cleanup is handled by TemporaryDirectory

    @pytest.fixture
    def test_project_id(self, project_dao):
        """Get a valid project ID for testing."""
        projects = project_dao.get_active_projects()
        if projects.empty:
            pytest.skip("No projects available for testing")
        return int(projects.iloc[0]['ObjectId'])

    def test_generate_schedule_summary(self, pdf_generator, test_project_id):
        """Test schedule summary PDF generation."""
        output_path = pdf_generator.generate_schedule_summary(
            project_id=test_project_id,
            include_activities=True,
            include_critical_path=True,
        )

        assert output_path.exists()
        assert output_path.suffix == '.pdf'
        assert output_path.stat().st_size > 1000  # Non-trivial file

    def test_generate_schedule_summary_custom_filename(
        self, pdf_generator, test_project_id
    ):
        """Test schedule summary with custom filename."""
        custom_name = "test_summary.pdf"
        output_path = pdf_generator.generate_schedule_summary(
            project_id=test_project_id,
            output_filename=custom_name,
        )

        assert output_path.exists()
        assert output_path.name == custom_name

    def test_generate_critical_path_report(self, pdf_generator, test_project_id):
        """Test critical path PDF generation."""
        output_path = pdf_generator.generate_critical_path_report(
            project_id=test_project_id,
            include_near_critical=True,
        )

        assert output_path.exists()
        assert output_path.suffix == '.pdf'
        assert 'critical_path' in output_path.stem

    def test_generate_health_check_report(self, pdf_generator, test_project_id):
        """Test health check PDF generation."""
        output_path = pdf_generator.generate_health_check_report(
            project_id=test_project_id,
        )

        assert output_path.exists()
        assert output_path.suffix == '.pdf'
        assert 'health_check' in output_path.stem

    def test_generate_comprehensive_report(self, pdf_generator, test_project_id):
        """Test comprehensive PDF generation with all sections."""
        output_path = pdf_generator.generate_comprehensive_report(
            project_id=test_project_id,
            sections=['summary', 'critical', 'health'],
        )

        assert output_path.exists()
        assert output_path.suffix == '.pdf'
        assert 'comprehensive' in output_path.stem
        # Comprehensive report should be larger
        assert output_path.stat().st_size > 5000

    def test_generate_comprehensive_report_single_section(
        self, pdf_generator, test_project_id
    ):
        """Test comprehensive report with single section."""
        output_path = pdf_generator.generate_comprehensive_report(
            project_id=test_project_id,
            sections=['summary'],
        )

        assert output_path.exists()

    def test_invalid_project_raises_error(self, pdf_generator):
        """Test that invalid project ID raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            pdf_generator.generate_schedule_summary(project_id=999999999)


@pytest.mark.integration
class TestConvenienceFunction:
    """Test the generate_pdf_report convenience function."""

    @pytest.fixture
    def test_project_id(self, project_dao):
        """Get a valid project ID for testing."""
        projects = project_dao.get_active_projects()
        if projects.empty:
            pytest.skip("No projects available for testing")
        return int(projects.iloc[0]['ObjectId'])

    def test_generate_pdf_report_summary(self, test_project_id):
        """Test convenience function for summary report."""
        output_path = generate_pdf_report(
            project_id=test_project_id,
            report_type='summary',
        )

        assert output_path.exists()
        # Cleanup
        output_path.unlink()

    def test_generate_pdf_report_invalid_type(self, test_project_id):
        """Test that invalid report type raises error."""
        with pytest.raises(ValueError, match="Unknown report type"):
            generate_pdf_report(
                project_id=test_project_id,
                report_type='invalid_type',
            )


# =============================================================================
# Report Content Tests
# =============================================================================


@pytest.mark.integration
class TestReportContent:
    """Test that report content is correctly generated."""

    @pytest.fixture
    def pdf_generator(self, sqlite_manager):
        """Create PDF generator with manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_gen = PDFGenerator(base_dir=tmpdir)
            pdf_gen.set_manager(sqlite_manager)
            yield pdf_gen

    @pytest.fixture
    def test_project_id(self, project_dao):
        """Get a valid project ID for testing."""
        projects = project_dao.get_active_projects()
        if projects.empty:
            pytest.skip("No projects available for testing")
        return int(projects.iloc[0]['ObjectId'])

    def test_project_header_builds(self, pdf_generator, project_dao, test_project_id):
        """Test project header content building."""
        project_df = project_dao.get_project_by_object_id(test_project_id)
        project = project_df.iloc[0]

        content = pdf_generator._build_project_header(project)

        assert len(content) > 0
        # Should have at least table and spacer
        assert len(content) >= 2

    def test_statistics_section_builds(
        self, pdf_generator, activity_dao, relationship_dao, test_project_id
    ):
        """Test statistics section content building."""
        activities = activity_dao.get_activities_for_project(test_project_id)
        critical = activity_dao.get_critical_activities(test_project_id)
        relationships = relationship_dao.get_relationships(test_project_id)

        content = pdf_generator._build_statistics_section(
            activities, critical, relationships
        )

        assert len(content) > 0

    def test_critical_path_section_builds(
        self, pdf_generator, activity_dao, test_project_id
    ):
        """Test critical path section content building."""
        critical = activity_dao.get_critical_activities(test_project_id)

        content = pdf_generator._build_critical_path_section(critical, max_rows=10)

        assert len(content) > 0

    def test_float_distribution_builds(
        self, pdf_generator, activity_dao, test_project_id
    ):
        """Test float distribution content building."""
        activities = activity_dao.get_activities_for_project(test_project_id)

        content = pdf_generator._build_float_distribution(activities)

        assert len(content) > 0
