import webbrowser
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import core.health as health
import core.update as update
from ui import widgets as W
from ui import theme as T


class CheckThread(QThread):
    result = pyqtSignal(int, bool, str)   # index, ok, message
    finished_all = pyqtSignal()

    def run(self):
        for i, entry in enumerate(health.CHECKS):
            ok, msg = health.check_one(entry)
            self.result.emit(i, ok, msg)
        self.finished_all.emit()


class UpdateThread(QThread):
    done = pyqtSignal(str, object, str)   # state, latest_version, url

    def run(self):
        state, latest, url = update.check_for_update()
        self.done.emit(state, latest, url)


class HealthDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Update Check — API Status")
        self.setMinimumWidth(620)
        self.setStyleSheet(f"QDialog {{ background:{T.BG}; }}")
        self._thread = None
        self._update_thread = None
        self._update_url = update.RELEASES_URL
        self._status_labels = []
        self._build_ui()
        self._check_update()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        # Version / update banner
        banner = W.card()
        row = QHBoxLayout()
        self._update_lbl = QLabel(f"SuccFrame v{update.__version__} — checking for updates…")
        self._update_lbl.setStyleSheet(f"color:{T.MUTED}; font-weight:600;")
        row.addWidget(self._update_lbl)
        row.addStretch()
        self._update_btn = QPushButton("Download Update")
        self._update_btn.setObjectName("primary")
        self._update_btn.clicked.connect(lambda: webbrowser.open(self._update_url))
        self._update_btn.hide()
        row.addWidget(self._update_btn)
        banner.body.addLayout(row)
        root.addWidget(banner)

        root.addWidget(W.title("API Status", 15))
        root.addWidget(W.muted(
            "Checks every external service SuccFrame relies on. "
            "If a tab stops working, run this to see which API is down."))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        grid = QGridLayout(body)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(0, 1)

        for i, entry in enumerate(health.CHECKS):
            name = W.value(entry["name"], size=12)
            tab = W.muted(entry.get("tab", ""))
            col = QVBoxLayout(); col.setSpacing(1)
            col.addWidget(name); col.addWidget(tab)
            wrap = QWidget(); wrap.setLayout(col)
            grid.addWidget(wrap, i, 0)
            status = QLabel("—")
            status.setStyleSheet(f"color:{T.MUTED};")
            status.setWordWrap(True)
            self._status_labels.append(status)
            grid.addWidget(status, i, 1, Qt.AlignmentFlag.AlignRight)

        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        btns = QHBoxLayout()
        self._check_btn = QPushButton("Check APIs")
        self._check_btn.setObjectName("primary")
        self._check_btn.clicked.connect(self._run_checks)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        btns.addWidget(self._check_btn)
        btns.addStretch()
        btns.addWidget(close)
        root.addLayout(btns)

    def _check_update(self):
        self._update_thread = UpdateThread()
        self._update_thread.done.connect(self._on_update)
        self._update_thread.start()

    def _on_update(self, state, latest, url):
        self._update_url = url
        if state == "outdated":
            self._update_lbl.setText(
                f"Update available: v{latest}  ·  you have v{update.__version__}")
            self._update_lbl.setStyleSheet(f"color:{T.GOLD}; font-weight:700;")
            self._update_btn.show()
        elif state == "current":
            self._update_lbl.setText(f"SuccFrame v{update.__version__} — up to date ✓")
            self._update_lbl.setStyleSheet(f"color:{T.GREEN}; font-weight:600;")
        else:
            self._update_lbl.setText(
                f"SuccFrame v{update.__version__} — couldn't check for updates")
            self._update_lbl.setStyleSheet(f"color:{T.MUTED}; font-weight:600;")

    def _run_checks(self):
        if self._thread and self._thread.isRunning():
            return
        self._check_btn.setEnabled(False)
        self._check_btn.setText("Checking…")
        for lbl in self._status_labels:
            lbl.setText("checking…")
            lbl.setStyleSheet(f"color:{T.MUTED};")
        self._thread = CheckThread()
        self._thread.result.connect(self._on_result)
        self._thread.finished_all.connect(self._on_done)
        self._thread.start()

    def _on_result(self, i, ok, msg):
        lbl = self._status_labels[i]
        color = T.GREEN if ok else T.RED
        prefix = "●  Up" if ok else "●  Down"
        text = f"{prefix}" if ok else f"{prefix} — {msg}"
        lbl.setText(text)
        lbl.setStyleSheet(f"color:{color}; font-weight:600;")

    def _on_done(self):
        self._check_btn.setEnabled(True)
        self._check_btn.setText("Check APIs")
