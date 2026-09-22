import numpy as np
from matplotlib.ticker import FuncFormatter
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QFontMetrics
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import data_service
from theme import BORDER, CHART_SEQUENCE, STATUS_COLORS, SURFACE, TEXT, TEXT_MUTED
from widgets.animated_button import AnimatedButton
from widgets.async_worker import AsyncWorker
from widgets.chart_canvas import ChartCanvas
from widgets.effects import apply_card_shadow
from widgets.kpi_card import KpiCard


class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer_layout.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setSpacing(16)

        header = QLabel("Panel General CTC")
        header.setObjectName("PageTitle")
        sub = QLabel("Sincronización en tiempo real con el backend")
        sub.setObjectName("PageSubtitle")

        toolbar = QHBoxLayout()
        toolbar.addWidget(header)
        toolbar.addStretch()
        refresh_btn = AnimatedButton("⟳ Actualizar")
        refresh_btn.clicked.connect(self.reload)
        toolbar.addWidget(refresh_btn)

        layout.addLayout(toolbar)
        layout.addWidget(sub)

        # 2x2 grid instead of a single row so the KPIs never fight each other
        # for horizontal space on narrower screens or high-DPI scaling.
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(14)
        self.kpi_estudiantes = KpiCard("Estudiantes Activos", "0")
        self.kpi_inscripciones = KpiCard("Inscripciones del Mes", "0")
        self.kpi_pagos = KpiCard("Pagos Pendientes", "$0")
        self.kpi_vencimientos = KpiCard("Próximos Vencimientos", "0")
        cards = (self.kpi_estudiantes, self.kpi_inscripciones, self.kpi_pagos, self.kpi_vencimientos)
        for card in cards:
            card.setMinimumWidth(160)
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        kpi_grid.addWidget(self.kpi_estudiantes, 0, 0)
        kpi_grid.addWidget(self.kpi_inscripciones, 0, 1)
        kpi_grid.addWidget(self.kpi_pagos, 0, 2)
        kpi_grid.addWidget(self.kpi_vencimientos, 0, 3)
        for col in range(4):
            kpi_grid.setColumnStretch(col, 1)
        layout.addLayout(kpi_grid)

        charts_container = QWidget()
        charts_row = QHBoxLayout(charts_container)
        charts_row.setSpacing(14)

        ingresos_box = QFrame()
        ingresos_box.setObjectName("KpiCard")
        apply_card_shadow(ingresos_box, blur=14, y_offset=6, alpha=60)
        ingresos_layout = QVBoxLayout(ingresos_box)
        ingresos_title = QLabel("Ingresos Semestrales")
        ingresos_title.setStyleSheet("font-weight: 600; border: none;")
        self.ingresos_canvas = ChartCanvas(width=5, height=2.8)
        self.ingresos_canvas.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self.ingresos_canvas.setMinimumWidth(200)
        ingresos_layout.addWidget(ingresos_title)
        ingresos_layout.addWidget(self.ingresos_canvas)
        charts_row.addWidget(ingresos_box, stretch=2)

        dist_box = QFrame()
        dist_box.setObjectName("KpiCard")
        dist_box.setMaximumWidth(320)
        apply_card_shadow(dist_box, blur=14, y_offset=6, alpha=60)
        dist_layout = QVBoxLayout(dist_box)
        dist_title = QLabel("Distribución Académica")
        dist_title.setStyleSheet("font-weight: 600; border: none;")
        self.dist_canvas = ChartCanvas(width=2.6, height=2.6)
        self.dist_canvas.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self.dist_canvas.setMinimumWidth(160)
        self.dist_legend = QVBoxLayout()
        self.dist_legend.setSpacing(4)
        dist_layout.addWidget(dist_title)
        dist_layout.addWidget(self.dist_canvas)
        dist_layout.addLayout(self.dist_legend)
        charts_row.addWidget(dist_box, stretch=1)

        layout.addWidget(charts_container)

        act_label = QLabel("Registro de Actividad Reciente")
        act_label.setObjectName("PageSubtitle")
        layout.addWidget(act_label)

        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(6)
        self.activity_table.setHorizontalHeaderLabels(
            ["Tipo", "Estudiante", "ID", "Programa", "Monto", "Estado"]
        )
        self.activity_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.activity_table.verticalHeader().setVisible(False)
        self.activity_table.horizontalHeader().setStretchLastSection(True)
        self.activity_table.setMinimumHeight(220)
        self.activity_table.setMaximumHeight(280)
        layout.addWidget(self.activity_table)

        self._load_worker = None
        self._ingresos_timer = QTimer(self)
        self._dist_timer = QTimer(self)
        self.reload()

    def reload(self) -> None:
        # Antes esto hacía hasta 7 peticiones HTTP síncronas seguidas en el
        # hilo de la interfaz (con duplicados: /payments/ se pedía 3 veces).
        # Ahora es una sola ronda, en un hilo aparte, para que la ventana no
        # se sienta congelada mientras carga.
        worker = AsyncWorker(data_service.load_dashboard_data, self)
        self._load_worker = worker
        worker.succeeded.connect(lambda data: self._on_data_loaded(worker, data))
        worker.failed.connect(lambda message: self._on_load_failed(worker, message))
        worker.start()

    def _on_load_failed(self, worker: AsyncWorker, message: str) -> None:
        if worker is not self._load_worker:
            return
        QMessageBox.critical(self, "Error", f"No se pudo cargar el panel: {message}")

    def _on_data_loaded(self, worker: AsyncWorker, data: dict) -> None:
        if worker is not self._load_worker:
            return  # una carga más reciente ya está en curso o terminó

        k = data_service.kpis_generales(data)
        ingresos = data_service.ingresos_mensuales(data)
        dist = data_service.distribucion_academica(data)
        actividad = data_service.actividad_reciente(data)

        self.kpi_estudiantes.set_value(f"{k['estudiantes_activos']:,}")
        self.kpi_inscripciones.set_value(str(k["inscripciones_mes"]))
        self.kpi_pagos.set_value(f"${k['pagos_pendientes']:,.2f}")
        self.kpi_pagos.set_sub(f"{k['cuotas_por_auditar']} cuotas por auditar", "warning")
        self.kpi_vencimientos.set_value(str(k["vencimientos"]))
        self.kpi_vencimientos.set_sub(f"{k['matriculas_criticas']} matrículas < 48h", "error")

        self._draw_ingresos(ingresos)
        self._draw_distribucion(dist)
        self._fill_activity(actividad)

    def _style_axes(self, ax) -> None:
        ax.grid(axis="y", color=BORDER, linewidth=0.7, alpha=0.7)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(BORDER)

    def _animate(self, timer: QTimer, duration_ms: int, frames: int, on_frame, on_finished=None) -> None:
        """Anima on_frame(t) de 0 a 1 con easing suave, en pocos pasos y una
        sola vez (no en bucle), para que se sienta fluida sin volverse un
        gasto de CPU continuo.

        `timer` es un QTimer que vive mientras exista la página (creado una
        sola vez en __init__), no uno nuevo por llamada: crear un QTimer,
        programar su deleteLater() al terminar, y luego seguir guardando esa
        misma referencia de Python para la próxima animación es lo que
        causaba "Internal C++ object already deleted" al recargar el panel.
        """
        timer.stop()
        if getattr(timer, "_ctc_connected", False):
            timer.timeout.disconnect()
        timer._ctc_connected = True
        step = {"n": 0}

        def tick():
            step["n"] += 1
            t = min(step["n"] / frames, 1.0)
            eased = 1 - (1 - t) ** 3  # ease-out cubic
            on_frame(eased)
            if t >= 1.0:
                timer.stop()
                if on_finished:
                    on_finished()

        timer.timeout.connect(tick)
        timer.start(max(duration_ms // frames, 1))

    def _draw_ingresos(self, ingresos: dict) -> None:
        meses = ingresos["meses"]
        proyectado_final = ingresos["proyectado"]
        cobrado_final = ingresos["cobrado"]
        max_value = max(proyectado_final + cobrado_final + [0]) or 1

        def render_frame(t: float) -> None:
            ax = self.ingresos_canvas.new_axes()
            x = np.arange(len(meses))
            width = 0.32
            ax.bar(
                x - width / 2, [v * t for v in proyectado_final], width,
                label="Proyectado", color=CHART_SEQUENCE[1], alpha=0.55,
            )
            ax.bar(
                x + width / 2, [v * t for v in cobrado_final], width,
                label="Cobrado", color=CHART_SEQUENCE[0],
            )
            ax.set_xticks(x)
            ax.set_xticklabels(meses)
            ax.set_ylim(0, max_value * 1.15)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _pos: f"${v:,.0f}"))
            self._style_axes(ax)
            ax.legend(
                facecolor=SURFACE,
                labelcolor=TEXT,
                fontsize=8,
                frameon=False,
                loc="upper center",
                bbox_to_anchor=(0.5, 1.18),
                ncol=2,
            )
            self.ingresos_canvas.render(top=0.82)

        self._animate(self._ingresos_timer, 450, 14, render_frame)

    def _draw_distribucion(self, dist: dict) -> None:
        programas = dist["programas"]
        estudiantes = dist["estudiantes"]
        colors = [CHART_SEQUENCE[i % len(CHART_SEQUENCE)] for i in range(len(programas))]

        def render_frame(t: float) -> None:
            ax = self.dist_canvas.new_axes()
            if programas:
                # Crece desde el centro; el texto de porcentaje solo se
                # muestra en el último frame para que no quede amontonado
                # mientras el pastel todavía es pequeño.
                ax.pie(
                    estudiantes,
                    colors=colors,
                    startangle=90,
                    radius=max(t, 0.05),
                    autopct="%1.0f%%" if t >= 1.0 else None,
                    pctdistance=0.78,
                    textprops={"color": TEXT, "fontsize": 8},
                    wedgeprops={"width": 0.42, "edgecolor": SURFACE, "linewidth": 2},
                )
                ax.axis("equal")
                ax.set_xlim(-1.05, 1.05)
                ax.set_ylim(-1.05, 1.05)
            else:
                ax.text(0.5, 0.5, "Sin matrículas todavía", ha="center", va="center", color=TEXT_MUTED, fontsize=9)
                ax.set_xticks([])
                ax.set_yticks([])
            self.dist_canvas.render()

        self._animate(self._dist_timer, 450, 14, render_frame)
        self._fill_dist_legend(dist)

    def _fill_dist_legend(self, dist: dict) -> None:
        while self.dist_legend.count():
            item = self.dist_legend.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, (programa, total) in enumerate(zip(dist["programas"], dist["estudiantes"])):
            color = CHART_SEQUENCE[i % len(CHART_SEQUENCE)]
            row = QLabel()
            row.setStyleSheet(f"color: {color}; border: none; font-size: 11px;")
            metrics = QFontMetrics(row.font())
            # Nombres largos de programas no deben romper el ancho del panel.
            suffix = f" ({total})"
            available = 240 - metrics.horizontalAdvance("●  " + suffix)
            elided = metrics.elidedText(programa, Qt.ElideRight, max(available, 40))
            row.setText(f"●  {elided}{suffix}")
            row.setToolTip(programa)
            self.dist_legend.addWidget(row)

    def _fill_activity(self, actividad: list[dict]) -> None:
        self.activity_table.setRowCount(len(actividad))
        for r, row in enumerate(actividad):
            values = [row["tipo"], row["estudiante"], row["id"], row["programa"], f"${row['monto']:,.2f}"]
            for c, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.activity_table.setItem(r, c, item)
            estado_item = QTableWidgetItem(row["estado"])
            estado_item.setFlags(estado_item.flags() & ~Qt.ItemIsEditable)
            estado_item.setForeground(QColor(STATUS_COLORS.get(row["estado_kind"], "#38bdf8")))
            self.activity_table.setItem(r, 5, estado_item)
