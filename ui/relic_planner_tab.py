from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QCompleter, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QStringListModel
from PyQt6.QtGui import QFont, QColor, QPixmap
import core.relic_api as relic_api
import core.images as images
from ui import widgets as W

RARITY_COLOR = {
    "Common": "#b08d57",
    "Uncommon": "#c0c0c0",
    "Rare": "#ffd700",
}


class RelicsLoader(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def run(self):
        try:
            self.done.emit(relic_api.get_relics())
        except Exception as e:
            self.error.emit(str(e))


class PricesLoader(QThread):
    price = pyqtSignal(int, object)  # row, plat or None
    finished_all = pyqtSignal()

    def __init__(self, items: list[str]):
        super().__init__()
        self.items = items

    def run(self):
        for row, name in enumerate(self.items):
            plat = relic_api.lowest_sell_price(name)
            self.price.emit(row, plat)
        self.finished_all.emit()


class RelicPlannerTab(QWidget):
    def __init__(self, _restore_state=None):
        super().__init__()
        self._relics = {}
        self._relics_thread = None
        self._prices_thread = None
        self._current_rewards = []
        self._restore_state_pending = _restore_state
        self._build_ui()
        self._load_relics()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QLabel("Relic Planner")
        f = QFont(); f.setBold(True); f.setPointSize(13)
        title.setFont(f)
        root.addWidget(title)

        bar = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Loading relics...")
        self._search.setEnabled(False)
        self._search.returnPressed.connect(self._show_relic)
        self._refine = QComboBox()
        self._refine.addItems(relic_api.STATES)
        self._refine.setCurrentText("Radiant")
        self._refine.currentIndexChanged.connect(self._show_relic)
        self._show_btn = QPushButton("Show")
        self._show_btn.setObjectName("primary")
        self._show_btn.setFixedWidth(80)
        self._show_btn.clicked.connect(self._show_relic)
        self._price_btn = QPushButton("Fetch Prices")
        self._price_btn.setFixedWidth(110)
        self._price_btn.clicked.connect(self._fetch_prices)
        self._price_btn.setEnabled(False)
        bar.addWidget(self._search)
        bar.addWidget(self._refine)
        bar.addWidget(self._show_btn)
        bar.addWidget(self._price_btn)
        root.addLayout(bar)

        self._status = QLabel("")
        self._status.setStyleSheet("color: #94a3b8;")
        root.addWidget(self._status)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["", "Reward", "Rarity", "Chance", "Price (p)"])
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(72)
        h = self._table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 76)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        root.addWidget(self._table)

        self._img_loaders = []
        self._row_icons = {}
        self._prices_by_name = {}
        self._price_names = []
        W.enable_header_sort(self._table, self._on_sort)

    def _save_state(self) -> dict:
        """Save state for theme change preservation."""
        return {
            "search_text": self._search.text(),
            "refine_state": self._refine.currentText(),
        }

    def _restore_state(self, state: dict):
        """Restore state after relics are loaded."""
        search_text = state.get("search_text", "")
        if search_text:
            self._search.setText(search_text)
        refine_state = state.get("refine_state", "Radiant")
        idx = self._refine.findText(refine_state)
        if idx >= 0:
            self._refine.setCurrentIndex(idx)
        if search_text:
            self._show_relic()

    def _load_relics(self):
        self._relics_thread = RelicsLoader()
        self._relics_thread.done.connect(self._on_relics)
        self._relics_thread.error.connect(lambda m: self._search.setPlaceholderText(f"Failed: {m}"))
        self._relics_thread.start()

    def _on_relics(self, relics: dict):
        self._relics = relics
        names = sorted(relics.keys(), key=relic_api.relic_sort_key)
        self._completer_model = QStringListModel(names)
        self._completer = QCompleter(self._completer_model, self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.setMaxVisibleItems(12)
        self._completer.activated.connect(lambda t: (self._search.setText(t), self._show_relic()))
        self._search.setCompleter(self._completer)
        self._search.setEnabled(True)
        self._search.setPlaceholderText("Type a relic (e.g. Meso F4)")
        # Restore state if pending
        if self._restore_state_pending:
            self._restore_state(self._restore_state_pending)
            self._restore_state_pending = None

    def _resolve(self, text: str):
        if text in self._relics:
            return text
        for k in self._relics:
            if k.lower() == text.lower():
                return k
        return None

    def _show_relic(self):
        key = self._resolve(self._search.text().strip())
        if not key:
            self._status.setText("Relic not found.")
            return
        state = self._refine.currentText()
        rewards = self._relics[key]["states"].get(state, [])
        self._current_rewards = sorted(rewards, key=lambda r: r.get("chance", 0), reverse=True)
        self._prices_by_name = {}
        self._render_rewards()
        self._status.setText(f"{key} ({state}) — {len(self._current_rewards)} rewards")
        self._price_btn.setEnabled(bool(self._current_rewards))

    def _render_rewards(self):
        rewards = self._current_rewards
        self._img_loaders = []
        self._row_icons = {}
        self._table.setRowCount(len(rewards))
        for i, rw in enumerate(rewards):
            icon = QLabel()
            icon.setFixedSize(64, 64)
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._row_icons[i] = icon
            self._table.setCellWidget(i, 0, icon)
            self._load_icon(i, rw["itemName"])

            name_item = QTableWidgetItem(rw["itemName"])
            rarity = rw.get("rarity", "")
            rarity_item = QTableWidgetItem(rarity)
            rarity_item.setForeground(QColor(RARITY_COLOR.get(rarity, "#e8eef7")))
            chance_item = QTableWidgetItem(f"{rw.get('chance', 0):.2f}%")
            chance_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            plat = self._prices_by_name.get(rw["itemName"])
            price_item = QTableWidgetItem("—" if plat is None else f"{plat}")
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if plat is not None:
                price_item.setForeground(QColor("#10b981"))
            self._table.setItem(i, 1, name_item)
            self._table.setItem(i, 2, rarity_item)
            self._table.setItem(i, 3, chance_item)
            self._table.setItem(i, 4, price_item)

    _RARITY_RANK = {"Common": 0, "Uncommon": 1, "Rare": 2, "Legendary": 3}

    def _on_sort(self, col, asc):
        if not self._current_rewards:
            return
        keys = {
            1: lambda r: r.get("itemName", "").lower(),
            2: lambda r: self._RARITY_RANK.get(r.get("rarity", ""), -1),
            3: lambda r: r.get("chance", 0),
            4: lambda r: self._prices_by_name.get(r["itemName"]) if self._prices_by_name.get(r["itemName"]) is not None else -1,
        }
        keyfn = keys.get(col)
        if keyfn:
            self._current_rewards.sort(key=keyfn, reverse=not asc)
            self._render_rewards()

    def _load_icon(self, row: int, item_name: str):
        url = relic_api.reward_icon_url(item_name)
        if not url:
            return
        overlay = relic_api.reward_subicon_url(item_name)
        loader = images.ImageLoader(str(row), url, overlay_url=overlay)
        loader.loaded.connect(self._on_icon)
        self._img_loaders.append(loader)
        loader.start()

    def _on_icon(self, key: str, pix: QPixmap):
        icon = self._row_icons.get(int(key))
        if icon:
            scaled = pix.scaled(
                icon.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon.setPixmap(scaled)

    def _fetch_prices(self):
        if self._prices_thread and self._prices_thread.isRunning():
            return
        if not self._current_rewards:
            return
        self._price_btn.setEnabled(False)
        self._status.setText("Fetching prices...")
        self._price_names = [rw["itemName"] for rw in self._current_rewards]
        self._prices_thread = PricesLoader(self._price_names)
        self._prices_thread.price.connect(self._on_price)
        self._prices_thread.finished_all.connect(self._on_prices_done)
        self._prices_thread.start()

    def _on_price(self, row: int, plat):
        if row >= len(self._price_names):
            return
        name = self._price_names[row]
        self._prices_by_name[name] = plat
        # update the visible cell for this item (row order may differ after sorting)
        for i in range(self._table.rowCount()):
            cell = self._table.item(i, 1)
            if cell and cell.text() == name:
                text = "—" if plat is None else f"{plat}"
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if plat is not None:
                    item.setForeground(QColor("#10b981"))
                self._table.setItem(i, 4, item)
                break

    def _on_prices_done(self):
        self._price_btn.setEnabled(True)
        prices = [p for p in self._prices_by_name.values() if p is not None]
        if prices:
            self._status.setText(f"Prices loaded — best reward: {max(prices)}p")
        else:
            self._status.setText("Prices loaded.")
