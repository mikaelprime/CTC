"""Shared visual theme for the CTC Campus desktop app (dark, teal branding)."""

PRIMARY = "#0d9488"
PRIMARY_BRIGHT = "#6bd8cb"
SECONDARY_BRIGHT = "#b6c4ff"
TERTIARY = "#38bdf8"
SUCCESS = "#10b981"
WARNING = "#f59e0b"
ERROR = "#ef4444"
BG = "#0b1326"
SURFACE = "#171f33"
SURFACE_ALT = "#1d2740"
BORDER = "#2a3552"
TEXT = "#dae2fd"
TEXT_MUTED = "#94a3b8"

CHART_SEQUENCE = [PRIMARY_BRIGHT, SECONDARY_BRIGHT, TERTIARY, "#7bd0ff", WARNING]

STATUS_COLORS = {
    "success": SUCCESS,
    "warning": WARNING,
    "error": ERROR,
    "info": TERTIARY,
}

STYLESHEET = f"""
* {{
    font-family: 'Segoe UI', sans-serif;
    color: {TEXT};
}}
QWidget {{
    background-color: {BG};
}}
QLabel {{
    background-color: transparent;
    border: none;
}}
QFormLayout QLabel {{
    background-color: transparent;
    border: none;
}}
QMainWindow, QDialog {{
    background-color: {BG};
}}
#LoginShell {{
    background-color: #08111f;
}}
#LoginCard {{
    background-color: #111f32;
    border: 1px solid #29415a;
    border-radius: 18px;
}}
#LoginEyebrow {{
    color: {PRIMARY_BRIGHT};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
}}
#LoginTitle {{
    color: #f4fbff;
    font-size: 34px;
    font-weight: 700;
}}
#LoginSubtitle {{
    color: {TEXT_MUTED};
    font-size: 13px;
}}
#LoginInput {{
    min-height: 34px;
    background-color: #0b1727;
    border: 1px solid #2c4862;
    border-radius: 8px;
    padding: 6px 10px;
}}
#LoginInput:focus {{
    border: 1px solid {PRIMARY_BRIGHT};
}}
#LoginButton {{
    min-height: 42px;
    border-radius: 9px;
    font-size: 14px;
}}
#LoginFooter {{
    color: #6f8aa1;
    font-size: 11px;
}}
#LoginExitButton {{
    background: transparent;
    border: none;
    color: {TEXT_MUTED};
    padding: 4px;
}}
#LoginExitButton:hover {{
    color: {ERROR};
}}
#Sidebar {{
    background-color: {SURFACE};
    border: none;
}}
#SidebarBrand {{
    font-size: 15px;
    font-weight: 600;
}}
#SidebarBrandSub {{
    color: {PRIMARY_BRIGHT};
    font-size: 10px;
    letter-spacing: 1px;
}}
QPushButton#NavButton {{
    text-align: left;
    padding: 10px 14px;
    border: none;
    border-radius: 8px;
    background: transparent;
    font-size: 13px;
}}
QPushButton#NavButton:hover {{
    background-color: {SURFACE_ALT};
}}
QPushButton#NavButton:checked {{
    background-color: {PRIMARY};
    color: #003732;
    font-weight: 600;
}}
#PageTitle {{
    font-size: 20px;
    font-weight: 600;
}}
#PageSubtitle {{
    color: {TEXT_MUTED};
    font-size: 12px;
    margin-bottom: 6px;
}}
#KpiCard {{
    background-color: {SURFACE};
    border: none;
    border-radius: 12px;
}}
#KpiLabel {{
    color: {TEXT_MUTED};
    font-size: 10px;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
#KpiValue {{
    font-size: 22px;
    font-weight: 700;
}}
#KpiSub {{
    color: {TEXT_MUTED};
    font-size: 11px;
}}
QTableWidget {{
    background-color: {SURFACE};
    border: none;
    gridline-color: transparent;
}}
QHeaderView::section {{
    background-color: {SURFACE_ALT};
    color: {TEXT_MUTED};
    padding: 6px;
    border: none;
    font-size: 11px;
    text-transform: uppercase;
}}
QTableWidget::item {{
    padding: 4px;
}}
QTableWidget::item:alternate {{
    background-color: {SURFACE_ALT};
}}
QTableWidget::item:selected {{
    background-color: {PRIMARY};
    color: #ffffff;
}}
QLabel#SummaryCaption {{
    color: {TEXT_MUTED};
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}
QLabel#SummaryValue {{
    color: {TEXT};
    font-size: 18px;
    font-weight: 700;
    padding-bottom: 8px;
}}
QGroupBox {{
    border: none;
    margin-top: 8px;
    padding-top: 12px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 0px;
    padding: 0 4px;
    color: {TEXT_MUTED};
}}
#RegisterPanel {{
    background-color: {SURFACE};
    border-radius: 12px;
    padding: 10px;
}}
#RegisterStatus {{
    color: {PRIMARY_BRIGHT};
    font-size: 13px;
    font-weight: 600;
}}
#PaymentHint {{
    background-color: transparent;
    color: {TEXT_MUTED};
    padding: 6px 0;
}}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit {{
    background-color: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 8px;
}}
QPushButton {{
    background-color: {SURFACE_ALT};
    border: none;
    border-radius: 6px;
    padding: 7px 14px;
}}
QPushButton:hover {{
    background-color: {PRIMARY};
}}
QPushButton[class="primary"] {{
    background-color: {PRIMARY};
    color: #003732;
    font-weight: 600;
    border: none;
}}
QPushButton[class="primary"]:hover {{
    background-color: {PRIMARY_BRIGHT};
}}
QLabel#Badge {{
    border-radius: 9px;
    padding: 2px 8px;
    font-size: 11px;
}}
QTabWidget::pane {{
    border: none;
}}
QTabBar::tab {{
    background: {SURFACE};
    padding: 8px 16px;
    border: none;
    border-bottom: none;
}}
QTabBar::tab:selected {{
    background: {PRIMARY};
    color: #003732;
}}
"""


def stylesheet_for(mode: str) -> str:
    if mode != "light":
        return STYLESHEET

    replacements = {
        "#0b1326": "#f4f7f8",
        "#171f33": "#ffffff",
        "#1d2740": "#e8eef0",
        "#2a3552": "#d6e0e3",
        "#dae2fd": "#17252b",
        "#94a3b8": "#60747c",
        "#08111f": "#eaf1f2",
        "#111f32": "#ffffff",
        "#29415a": "#d3e0e3",
        "#f4fbff": "#10252b",
        "#0b1727": "#f7fafb",
        "#2c4862": "#c2d2d6",
        "#6f8aa1": "#71878e",
        "#003732": "#ffffff",
    }
    light_stylesheet = STYLESHEET
    for dark_color, light_color in replacements.items():
        light_stylesheet = light_stylesheet.replace(dark_color, light_color)
    return light_stylesheet
