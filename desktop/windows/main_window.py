from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from api_client import api
from window_utils import show_maximized_on_current_screen
from pages.cashiers_page import CashiersPage
from pages.dashboard_page import DashboardPage
from pages.diplomas_page import DiplomasPage
from pages.enrollments_page import EnrollmentsPage
from pages.payments_page import PaymentsPage
from pages.schedules_page import SchedulesPage
from pages.settings_page import SettingsPage
from pages.students_page import StudentsPage

NAV_ITEMS = [
    ("🏫 Dashboard", DashboardPage),
    ("🎓 Estudiantes", StudentsPage),
    ("📝 Inscripciones", EnrollmentsPage),
    ("💳 Pagos", PaymentsPage),
    ("📅 Horarios", SchedulesPage),
    ("🎓 Diplomas", DiplomasPage),
    ("🧾 Cajeros", CashiersPage),
    ("⚙️ Configuración", SettingsPage),
]

ADMIN_ONLY = {"🎓 Diplomas", "🧾 Cajeros", "⚙️ Configuración"}


class MainWindow(QMainWindow):
    def __init__(self, on_logout, on_exit=None, theme_manager=None):
        super().__init__()
        self.on_logout = on_logout
        self.on_exit = on_exit
        self.theme_manager = theme_manager
        self.setWindowTitle("CTC Campus · Admin Console")

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 18, 14, 18)

        brand = QLabel("CTC Campus")
        brand.setObjectName("SidebarBrand")
        brand_sub = QLabel((api.user_role or "USUARIO").upper())
        brand_sub.setObjectName("SidebarBrandSub")
        sidebar_layout.addWidget(brand)
        sidebar_layout.addWidget(brand_sub)
        sidebar_layout.addSpacing(20)

        self.stack = QStackedWidget()
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        visible_items = NAV_ITEMS
        if (api.user_role or "").upper() in {"CAJERO", "CASHIER"}:
            visible_items = [item for item in NAV_ITEMS if item[0] not in ADMIN_ONLY]

        for index, (label, page_cls) in enumerate(visible_items):
            btn = QPushButton(label)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _checked=False, i=index: self.switch_page(i))
            self.nav_group.addButton(btn, index)
            sidebar_layout.addWidget(btn)
            self.stack.addWidget(page_cls())

        sidebar_layout.addStretch()

        display_row = QHBoxLayout()
        theme_btn = QPushButton("Modo claro")
        theme_btn.clicked.connect(lambda: self.toggle_theme(theme_btn))
        fullscreen_btn = QPushButton("Pantalla completa")
        fullscreen_btn.clicked.connect(lambda: self.toggle_fullscreen(fullscreen_btn))
        display_row.addWidget(theme_btn)
        display_row.addWidget(fullscreen_btn)
        sidebar_layout.addLayout(display_row)

        user_label = QLabel(api.user_email or "")
        user_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        sidebar_layout.addWidget(user_label)

        logout_btn = QPushButton("Cerrar sesión")
        logout_btn.clicked.connect(self.handle_logout)
        sidebar_layout.addWidget(logout_btn)

        exit_btn = QPushButton("Salir del programa")
        exit_btn.clicked.connect(self.handle_exit)
        sidebar_layout.addWidget(exit_btn)

        root_layout.addWidget(sidebar)

        content_wrapper = QWidget()
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.addWidget(self.stack)
        root_layout.addWidget(content_wrapper, stretch=1)

        self.nav_group.button(0).setChecked(True)
        self.stack.setCurrentIndex(0)

    def show_on_current_screen(self) -> None:
        show_maximized_on_current_screen(self)

    def switch_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        widget = self.stack.currentWidget()
        if hasattr(widget, "reload"):
            widget.reload()

    def handle_logout(self) -> None:
        self.close()
        api.logout()
        self.on_logout()

    def handle_exit(self) -> None:
        if self.on_exit:
            self.on_exit()
        else:
            self.close()

    def toggle_theme(self, button: QPushButton) -> None:
        if not self.theme_manager:
            return
        mode = self.theme_manager.toggle()
        button.setText("Modo oscuro" if mode == "light" else "Modo claro")

    def toggle_fullscreen(self, button: QPushButton) -> None:
        if self.isFullScreen():
            self.showMaximized()
            button.setText("Pantalla completa")
        else:
            self.showFullScreen()
            button.setText("Salir pantalla completa")
