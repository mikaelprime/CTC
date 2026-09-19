from PySide6.QtWidgets import QLabel

from theme import STATUS_COLORS


def make_badge(text: str, kind: str = "info") -> QLabel:
    color = STATUS_COLORS.get(kind, STATUS_COLORS["info"])
    label = QLabel(text)
    label.setObjectName("Badge")
    label.setStyleSheet(f"background-color: rgba(0,0,0,0.001); color: {color}; font-weight: 600;")
    return label
