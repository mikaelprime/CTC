"""Gráfico de tendencia interactivo (pyqtgraph).

A diferencia de `ChartCanvas` (matplotlib, usado para los charts animados del
panel), este widget usa pyqtgraph para ofrecer una interacción real: al mover
el mouse sobre la gráfica aparece una línea guía y una etiqueta con el mes y
el monto exacto bajo el cursor. matplotlib no ofrece esto sin reconstruir la
figura en cada movimiento (demasiado costoso para seguir al mouse en vivo);
pyqtgraph está diseñado para actualizarse a 60fps con datos en tiempo real.
"""

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from theme import BORDER, CHART_SEQUENCE, SURFACE, TEXT, TEXT_MUTED

pg.setConfigOption("background", SURFACE)
pg.setConfigOption("foreground", TEXT_MUTED)
pg.setConfigOptions(antialias=True)


class TrendChart(pg.PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMenuEnabled(False)
        self.setMouseEnabled(x=False, y=False)
        self.hideButtons()
        self.showGrid(x=False, y=True, alpha=0.15)
        self.getAxis("left").setTextPen(TEXT_MUTED)
        self.getAxis("bottom").setTextPen(TEXT_MUTED)
        self.getAxis("left").setPen(BORDER)
        self.getAxis("bottom").setPen(BORDER)
        self.setBackground(SURFACE)

        self._months: list[str] = []
        self._series: dict[str, list[float]] = {}

        self.legend = self.addLegend(offset=(10, 6), labelTextColor=TEXT_MUTED, brush=pg.mkBrush(SURFACE))

        self._cobrado_curve = self.plot(
            [], [], pen=pg.mkPen(CHART_SEQUENCE[0], width=2.4), name="Cobrado",
            symbol="o", symbolSize=6, symbolBrush=CHART_SEQUENCE[0], symbolPen=None,
        )
        self._proyectado_curve = self.plot(
            [], [], pen=pg.mkPen(CHART_SEQUENCE[1], width=1.8, style=Qt.DashLine), name="Proyectado",
        )

        self._crosshair = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(BORDER, width=1))
        self._crosshair.setVisible(False)
        self.addItem(self._crosshair, ignoreBounds=True)

        self._tooltip = pg.TextItem(color=TEXT, anchor=(0.5, 1.2), fill=pg.mkBrush(SURFACE))
        self._tooltip.setFont(QFont("Segoe UI", 9))
        self._tooltip.setVisible(False)
        self.addItem(self._tooltip, ignoreBounds=True)

        self._proxy = pg.SignalProxy(self.scene().sigMouseMoved, rateLimit=60, slot=self._on_mouse_move)

    def set_data(self, months: list[str], cobrado: list[float], proyectado: list[float]) -> None:
        self._months = months
        self._series = {"Cobrado": cobrado, "Proyectado": proyectado}
        x = list(range(len(months)))
        self._cobrado_curve.setData(x, cobrado)
        self._proyectado_curve.setData(x, proyectado)
        axis = self.getAxis("bottom")
        axis.setTicks([list(enumerate(months))])
        self._tooltip.setVisible(False)
        self._crosshair.setVisible(False)

    def _on_mouse_move(self, event) -> None:
        if not self._months:
            return
        pos = event[0]
        if not self.sceneBoundingRect().contains(pos):
            self._tooltip.setVisible(False)
            self._crosshair.setVisible(False)
            return
        point = self.getPlotItem().vb.mapSceneToView(pos)
        index = round(point.x())
        if index < 0 or index >= len(self._months):
            self._tooltip.setVisible(False)
            self._crosshair.setVisible(False)
            return
        cobrado = self._series["Cobrado"][index]
        proyectado = self._series["Proyectado"][index]
        self._crosshair.setPos(index)
        self._crosshair.setVisible(True)
        self._tooltip.setHtml(
            f"<div style='padding:2px 4px'>"
            f"<b>{self._months[index]}</b><br>"
            f"Cobrado: ${cobrado:,.2f}<br>"
            f"Proyectado: ${proyectado:,.2f}"
            f"</div>"
        )
        self._tooltip.setPos(index, max(cobrado, proyectado))
        self._tooltip.setVisible(True)
