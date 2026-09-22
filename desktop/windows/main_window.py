from PySide6.QtGui import QKeySequence, QShortcut
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
from widgets.animated_button import AnimatedButton
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

        # Las páginas hacen llamadas a la API apenas se crean. Si se instancian
        # todas de una vez al iniciar sesión, cada una bloquea la ventana
        # principal por turnos (peor aún si el backend gratuito de Render
        # estaba dormido). Se crean de forma perezosa, solo al navegar a ellas.
        self._page_classes = [page_cls for _, page_cls in visible_items]
        self._page_widgets: dict[int, QWidget] = {}
        for index in range(len(self._page_classes)):
            self.stack.addWidget(QWidget())

        for index, (label, _page_cls) in enumerate(visible_items):
            btn = AnimatedButton(label)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _checked=False, i=index: self.switch_page(i))
            self.nav_group.addButton(btn, index)
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        # En columna, no en fila: dos botones de texto largo no caben uno junto
        # al otro en un sidebar de 220px sin cortarse.
        display_col = QVBoxLayout()
        display_col.setSpacing(6)
        theme_btn = QPushButton("Modo claro")
        theme_btn.clicked.connect(lambda: self.toggle_theme(theme_btn))
        self.fullscreen_btn = QPushButton("Pantalla completa")
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        display_col.addWidget(theme_btn)
        display_col.addWidget(self.fullscreen_btn)
        sidebar_layout.addLayout(display_col)

        # F11 además del botón: es el atajo estándar en Windows para esto.
        QShortcut(QKeySequence("F11"), self, activated=self.toggle_fullscreen)

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
        self.switch_page(0)

    def show_on_current_screen(self) -> None:
        show_maximized_on_current_screen(self)

    def switch_page(self, index: int) -> None:
        just_created = False
        if index not in self._page_widgets:
            widget = self._page_classes[index]()
            self._page_widgets[index] = widget
            self.stack.removeWidget(self.stack.widget(index))
            self.stack.insertWidget(index, widget)
            just_created = True
        self.stack.setCurrentIndex(index)
        widget = self._page_widgets[index]
        # El constructor de cada página ya hace su propia carga inicial;
        # solo se recarga aquí en visitas posteriores.
        if not just_created and hasattr(widget, "reload"):
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

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showMaximized()
            self.fullscreen_btn.setText("Pantalla completa")
        else:
            self.showFullScreen()
            self.fullscreen_btn.setText("Salir pantalla completa")
