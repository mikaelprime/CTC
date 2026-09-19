from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from theme import STATUS_COLORS


class KpiCard(QFrame):
    def __init__(self, label: str, value: str, sub: str = "", sub_kind: str = "info", parent=None):
        super().__init__(parent)
        self.setObjectName("KpiCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        self.label = QLabel(label)
        self.label.setObjectName("KpiLabel")
        self.value = QLabel(value)
        self.value.setObjectName("KpiValue")
        self.sub = QLabel(sub)
        self.sub.setObjectName("KpiSub")

        layout.addWidget(self.label)
        layout.addWidget(self.value)
        layout.addWidget(self.sub)
        self.set_sub(sub, sub_kind)

    def set_value(self, value: str) -> None:
        self.value.setText(value)

    def set_sub(self, sub: str, kind: str = "info") -> None:
        self.sub.setText(sub)
        color = STATUS_COLORS.get(kind, STATUS_COLORS["info"])
        self.sub.setStyleSheet(f"color: {color}; font-size: 11px;")
