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
QMainWindow, QDialog {{
    background-color: {BG};
}}
#Sidebar {{
    background-color: {SURFACE};
    border-right: 1px solid {BORDER};
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
    border: 1px solid {BORDER};
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
    border: 1px solid {BORDER};
    border-radius: 8px;
    gridline-color: {BORDER};
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
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit {{
    background-color: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 8px;
}}
QPushButton {{
    background-color: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 7px 14px;
}}
QPushButton:hover {{
    border-color: {PRIMARY_BRIGHT};
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
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
QTabBar::tab {{
    background: {SURFACE};
    padding: 8px 16px;
    border: 1px solid {BORDER};
    border-bottom: none;
}}
QTabBar::tab:selected {{
    background: {PRIMARY};
    color: #003732;
}}
"""
