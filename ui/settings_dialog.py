from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton, QFrame
)
from core import settings
from ui import widgets as W
from ui import theme as T


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(460)
        self.setStyleSheet(f"QDialog {{ background:{T.BG}; }}")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        root.addWidget(W.title("Settings", 15))

        card = W.card()
        self._remember = QCheckBox("Remember last used Tab")
        self._remember.setChecked(settings.get_remember_tab())
        self._remember.toggled.connect(settings.set_remember_tab)
        card.body.addWidget(self._remember)
        card.body.addWidget(W.muted(
            "When on, the app reopens on whichever tab you used last. "
            "When off, it always starts on World State."))
        root.addWidget(card)

        root.addStretch()
        btns = QHBoxLayout()
        btns.addStretch()
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        btns.addWidget(close)
        root.addLayout(btns)
