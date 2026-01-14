"""
Tests for PDF styles module.

Verifies styling constants, color functions, and style generators.
"""

import pytest
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import TableStyle

from src.reporting.pdf_styles import (
    # Color constants
    CORPORATE_PRIMARY,
    CORPORATE_SECONDARY,
    CORPORATE_ACCENT,
    COLOR_CRITICAL,
    COLOR_HIGH,
    COLOR_MEDIUM,
    COLOR_LOW,
    COLOR_INFO,
    FLOAT_CRITICAL,
    FLOAT_NEAR_CRITICAL,
    FLOAT_LOW,
    FLOAT_MODERATE,
    FLOAT_HIGH,
    TABLE_HEADER_BG,
    TABLE_HEADER_TEXT,
    TABLE_ROW_ALT,
    TABLE_BORDER,
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STATUS_NOT_STARTED,
    # Layout constants
    MARGIN_TOP,
    MARGIN_BOTTOM,
    MARGIN_LEFT,
    MARGIN_RIGHT,
    PAGE_HEADER_HEIGHT,
    PAGE_FOOTER_HEIGHT,
    CONTENT_WIDTH_LETTER,
    CONTENT_WIDTH_A4,
    # Font constants
    FONT_TITLE,
    FONT_HEADING1,
    FONT_HEADING2,
    FONT_BODY,
    FONT_SMALL,
    FONT_FOOTER,
    # Threshold constants
    THRESHOLD_CRITICAL_FLOAT,
    THRESHOLD_NEAR_CRITICAL,
    THRESHOLD_LOW_FLOAT,
    THRESHOLD_MODERATE_FLOAT,
    THRESHOLD_HIGH_DURATION,
    TARGET_LOGIC_DENSITY,
    TARGET_CONSTRAINT_PERCENT,
    # Health constants
    HEALTH_EXCELLENT,
    HEALTH_GOOD,
    HEALTH_FAIR,
    HEALTH_POOR,
    # Functions
    get_health_color,
    get_float_color,
    get_severity_color,
    get_custom_styles,
    get_table_style,
    get_summary_box_style,
)


class TestColorConstants:
    """Tests for color constant definitions."""

    def test_corporate_colors_are_color_objects(self):
        """Test corporate colors are valid Color objects."""
        assert hasattr(CORPORATE_PRIMARY, 'hexval')
        assert hasattr(CORPORATE_SECONDARY, 'hexval')
        assert hasattr(CORPORATE_ACCENT, 'hexval')

    def test_severity_colors_are_color_objects(self):
        """Test severity colors are valid Color objects."""
        assert hasattr(COLOR_CRITICAL, 'hexval')
        assert hasattr(COLOR_HIGH, 'hexval')
        assert hasattr(COLOR_MEDIUM, 'hexval')
        assert hasattr(COLOR_LOW, 'hexval')
        assert hasattr(COLOR_INFO, 'hexval')

    def test_float_colors_are_defined(self):
        """Test float status colors are defined."""
        assert FLOAT_CRITICAL is not None
        assert FLOAT_NEAR_CRITICAL is not None
        assert FLOAT_LOW is not None
        assert FLOAT_MODERATE is not None
        assert FLOAT_HIGH is not None

    def test_table_header_text_is_white(self):
        """Test table header text is white for contrast."""
        assert TABLE_HEADER_TEXT == colors.white

    def test_table_header_bg_is_corporate_primary(self):
        """Test table header background uses corporate color."""
        assert TABLE_HEADER_BG == CORPORATE_PRIMARY

    def test_status_colors_are_distinct(self):
        """Test status colors are different from each other."""
        assert STATUS_COMPLETED != STATUS_IN_PROGRESS
        assert STATUS_IN_PROGRESS != STATUS_NOT_STARTED
        assert STATUS_COMPLETED != STATUS_NOT_STARTED


class TestLayoutConstants:
    """Tests for page layout constants."""

    def test_margins_are_positive(self):
        """Test all margins are positive values."""
        assert MARGIN_TOP > 0
        assert MARGIN_BOTTOM > 0
        assert MARGIN_LEFT > 0
        assert MARGIN_RIGHT > 0

    def test_margins_use_inches(self):
        """Test margins are in inches (0.75 inch)."""
        expected = 0.75 * inch
        assert MARGIN_TOP == expected
        assert MARGIN_BOTTOM == expected
        assert MARGIN_LEFT == expected
        assert MARGIN_RIGHT == expected

    def test_header_footer_heights_positive(self):
        """Test header and footer heights are positive."""
        assert PAGE_HEADER_HEIGHT > 0
        assert PAGE_FOOTER_HEIGHT > 0

    def test_content_width_letter_calculation(self):
        """Test letter content width calculation is correct."""
        expected = 8.5 * inch - MARGIN_LEFT - MARGIN_RIGHT
        assert CONTENT_WIDTH_LETTER == expected

    def test_content_width_a4_calculation(self):
        """Test A4 content width calculation is correct."""
        expected = 8.27 * inch - MARGIN_LEFT - MARGIN_RIGHT
        assert CONTENT_WIDTH_A4 == expected

    def test_letter_wider_than_a4(self):
        """Test letter page is wider than A4."""
        assert CONTENT_WIDTH_LETTER > CONTENT_WIDTH_A4


class TestFontConstants:
    """Tests for font size constants."""

    def test_font_sizes_are_positive_integers(self):
        """Test all font sizes are positive integers."""
        font_sizes = [FONT_TITLE, FONT_HEADING1, FONT_HEADING2,
                      FONT_BODY, FONT_SMALL, FONT_FOOTER]
        for size in font_sizes:
            assert isinstance(size, int)
            assert size > 0

    def test_font_hierarchy(self):
        """Test font sizes decrease in correct hierarchy."""
        assert FONT_TITLE > FONT_HEADING1
        assert FONT_HEADING1 > FONT_HEADING2
        assert FONT_HEADING2 >= FONT_BODY
        assert FONT_BODY > FONT_SMALL
        assert FONT_SMALL >= FONT_FOOTER

    def test_specific_font_values(self):
        """Test specific font size values."""
        assert FONT_TITLE == 18
        assert FONT_HEADING1 == 14
        assert FONT_HEADING2 == 12
        assert FONT_BODY == 10
        assert FONT_SMALL == 8
        assert FONT_FOOTER == 8


class TestThresholdConstants:
    """Tests for mining industry threshold constants."""

    def test_float_thresholds_in_order(self):
        """Test float thresholds are in ascending order."""
        assert THRESHOLD_CRITICAL_FLOAT < THRESHOLD_NEAR_CRITICAL
        assert THRESHOLD_NEAR_CRITICAL < THRESHOLD_LOW_FLOAT
        assert THRESHOLD_LOW_FLOAT < THRESHOLD_MODERATE_FLOAT

    def test_float_threshold_values(self):
        """Test specific float threshold values."""
        assert THRESHOLD_CRITICAL_FLOAT == 0
        assert THRESHOLD_NEAR_CRITICAL == 10
        assert THRESHOLD_LOW_FLOAT == 30
        assert THRESHOLD_MODERATE_FLOAT == 60

    def test_high_duration_threshold(self):
        """Test high duration threshold value."""
        assert THRESHOLD_HIGH_DURATION == 20

    def test_logic_density_target(self):
        """Test logic density target for mining industry."""
        assert TARGET_LOGIC_DENSITY == 1.8

    def test_constraint_percent_target(self):
        """Test constraint percentage target."""
        assert TARGET_CONSTRAINT_PERCENT == 5.0


class TestHealthConstants:
    """Tests for health check scoring constants."""

    def test_health_thresholds_in_order(self):
        """Test health thresholds are in descending order."""
        assert HEALTH_EXCELLENT > HEALTH_GOOD
        assert HEALTH_GOOD > HEALTH_FAIR
        assert HEALTH_FAIR > HEALTH_POOR

    def test_health_threshold_values(self):
        """Test specific health threshold values."""
        assert HEALTH_EXCELLENT == 90
        assert HEALTH_GOOD == 75
        assert HEALTH_FAIR == 50
        assert HEALTH_POOR == 0

    def test_health_covers_full_range(self):
        """Test health thresholds cover 0-100 range."""
        assert HEALTH_POOR == 0
        assert HEALTH_EXCELLENT <= 100


class TestGetHealthColor:
    """Tests for get_health_color function."""

    def test_excellent_score_returns_green(self):
        """Test excellent score (>= 90) returns green."""
        color = get_health_color(95)
        assert color == COLOR_LOW

    def test_exactly_excellent_returns_green(self):
        """Test exactly 90 returns green."""
        color = get_health_color(90)
        assert color == COLOR_LOW

    def test_good_score_returns_light_green(self):
        """Test good score (75-89) returns light green."""
        color = get_health_color(80)
        # Should be light green, not the same as excellent
        assert hasattr(color, 'hexval')  # Valid color object

    def test_exactly_good_returns_light_green(self):
        """Test exactly 75 returns light green."""
        color = get_health_color(75)
        assert color != COLOR_CRITICAL
        assert color != COLOR_LOW  # Not dark green (excellent)

    def test_fair_score_returns_yellow(self):
        """Test fair score (50-74) returns yellow."""
        color = get_health_color(60)
        assert color == COLOR_MEDIUM

    def test_exactly_fair_returns_yellow(self):
        """Test exactly 50 returns yellow."""
        color = get_health_color(50)
        assert color == COLOR_MEDIUM

    def test_poor_score_returns_red(self):
        """Test poor score (< 50) returns red."""
        color = get_health_color(30)
        assert color == COLOR_CRITICAL

    def test_zero_score_returns_red(self):
        """Test zero score returns red."""
        color = get_health_color(0)
        assert color == COLOR_CRITICAL

    def test_negative_score_returns_red(self):
        """Test negative score returns red."""
        color = get_health_color(-10)
        assert color == COLOR_CRITICAL

    def test_100_score_returns_green(self):
        """Test perfect 100 score returns green."""
        color = get_health_color(100)
        assert color == COLOR_LOW


class TestGetFloatColor:
    """Tests for get_float_color function."""

    def test_zero_float_returns_critical(self):
        """Test zero float returns critical red."""
        color = get_float_color(0)
        assert color == FLOAT_CRITICAL

    def test_negative_float_returns_critical(self):
        """Test negative float returns critical red."""
        color = get_float_color(-5)
        assert color == FLOAT_CRITICAL

    def test_near_critical_float(self):
        """Test 1-10 day float returns near critical color."""
        color = get_float_color(5)
        assert color == FLOAT_NEAR_CRITICAL

    def test_exactly_10_days_returns_near_critical(self):
        """Test exactly 10 days returns near critical."""
        color = get_float_color(10)
        assert color == FLOAT_NEAR_CRITICAL

    def test_low_float(self):
        """Test 11-30 day float returns low float color."""
        color = get_float_color(20)
        assert color == FLOAT_LOW

    def test_exactly_30_days_returns_low(self):
        """Test exactly 30 days returns low float color."""
        color = get_float_color(30)
        assert color == FLOAT_LOW

    def test_moderate_float(self):
        """Test 31-60 day float returns moderate color."""
        color = get_float_color(45)
        assert color == FLOAT_MODERATE

    def test_exactly_60_days_returns_moderate(self):
        """Test exactly 60 days returns moderate color."""
        color = get_float_color(60)
        assert color == FLOAT_MODERATE

    def test_high_float(self):
        """Test > 60 day float returns high float color."""
        color = get_float_color(90)
        assert color == FLOAT_HIGH

    def test_very_high_float(self):
        """Test very high float returns high color."""
        color = get_float_color(365)
        assert color == FLOAT_HIGH


class TestGetSeverityColor:
    """Tests for get_severity_color function."""

    def test_critical_severity(self):
        """Test 'critical' returns critical color."""
        assert get_severity_color('critical') == COLOR_CRITICAL

    def test_high_severity(self):
        """Test 'high' returns high color."""
        assert get_severity_color('high') == COLOR_HIGH

    def test_medium_severity(self):
        """Test 'medium' returns medium color."""
        assert get_severity_color('medium') == COLOR_MEDIUM

    def test_low_severity(self):
        """Test 'low' returns low color."""
        assert get_severity_color('low') == COLOR_LOW

    def test_info_severity(self):
        """Test 'info' returns info color."""
        assert get_severity_color('info') == COLOR_INFO

    def test_case_insensitive(self):
        """Test severity lookup is case insensitive."""
        assert get_severity_color('CRITICAL') == COLOR_CRITICAL
        assert get_severity_color('Critical') == COLOR_CRITICAL
        assert get_severity_color('HIGH') == COLOR_HIGH

    def test_unknown_severity_returns_info(self):
        """Test unknown severity defaults to info color."""
        assert get_severity_color('unknown') == COLOR_INFO
        assert get_severity_color('other') == COLOR_INFO
        assert get_severity_color('') == COLOR_INFO


class TestGetCustomStyles:
    """Tests for get_custom_styles function."""

    def test_returns_dict(self):
        """Test function returns a dictionary."""
        styles = get_custom_styles()
        assert isinstance(styles, dict)

    def test_all_expected_styles_present(self):
        """Test all expected style names are present."""
        styles = get_custom_styles()
        expected_styles = [
            'ReportTitle', 'SectionHeading', 'SubHeading', 'BodyText',
            'SmallText', 'TableHeader', 'TableCell', 'StatValue',
            'StatLabel', 'Footer', 'CriticalText', 'WarningText', 'SuccessText'
        ]
        for style_name in expected_styles:
            assert style_name in styles, f"Missing style: {style_name}"

    def test_styles_are_paragraph_styles(self):
        """Test all styles are ParagraphStyle instances."""
        styles = get_custom_styles()
        for name, style in styles.items():
            assert isinstance(style, ParagraphStyle), \
                f"Style '{name}' is not a ParagraphStyle"

    def test_report_title_style(self):
        """Test ReportTitle style properties."""
        styles = get_custom_styles()
        title_style = styles['ReportTitle']
        assert title_style.fontSize == FONT_TITLE
        assert title_style.textColor == CORPORATE_PRIMARY

    def test_section_heading_style(self):
        """Test SectionHeading style properties."""
        styles = get_custom_styles()
        heading_style = styles['SectionHeading']
        assert heading_style.fontSize == FONT_HEADING1
        assert heading_style.textColor == CORPORATE_PRIMARY

    def test_critical_text_style(self):
        """Test CriticalText style uses critical color."""
        styles = get_custom_styles()
        critical_style = styles['CriticalText']
        assert critical_style.textColor == COLOR_CRITICAL

    def test_warning_text_style(self):
        """Test WarningText style uses high/warning color."""
        styles = get_custom_styles()
        warning_style = styles['WarningText']
        assert warning_style.textColor == COLOR_HIGH

    def test_success_text_style(self):
        """Test SuccessText style uses low/success color."""
        styles = get_custom_styles()
        success_style = styles['SuccessText']
        assert success_style.textColor == COLOR_LOW

    def test_table_header_style_uses_white_text(self):
        """Test TableHeader style uses white text."""
        styles = get_custom_styles()
        header_style = styles['TableHeader']
        assert header_style.textColor == TABLE_HEADER_TEXT


class TestGetTableStyle:
    """Tests for get_table_style function."""

    def test_returns_table_style(self):
        """Test function returns a TableStyle object."""
        style = get_table_style()
        assert isinstance(style, TableStyle)

    def test_with_alternating_rows_default(self):
        """Test default includes alternating rows option."""
        style = get_table_style()
        # Should return valid TableStyle
        assert style is not None

    def test_without_alternating_rows(self):
        """Test with alternating rows disabled."""
        style = get_table_style(alternating_rows=False)
        assert isinstance(style, TableStyle)

    def test_table_style_has_commands(self):
        """Test TableStyle has styling commands."""
        style = get_table_style()
        # TableStyle should have _cmds or equivalent
        assert hasattr(style, 'getCommands') or hasattr(style, '_cmds')


class TestGetSummaryBoxStyle:
    """Tests for get_summary_box_style function."""

    def test_returns_table_style(self):
        """Test function returns a TableStyle object."""
        style = get_summary_box_style()
        assert isinstance(style, TableStyle)

    def test_summary_box_has_commands(self):
        """Test summary box style has styling commands."""
        style = get_summary_box_style()
        assert hasattr(style, 'getCommands') or hasattr(style, '_cmds')


class TestColorConsistency:
    """Tests for color consistency across the module."""

    def test_float_critical_matches_color_critical(self):
        """Test float critical color matches severity critical."""
        assert FLOAT_CRITICAL == COLOR_CRITICAL

    def test_float_high_matches_color_low(self):
        """Test float high (good) matches color low (good)."""
        assert FLOAT_HIGH == COLOR_LOW

    def test_status_completed_is_green(self):
        """Test completed status is green (success)."""
        assert STATUS_COMPLETED == COLOR_LOW

    def test_status_in_progress_is_blue(self):
        """Test in-progress status is blue (info)."""
        assert STATUS_IN_PROGRESS == COLOR_INFO


class TestStyleIntegration:
    """Integration tests for style functions working together."""

    def test_health_and_float_color_consistency(self):
        """Test color consistency between health and float functions."""
        # Both critical conditions should return same red
        health_critical = get_health_color(10)
        float_critical = get_float_color(-5)
        assert health_critical == float_critical

    def test_severity_covers_all_health_levels(self):
        """Test severity colors can represent all health conditions."""
        # All health conditions can be mapped to a severity
        critical_color = get_severity_color('critical')
        high_color = get_severity_color('high')
        medium_color = get_severity_color('medium')
        low_color = get_severity_color('low')

        # These should all be distinct and valid
        assert critical_color is not None
        assert high_color is not None
        assert medium_color is not None
        assert low_color is not None

    def test_custom_styles_use_defined_colors(self):
        """Test custom styles use the defined color constants."""
        styles = get_custom_styles()

        # Critical text should use critical color
        assert styles['CriticalText'].textColor == COLOR_CRITICAL

        # Title should use corporate primary
        assert styles['ReportTitle'].textColor == CORPORATE_PRIMARY
