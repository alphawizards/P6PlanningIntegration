#!/usr/bin/env python3
"""
PDF Styling Constants for P6 Report Generator.

Provides consistent styling for professional schedule reports:
- Color schemes (corporate and severity-based)
- Page layouts and margins
- Table styles
- Font configurations
"""

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


# =============================================================================
# Color Schemes
# =============================================================================

# Corporate Colors (customizable per organization)
CORPORATE_PRIMARY = colors.HexColor('#003366')    # Dark Blue
CORPORATE_SECONDARY = colors.HexColor('#0066CC')  # Medium Blue
CORPORATE_ACCENT = colors.HexColor('#FF6600')     # Orange

# Severity Colors (Mining Industry Standard)
COLOR_CRITICAL = colors.HexColor('#D32F2F')       # Red - Critical issues
COLOR_HIGH = colors.HexColor('#F57C00')           # Orange - High priority
COLOR_MEDIUM = colors.HexColor('#FBC02D')         # Yellow - Medium priority
COLOR_LOW = colors.HexColor('#388E3C')            # Green - Low priority / OK
COLOR_INFO = colors.HexColor('#1976D2')           # Blue - Informational

# Float Status Colors
FLOAT_CRITICAL = COLOR_CRITICAL                    # Float <= 0
FLOAT_NEAR_CRITICAL = COLOR_HIGH                   # Float 1-10 days
FLOAT_LOW = colors.HexColor('#FFB300')             # Float 11-30 days
FLOAT_MODERATE = colors.HexColor('#7CB342')        # Float 31-60 days
FLOAT_HIGH = COLOR_LOW                             # Float > 60 days

# Table Colors
TABLE_HEADER_BG = CORPORATE_PRIMARY
TABLE_HEADER_TEXT = colors.white
TABLE_ROW_ALT = colors.HexColor('#F5F5F5')         # Light gray alternating
TABLE_BORDER = colors.HexColor('#CCCCCC')          # Light gray border

# Status Colors
STATUS_COMPLETED = COLOR_LOW                       # Green
STATUS_IN_PROGRESS = COLOR_INFO                    # Blue
STATUS_NOT_STARTED = colors.HexColor('#9E9E9E')    # Gray


# =============================================================================
# Page Layout
# =============================================================================

# Margins
MARGIN_TOP = 0.75 * inch
MARGIN_BOTTOM = 0.75 * inch
MARGIN_LEFT = 0.75 * inch
MARGIN_RIGHT = 0.75 * inch

# Header/Footer
PAGE_HEADER_HEIGHT = 0.6 * inch
PAGE_FOOTER_HEIGHT = 0.4 * inch

# Content widths (for letter size page)
CONTENT_WIDTH_LETTER = 8.5 * inch - MARGIN_LEFT - MARGIN_RIGHT
CONTENT_WIDTH_A4 = 8.27 * inch - MARGIN_LEFT - MARGIN_RIGHT


# =============================================================================
# Font Sizes
# =============================================================================

FONT_TITLE = 18
FONT_HEADING1 = 14
FONT_HEADING2 = 12
FONT_BODY = 10
FONT_SMALL = 8
FONT_FOOTER = 8


# =============================================================================
# Mining Industry Thresholds
# =============================================================================

# Float thresholds (in days)
THRESHOLD_CRITICAL_FLOAT = 0
THRESHOLD_NEAR_CRITICAL = 10
THRESHOLD_LOW_FLOAT = 30
THRESHOLD_MODERATE_FLOAT = 60

# Duration thresholds
THRESHOLD_HIGH_DURATION = 20  # Days - flag activities longer than this

# Logic density target
TARGET_LOGIC_DENSITY = 1.8  # Relationships per activity

# Constraint limit
TARGET_CONSTRAINT_PERCENT = 5.0  # Max percentage of constrained activities


# =============================================================================
# Health Check Scoring
# =============================================================================

HEALTH_EXCELLENT = 90
HEALTH_GOOD = 75
HEALTH_FAIR = 50
HEALTH_POOR = 0


def get_health_color(score: float) -> colors.Color:
    """Get color based on health score."""
    if score >= HEALTH_EXCELLENT:
        return COLOR_LOW  # Green
    elif score >= HEALTH_GOOD:
        return colors.HexColor('#7CB342')  # Light green
    elif score >= HEALTH_FAIR:
        return COLOR_MEDIUM  # Yellow
    else:
        return COLOR_CRITICAL  # Red


def get_float_color(float_days: float) -> colors.Color:
    """Get color based on total float value."""
    if float_days <= THRESHOLD_CRITICAL_FLOAT:
        return FLOAT_CRITICAL
    elif float_days <= THRESHOLD_NEAR_CRITICAL:
        return FLOAT_NEAR_CRITICAL
    elif float_days <= THRESHOLD_LOW_FLOAT:
        return FLOAT_LOW
    elif float_days <= THRESHOLD_MODERATE_FLOAT:
        return FLOAT_MODERATE
    else:
        return FLOAT_HIGH


def get_severity_color(severity: str) -> colors.Color:
    """Get color based on severity level."""
    severity_map = {
        'critical': COLOR_CRITICAL,
        'high': COLOR_HIGH,
        'medium': COLOR_MEDIUM,
        'low': COLOR_LOW,
        'info': COLOR_INFO,
    }
    return severity_map.get(severity.lower(), COLOR_INFO)


# =============================================================================
# Custom Paragraph Styles
# =============================================================================

def get_custom_styles():
    """
    Get customized paragraph styles for P6 reports.

    Returns:
        dict: Dictionary of ParagraphStyle objects
    """
    styles = getSampleStyleSheet()

    custom_styles = {
        'ReportTitle': ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=FONT_TITLE,
            textColor=CORPORATE_PRIMARY,
            spaceAfter=12,
            alignment=TA_CENTER,
        ),
        'SectionHeading': ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontSize=FONT_HEADING1,
            textColor=CORPORATE_PRIMARY,
            spaceBefore=12,
            spaceAfter=6,
            borderWidth=1,
            borderColor=CORPORATE_PRIMARY,
            borderPadding=4,
        ),
        'SubHeading': ParagraphStyle(
            'SubHeading',
            parent=styles['Heading3'],
            fontSize=FONT_HEADING2,
            textColor=CORPORATE_SECONDARY,
            spaceBefore=8,
            spaceAfter=4,
        ),
        'BodyText': ParagraphStyle(
            'BodyText',
            parent=styles['Normal'],
            fontSize=FONT_BODY,
            leading=14,
            spaceAfter=6,
        ),
        'SmallText': ParagraphStyle(
            'SmallText',
            parent=styles['Normal'],
            fontSize=FONT_SMALL,
            leading=10,
            textColor=colors.HexColor('#666666'),
        ),
        'TableHeader': ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontSize=FONT_SMALL,
            textColor=TABLE_HEADER_TEXT,
            alignment=TA_CENTER,
        ),
        'TableCell': ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontSize=FONT_SMALL,
            leading=10,
        ),
        'StatValue': ParagraphStyle(
            'StatValue',
            parent=styles['Normal'],
            fontSize=FONT_HEADING1,
            textColor=CORPORATE_PRIMARY,
            alignment=TA_CENTER,
        ),
        'StatLabel': ParagraphStyle(
            'StatLabel',
            parent=styles['Normal'],
            fontSize=FONT_SMALL,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER,
        ),
        'Footer': ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=FONT_FOOTER,
            textColor=colors.HexColor('#999999'),
            alignment=TA_CENTER,
        ),
        'CriticalText': ParagraphStyle(
            'CriticalText',
            parent=styles['Normal'],
            fontSize=FONT_BODY,
            textColor=COLOR_CRITICAL,
        ),
        'WarningText': ParagraphStyle(
            'WarningText',
            parent=styles['Normal'],
            fontSize=FONT_BODY,
            textColor=COLOR_HIGH,
        ),
        'SuccessText': ParagraphStyle(
            'SuccessText',
            parent=styles['Normal'],
            fontSize=FONT_BODY,
            textColor=COLOR_LOW,
        ),
    }

    return custom_styles


# =============================================================================
# Table Style Helpers
# =============================================================================

def get_table_style(alternating_rows: bool = True):
    """
    Get standard table style for P6 reports.

    Args:
        alternating_rows: Whether to use alternating row colors

    Returns:
        list: TableStyle commands
    """
    from reportlab.platypus import TableStyle

    style_commands = [
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), TABLE_HEADER_TEXT),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), FONT_SMALL),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, TABLE_BORDER),
        ('BOX', (0, 0), (-1, -1), 1, CORPORATE_PRIMARY),

        # Body
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), FONT_SMALL),

        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]

    return TableStyle(style_commands)


def get_summary_box_style():
    """Get style for summary/statistics boxes."""
    from reportlab.platypus import TableStyle

    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F9FA')),
        ('BOX', (0, 0), (-1, -1), 1, CORPORATE_PRIMARY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ])
