"""Shared visual theme for the CTC Campus desktop app (dark, teal branding).

No es CSS ni Tailwind: PySide6 usa QSS (Qt Style Sheets), un lenguaje propio
de Qt con una sintaxis parecida a CSS pero con su propio set de selectores
y propiedades. Esto centraliza esa hoja de estilos para toda la app nativa.
"""

PRIMARY = "#14b8a6"
PRIMARY_DARK = "#0d9488"
PRIMARY_BRIGHT = "#5eead4"
SECONDARY_BRIGHT = "#b6c4ff"
TERTIARY = "#38bdf8"
SUCCESS = "#10b981"
WARNING = "#f59e0b"
ERROR = "#f87171"
BG = "#0a0f1e"
SURFACE = "#141c30"
SURFACE_ALT = "#1b2540"
SURFACE_HOVER = "#212c4a"
BORDER = "#293150"
BORDER_SOFT = "#232b46"
TEXT = "#e6ebff"
TEXT_MUTED = "#8b96b8"

FONT_STACK = "'Segoe UI', sans-serif"

CHART_SEQUENCE = [PRIMARY_BRIGHT, SECONDARY_BRIGHT, TERTIARY, "#7bd0ff", WARNING]

STATUS_COLORS = {
    "success": SUCCESS,
    "warning": WARNING,
    "error": ERROR,
    "info": TERTIARY,
}

STYLESHEET = f"""
* {{
    font-family: {FONT_STACK};
    color: {TEXT};
    outline: none;
}}
QWidget {{
    background-color: {BG};
    font-size: 13px;
}}
QLabel {{
    background-color: transparent;
    border: none;
}}
QFormLayout QLabel {{
    background-color: transparent;
    border: none;
}}
QToolTip {{
    background-color: {SURFACE_ALT};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
}}
QMainWindow, QDialog {{
    background-color: {BG};
}}
QDialog {{
    border-radius: 12px;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    min-height: 30px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background: {PRIMARY};
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    min-width: 30px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {PRIMARY};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0px;
    width: 0px;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: none;
}}

/* ---------- Login ---------- */
#LoginShell {{
    background-color: {BG};
}}
#LoginCard {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_SOFT};
    border-radius: 20px;
}}
#LoginEyebrow {{
    color: {PRIMARY_BRIGHT};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 3px;
}}
#LoginTitle {{
    color: #f7fbff;
    font-size: 36px;
    font-weight: 700;
    letter-spacing: -0.5px;
}}
#LoginSubtitle {{
    color: {TEXT_MUTED};
    font-size: 13px;
}}
#LoginInput {{
    min-height: 22px;
    background-color: {BG};
    border: 1.5px solid {BORDER};
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: {PRIMARY};
}}
#LoginInput:hover {{
    border: 1.5px solid #3a4468;
}}
#LoginInput:focus {{
    border: 1.5px solid {PRIMARY};
}}
#LoginButton {{
    min-height: 44px;
    border-radius: 11px;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.2px;
}}
#LoginButton:disabled {{
    background-color: {SURFACE_ALT};
    color: {TEXT_MUTED};
}}
#LoginFooter {{
    color: #5c6a8c;
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

/* ---------- Splash / carga ---------- */
#SplashShell {{
    background-color: {BG};
}}
#SplashTitle {{
    color: #f7fbff;
    font-size: 26px;
    font-weight: 700;
}}
#SplashStatus {{
    color: {TEXT_MUTED};
    font-size: 12.5px;
}}
QProgressBar#SplashBar {{
    background-color: {SURFACE_ALT};
    border: none;
    border-radius: 3px;
    max-height: 6px;
    min-height: 6px;
}}
QProgressBar#SplashBar::chunk {{
    background-color: {PRIMARY};
    border-radius: 3px;
}}

/* ---------- Sidebar ---------- */
#Sidebar {{
    background-color: {SURFACE};
    border: none;
    border-right: 1px solid {BORDER_SOFT};
}}
#SidebarBrand {{
    font-size: 16px;
    font-weight: 700;
    letter-spacing: -0.2px;
}}
#SidebarBrandSub {{
    color: {PRIMARY_BRIGHT};
    font-size: 10px;
    letter-spacing: 1.5px;
    font-weight: 600;
}}
QPushButton#NavButton {{
    text-align: left;
    padding: 11px 14px;
    border: none;
    border-radius: 10px;
    background: transparent;
    font-size: 13px;
    color: {TEXT_MUTED};
}}
QPushButton#NavButton:hover {{
    background-color: {SURFACE_ALT};
    color: {TEXT};
}}
QPushButton#NavButton:checked {{
    background-color: {PRIMARY};
    color: #002824;
    font-weight: 600;
}}

/* ---------- Contenido general ---------- */
#PageTitle {{
    font-size: 21px;
    font-weight: 700;
    letter-spacing: -0.2px;
}}
#PageSubtitle {{
    color: {TEXT_MUTED};
    font-size: 12px;
    margin-bottom: 6px;
}}
#KpiCard {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_SOFT};
    border-radius: 14px;
}}
#KpiLabel {{
    color: {TEXT_MUTED};
    font-size: 10px;
    letter-spacing: 1px;
    text-transform: uppercase;
    font-weight: 600;
}}
#KpiValue {{
    font-size: 24px;
    font-weight: 700;
    letter-spacing: -0.3px;
}}
#KpiSub {{
    color: {TEXT_MUTED};
    font-size: 11px;
}}
QTableWidget {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_SOFT};
    border-radius: 12px;
    gridline-color: transparent;
    selection-background-color: transparent;
}}
QHeaderView::section {{
    background-color: {SURFACE_ALT};
    color: {TEXT_MUTED};
    padding: 8px 6px;
    border: none;
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}
QTableWidget::item {{
    padding: 6px 4px;
}}
QTableWidget::item:alternate {{
    background-color: {SURFACE_ALT};
}}
QTableWidget::item:selected {{
    background-color: {PRIMARY_DARK};
    color: #ffffff;
}}
QLabel#SummaryCaption {{
    color: {TEXT_MUTED};
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
}}
QLabel#SummaryValue {{
    color: {TEXT};
    font-size: 19px;
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
    border: 1px solid {BORDER_SOFT};
    border-radius: 14px;
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
    border: 1.5px solid {BORDER};
    border-radius: 8px;
    padding: 6px 9px;
    min-height: 20px;
    selection-background-color: {PRIMARY};
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover, QTimeEdit:hover {{
    border: 1.5px solid #3a4468;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus {{
    border: 1.5px solid {PRIMARY};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    selection-background-color: {PRIMARY_DARK};
    outline: none;
    padding: 4px;
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 16px;
    border: none;
}}
QPushButton {{
    background-color: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 15px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {SURFACE_HOVER};
    border: 1px solid #3a4468;
}}
QPushButton:pressed {{
    background-color: {BORDER};
}}
QPushButton:disabled {{
    color: {TEXT_MUTED};
    background-color: {SURFACE_ALT};
}}
QPushButton[class="primary"] {{
    background-color: {PRIMARY};
    color: #002824;
    font-weight: 600;
    border: 1px solid {PRIMARY};
}}
QPushButton[class="primary"]:hover {{
    background-color: {PRIMARY_BRIGHT};
    border: 1px solid {PRIMARY_BRIGHT};
}}
QPushButton[class="primary"]:pressed {{
    background-color: {PRIMARY_DARK};
}}
QLabel#Badge {{
    border-radius: 9px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}}
QTabWidget::pane {{
    border: none;
}}
QTabBar::tab {{
    background: {SURFACE};
    padding: 8px 16px;
    border: none;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}
QTabBar::tab:selected {{
    background: {PRIMARY};
    color: #002824;
}}
QMessageBox {{
    background-color: {SURFACE};
}}
QMessageBox QLabel {{
    color: {TEXT};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1.5px solid {BORDER};
    background: {SURFACE_ALT};
}}
QCheckBox::indicator:checked {{
    background: {PRIMARY};
    border: 1.5px solid {PRIMARY};
}}
"""


def stylesheet_for(mode: str) -> str:
    if mode != "light":
        return STYLESHEET

    replacements = {
        BG: "#f4f7f8",
        SURFACE: "#ffffff",
        SURFACE_ALT: "#eef2f4",
        SURFACE_HOVER: "#e2e8ec",
        BORDER: "#d7e0e3",
        BORDER_SOFT: "#e2e8ec",
        TEXT: "#16232a",
        TEXT_MUTED: "#5c747c",
        "#3a4468": "#c2ced3",
        "#f7fbff": "#0d1f24",
        "#5c6a8c": "#6a828a",
        "#002824": "#ffffff",
    }
    light_stylesheet = STYLESHEET
    for dark_color, light_color in replacements.items():
        light_stylesheet = light_stylesheet.replace(dark_color, light_color)
    return light_stylesheet
