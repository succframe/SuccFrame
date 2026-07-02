from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QPushButton, QWidget, QHBoxLayout, QMenu, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter
from ui.world_state_tab import WorldStateTab
from ui.price_checker_tab import PriceCheckerTab
from ui.relic_planner_tab import RelicPlannerTab
from ui.search_item_tab import SearchItemTab
from ui.riven_mods_tab import RivenModsTab
from ui.health_dialog import HealthDialog
from ui.settings_dialog import SettingsDialog
from ui import theme
from core import settings
from core.update import __version__


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"SuccFrame v{__version__}")
        self.setMinimumSize(1000, 650)
        self.resize(1500, 975)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self._riven_state = None
        self._price_checker_state = None
        self._relic_planner_state = None
        self._add_tabs()
        self._build_corner()

        if settings.get_remember_tab():
            idx = settings.get_last_tab()
            if 0 <= idx < self.tabs.count():
                self.tabs.setCurrentIndex(idx)
        self.tabs.currentChanged.connect(settings.set_last_tab)

    def _add_tabs(self):
        self.price_checker = PriceCheckerTab(_restore_state=self._price_checker_state)
        self.search_item = SearchItemTab(open_price=self._open_in_price_checker)
        self.tabs.addTab(WorldStateTab(), "World State")
        self.tabs.addTab(self.search_item, "Search Item")
        self.tabs.addTab(self.price_checker, "Price Checker")
        self.relic_planner = RelicPlannerTab(_restore_state=self._relic_planner_state)
        self.tabs.addTab(self.relic_planner, "Relic Planner")
        self.riven_mods = RivenModsTab(_restore_state=self._riven_state)
        self.tabs.addTab(self.riven_mods, "Riven Mods")

    def _build_corner(self):
        corner = QWidget()
        lay = QHBoxLayout(corner)
        lay.setContentsMargins(0, 0, 6, 0)
        lay.setSpacing(8)

        theme_btn = QPushButton("Theme")
        theme_btn.setFixedWidth(110)
        menu = QMenu(theme_btn)
        for name, pal in theme.THEMES.items():
            act = menu.addAction(self._swatch(pal.get("SWATCH", pal["ACCENT"])), name)
            act.triggered.connect(lambda _, n=name: self._apply_theme(n))
        theme_btn.setMenu(menu)
        lay.addWidget(theme_btn)

        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self._open_settings)
        lay.addWidget(settings_btn)

        update_btn = QPushButton("Update Check")
        update_btn.setObjectName("primary")
        update_btn.clicked.connect(self._open_health)
        lay.addWidget(update_btn)

        self.tabs.setCornerWidget(corner, Qt.Corner.TopRightCorner)

    @staticmethod
    def _swatch(color: str) -> QIcon:
        """A rounded color chip previewing a theme, with an always-visible border."""
        pm = QPixmap(18, 18)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor("#9aa3b2"))
        p.setBrush(QColor(color))
        p.drawRoundedRect(1, 1, 16, 16, 5, 5)
        p.end()
        return QIcon(pm)

    def _apply_theme(self, name: str):
        theme.apply(QApplication.instance(), name)
        settings.set_theme(name)
        self._rebuild_tabs()

    def _rebuild_tabs(self):
        idx = self.tabs.currentIndex()
        # Save tab states before rebuilding
        if hasattr(self, 'riven_mods'):
            self._riven_state = self.riven_mods._save_state()
        if hasattr(self, 'price_checker'):
            self._price_checker_state = self.price_checker._save_state()
        if hasattr(self, 'relic_planner'):
            self._relic_planner_state = self.relic_planner._save_state()
        while self.tabs.count():
            w = self.tabs.widget(0)
            self.tabs.removeTab(0)
            w.deleteLater()
        self._add_tabs()
        self.tabs.setCurrentIndex(idx)

    def _open_in_price_checker(self, item_name: str):
        self.price_checker.search_for(item_name)
        self.tabs.setCurrentWidget(self.price_checker)

    def _open_settings(self):
        SettingsDialog(self).exec()

    def _open_health(self):
        HealthDialog(self).exec()
