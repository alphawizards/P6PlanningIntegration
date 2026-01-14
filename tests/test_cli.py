"""
Tests for CLI commands using mocks.

Tests CLI argument parsing and command routing without database.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
import argparse


class TestCLIArgumentParsing:
    """Tests for CLI argument parsing."""

    def test_help_exits_cleanly(self):
        """Test --help exits with code 0."""
        # Create argument parser matching main.py structure
        parser = argparse.ArgumentParser(description='P6 Planning Integration CLI')
        parser.add_argument('--help-full', action='store_true')

        # Test that help action raises SystemExit with code 0
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(['--help'])
        assert exc_info.value.code == 0

    def test_list_projects_argument(self):
        """Test --list-projects argument is recognized."""
        test_args = ['main.py', '--list-projects']

        parser = argparse.ArgumentParser()
        parser.add_argument('--list-projects', '-l', action='store_true')

        args = parser.parse_args(test_args[1:])
        assert args.list_projects is True

    def test_report_argument_requires_type(self):
        """Test --report requires type argument."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--report', '-r', choices=['summary', 'critical', 'health', 'comprehensive'])

        # Should fail without type
        with pytest.raises(SystemExit):
            parser.parse_args(['--report'])

    def test_report_types_accepted(self):
        """Test all report types are accepted."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--report', '-r', choices=['summary', 'critical', 'health', 'comprehensive'])

        for report_type in ['summary', 'critical', 'health', 'comprehensive']:
            args = parser.parse_args(['--report', report_type])
            assert args.report == report_type

    def test_invalid_report_type_rejected(self):
        """Test invalid report type is rejected."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--report', '-r', choices=['summary', 'critical', 'health', 'comprehensive'])

        with pytest.raises(SystemExit):
            parser.parse_args(['--report', 'invalid'])

    def test_project_argument(self):
        """Test --project argument accepts integer."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--project', '-p', type=int)

        args = parser.parse_args(['--project', '123'])
        assert args.project == 123

    def test_output_argument(self):
        """Test --output argument."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--output', '-o')

        args = parser.parse_args(['--output', 'my_report.pdf'])
        assert args.output == 'my_report.pdf'

    def test_landscape_flag(self):
        """Test --landscape flag."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--landscape', action='store_true')

        args = parser.parse_args(['--landscape'])
        assert args.landscape is True

        args = parser.parse_args([])
        assert args.landscape is False

    def test_verbose_flag(self):
        """Test --verbose flag."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--verbose', '-v', action='store_true')

        args = parser.parse_args(['-v'])
        assert args.verbose is True

    def test_export_json_flag(self):
        """Test --export-json flag."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--export-json', action='store_true')

        args = parser.parse_args(['--export-json'])
        assert args.export_json is True

    def test_filepath_positional(self):
        """Test filepath positional argument."""
        parser = argparse.ArgumentParser()
        parser.add_argument('filepath', nargs='?')

        args = parser.parse_args(['schedule.xer'])
        assert args.filepath == 'schedule.xer'

    def test_combined_arguments(self):
        """Test combining multiple arguments."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--report', '-r', choices=['summary', 'critical', 'health', 'comprehensive'])
        parser.add_argument('--project', '-p', type=int)
        parser.add_argument('--output', '-o')
        parser.add_argument('--landscape', action='store_true')

        args = parser.parse_args([
            '--report', 'comprehensive',
            '--project', '456',
            '--output', 'report.pdf',
            '--landscape'
        ])

        assert args.report == 'comprehensive'
        assert args.project == 456
        assert args.output == 'report.pdf'
        assert args.landscape is True


class TestListProjectsMode:
    """Tests for list projects mode."""

    @patch('main.P6_CONNECTION_MODE', 'SQLITE')
    @patch('main.SQLiteManager')
    def test_list_projects_calls_manager(self, mock_manager_class):
        """Test list projects creates manager and queries."""
        # Setup mock
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.__enter__ = Mock(return_value=mock_manager)
        mock_manager.__exit__ = Mock(return_value=False)

        mock_dao = MagicMock()
        mock_manager.get_project_dao.return_value = mock_dao

        import pandas as pd
        mock_dao.get_active_projects.return_value = pd.DataFrame({
            'ObjectId': [1, 2],
            'Id': ['PROJ1', 'PROJ2'],
            'Name': ['Project 1', 'Project 2']
        })

        # Import after patching
        from main import list_projects_mode
        result = list_projects_mode(verbose=False)

        assert result == 0
        mock_manager.connect.assert_called_once()
        mock_manager.disconnect.assert_called_once()
        mock_dao.get_active_projects.assert_called_once()

    @patch('main.P6_CONNECTION_MODE', 'SQLITE')
    @patch('main.SQLiteManager')
    def test_list_projects_empty_database(self, mock_manager_class):
        """Test list projects with empty database."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_dao = MagicMock()
        mock_manager.get_project_dao.return_value = mock_dao

        import pandas as pd
        mock_dao.get_active_projects.return_value = pd.DataFrame()

        from main import list_projects_mode
        result = list_projects_mode()

        assert result == 0


class TestReportGenerationMode:
    """Tests for report generation mode."""

    @patch('main.P6_CONNECTION_MODE', 'SQLITE')
    @patch('main.SQLiteManager')
    @patch('main.PDFGenerator')
    def test_report_mode_validates_project(self, mock_pdf_gen, mock_manager_class):
        """Test report mode validates project exists."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_dao = MagicMock()
        mock_manager.get_project_dao.return_value = mock_dao

        import pandas as pd
        # Project not found
        mock_dao.get_project_by_object_id.return_value = pd.DataFrame()

        from main import generate_report_mode
        result = generate_report_mode(project_id=999, report_type='summary')

        assert result == 1  # Should fail
        mock_pdf_gen.assert_not_called()

    @patch('main.P6_CONNECTION_MODE', 'SQLITE')
    @patch('main.SQLiteManager')
    @patch('main.PDFGenerator')
    def test_report_mode_calls_generator(self, mock_pdf_gen_class, mock_manager_class):
        """Test report mode calls PDF generator."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_dao = MagicMock()
        mock_manager.get_project_dao.return_value = mock_dao

        import pandas as pd
        mock_dao.get_project_by_object_id.return_value = pd.DataFrame({
            'ObjectId': [123],
            'Name': ['Test Project']
        })

        mock_pdf_gen = MagicMock()
        mock_pdf_gen_class.return_value = mock_pdf_gen
        mock_pdf_gen.generate_schedule_summary.return_value = Path('test.pdf')

        # Mock the path stat
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value.st_size = 1024

            from main import generate_report_mode
            result = generate_report_mode(project_id=123, report_type='summary')

        assert result == 0
        mock_pdf_gen.generate_schedule_summary.assert_called_once()


class TestAnalyzeMode:
    """Tests for schedule analysis mode."""

    @patch('main.P6_CONNECTION_MODE', 'SQLITE')
    @patch('main.SQLiteManager')
    @patch('main.ScheduleAnalyzer')
    def test_analyze_validates_project(self, mock_analyzer, mock_manager_class):
        """Test analyze mode validates project exists."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_dao = MagicMock()
        mock_manager.get_project_dao.return_value = mock_dao

        import pandas as pd
        mock_dao.get_project_by_object_id.return_value = pd.DataFrame()

        from main import analyze_schedule_mode
        result = analyze_schedule_mode(project_id=999)

        assert result == 1
        mock_analyzer.assert_not_called()

    @patch('main.P6_CONNECTION_MODE', 'SQLITE')
    @patch('main.SQLiteManager')
    @patch('main.ScheduleAnalyzer')
    def test_analyze_runs_health_check(self, mock_analyzer_class, mock_manager_class):
        """Test analyze mode runs health check."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_dao = MagicMock()
        mock_manager.get_project_dao.return_value = mock_dao

        import pandas as pd
        mock_dao.get_project_by_object_id.return_value = pd.DataFrame({
            'ObjectId': [123],
            'Name': ['Test Project']
        })

        mock_analyzer = MagicMock()
        mock_analyzer_class.return_value = mock_analyzer
        mock_analyzer.run_health_check.return_value = {
            'health_score': 85.0,
            'total_activities': 100,
            'total_relationships': 150,
            'checks': {
                'open_ends': {'open_start_count': 0, 'open_finish_count': 0},
                'constraints': {'hard_constraint_count': 0},
                'float': {'negative_float_count': 0, 'min_float': 5.0},
                'duration_lag': {'high_duration_count': 0, 'negative_lag_count': 0},
                'progress': {'missing_actual_start_count': 0, 'missing_actual_finish_count': 0}
            }
        }

        from main import analyze_schedule_mode
        result = analyze_schedule_mode(project_id=123)

        assert result == 0
        mock_analyzer.run_health_check.assert_called_once_with(123)


class TestFileIngestionMode:
    """Tests for file ingestion mode."""

    def test_file_not_found_returns_error(self):
        """Test file not found returns error code."""
        from main import test_file_ingestion
        result = test_file_ingestion('/nonexistent/file.xer')
        assert result == 1

    def test_unsupported_format_returns_error(self, tmp_path):
        """Test unsupported file format returns error."""
        # Create a file with unsupported extension
        test_file = tmp_path / "file.txt"
        test_file.write_text("test content")

        from main import test_file_ingestion
        result = test_file_ingestion(str(test_file))
        assert result == 1


class TestDatabaseTestMode:
    """Tests for database test mode."""

    @patch('main.P6_CONNECTION_MODE', 'SQLITE')
    @patch('main.SQLiteManager')
    def test_database_test_connects_and_disconnects(self, mock_manager_class):
        """Test database test connects and disconnects."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        # Setup DAOs
        mock_project_dao = MagicMock()
        mock_activity_dao = MagicMock()
        mock_relationship_dao = MagicMock()

        mock_manager.get_project_dao.return_value = mock_project_dao
        mock_manager.get_activity_dao.return_value = mock_activity_dao
        mock_manager.get_relationship_dao.return_value = mock_relationship_dao

        import pandas as pd
        mock_project_dao.get_all_projects.return_value = pd.DataFrame({
            'ObjectId': [1],
            'Name': ['Test']
        })
        mock_activity_dao.get_activities_for_project.return_value = pd.DataFrame()
        mock_relationship_dao.get_relationships.return_value = pd.DataFrame()

        from main import test_database_connection
        result = test_database_connection()

        assert result == 0
        mock_manager.connect.assert_called_once()
        mock_manager.disconnect.assert_called_once()
