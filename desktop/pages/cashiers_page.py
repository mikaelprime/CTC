from PySide6.QtWidgets import QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget


class CashiersPage(QWidget):
    """No backend model exists yet for cashiers/cash registers — local demo data only."""

    _DEMO = [
        {"nombre": "Rosa Elena Quispe", "turno": "Mañana", "caja": "Caja 1", "estado": "Abierta", "recaudado_hoy": 3420.0},
        {"nombre": "Manuel Ortega Díaz", "turno": "Tarde", "caja": "Caja 2", "estado": "Cerrada", "recaudado_hoy": 2110.0},
        {"nombre": "Sofía Herrera Luna", "turno": "Mañana", "caja": "Caja 3", "estado": "Abierta", "recaudado_hoy": 1875.0},
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        header = QLabel("Gestión y Registro de Cajeros")
        header.setObjectName("PageTitle")
        sub = QLabel("Control de turnos y arqueo de caja")
        sub.setObjectName("PageSubtitle")
        notice = QLabel(
            "⚠ El backend aún no expone un módulo de cajeros/cajas. "
            "Esta vista muestra datos de referencia hasta que se agregue esa API."
        )
        notice.setWordWrap(True)
        notice.setStyleSheet("color: #f59e0b;")

        layout.addWidget(header)
        layout.addWidget(sub)
        layout.addWidget(notice)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Nombre", "Turno", "Caja", "Recaudado Hoy", "Estado"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setRowCount(len(self._DEMO))
        for r, row in enumerate(self._DEMO):
            table.setItem(r, 0, QTableWidgetItem(row["nombre"]))
            table.setItem(r, 1, QTableWidgetItem(row["turno"]))
            table.setItem(r, 2, QTableWidgetItem(row["caja"]))
            table.setItem(r, 3, QTableWidgetItem(f"${row['recaudado_hoy']:,.2f}"))
            table.setItem(r, 4, QTableWidgetItem(row["estado"]))
        layout.addWidget(table)
