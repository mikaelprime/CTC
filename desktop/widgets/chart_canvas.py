import matplotlib

matplotlib.use("QtAgg")

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from theme import BG, BORDER, SURFACE, TEXT, TEXT_MUTED


class ChartCanvas(FigureCanvasQTAgg):
    def __init__(self, width=5, height=3.2):
        fig = Figure(figsize=(width, height), dpi=100)
        fig.patch.set_facecolor(SURFACE)
        super().__init__(fig)
        self.fig = fig

    def new_axes(self):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor(SURFACE)
        for spine in ax.spines.values():
            spine.set_color(BORDER)
        ax.tick_params(colors=TEXT_MUTED, labelsize=8)
        ax.xaxis.label.set_color(TEXT_MUTED)
        ax.yaxis.label.set_color(TEXT_MUTED)
        return ax

    def render(self, top: float = 0.95):
        self.fig.tight_layout(rect=(0, 0, 1, top))
        self.draw()
