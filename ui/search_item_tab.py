from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QScrollArea, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView
)
import webbrowser
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPixmap
import core.items_api as items_api
import core.market_api as market
import core.images as images
from ui import theme as T


def _wiki_url(name: str) -> str:
    return "https://wiki.warframe.com/w/" + name.strip().replace(" ", "_")

RARITY_COLOR = {
    "Common": "#b08d57", "Uncommon": "#c0c0c0", "Rare": "#ffd700",
    "Legendary": "#ef4444",
}


class SearchThread(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        try:
            self.done.emit(items_api.search(self.query))
        except Exception as e:
            self.error.emit(str(e))


class PriceThread(QThread):
    done = pyqtSignal(object)

    def __init__(self, name):
        super().__init__()
        self.name = name

    def run(self):
        try:
            self.done.emit(market.price_summary(self.name))
        except Exception:
            self.done.emit(None)


def _bold(text, size=11, color=None):
    color = color or T.TEXT
    lbl = QLabel(text)
    f = QFont(); f.setBold(True); f.setPointSize(size)
    lbl.setFont(f)
    lbl.setStyleSheet(f"color: {color};")
    return lbl


def _badge(text, color):
    b = QLabel(text)
    b.setStyleSheet(
        f"background: {T.SURFACE_2}; border: 1px solid {color}; border-radius: 9px; "
        f"padding: 2px 10px; color: {color};"
    )
    return b


class SearchItemTab(QWidget):
    def __init__(self, open_price=None):
        super().__init__()
        self._open_price = open_price
        self._results = []
        self._search_thread = None
        self._price_thread = None
        self._img_loader = None
        self._drop_img_loaders = []
        self._drop_icons_by_name = {}
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        root.addWidget(_bold("Search Item", 13))

        bar = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search any item — weapon, warframe, mod, prime part, set…")
        self._search.returnPressed.connect(self._do_search)
        self._btn = QPushButton("Search")
        self._btn.setObjectName("primary")
        self._btn.setFixedWidth(90)
        self._btn.clicked.connect(self._do_search)
        bar.addWidget(self._search)
        bar.addWidget(self._btn)
        root.addLayout(bar)

        self._picker = QComboBox()
        self._picker.setVisible(False)
        self._picker.currentIndexChanged.connect(self._on_pick)
        root.addWidget(self._picker)

        self._status = QLabel("")
        self._status.setStyleSheet(f"color: {T.MUTED};")
        root.addWidget(self._status)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._detail = QWidget()
        self._detail_layout = QVBoxLayout(self._detail)
        self._detail_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._detail_layout.setSpacing(10)
        scroll.setWidget(self._detail)
        root.addWidget(scroll)

    # ── search ───────────────────────────────────────────────────────────

    def _do_search(self):
        q = self._search.text().strip()
        if not q:
            return
        if self._search_thread and self._search_thread.isRunning():
            return
        self._btn.setEnabled(False)
        self._status.setText("Searching...")
        self._search_thread = SearchThread(q)
        self._search_thread.done.connect(self._on_results)
        self._search_thread.error.connect(self._on_error)
        self._search_thread.start()

    def _on_error(self, msg):
        self._btn.setEnabled(True)
        self._status.setText(f"Error: {msg}")

    def _on_results(self, results):
        self._btn.setEnabled(True)
        self._results = results
        if not results:
            self._picker.setVisible(False)
            self._status.setText("No items found.")
            self._clear_detail()
            return
        self._status.setText(f"{len(results)} match(es).")
        self._picker.blockSignals(True)
        self._picker.clear()
        for it in results:
            label = f"{it.get('name', '?')}  —  {it.get('type', it.get('category', ''))}"
            self._picker.addItem(label)
        self._picker.blockSignals(False)
        self._picker.setVisible(len(results) > 1)
        self._picker.setCurrentIndex(0)
        self._render(results[0])

    def _on_pick(self, idx):
        if 0 <= idx < len(self._results):
            self._render(self._results[idx])

    # ── render ───────────────────────────────────────────────────────────

    def _clear_detail(self):
        while self._detail_layout.count():
            item = self._detail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _render(self, item: dict):
        self._clear_detail()

        # Header
        header = QHBoxLayout()
        self._img = QLabel()
        self._img.setFixedSize(120, 120)
        self._img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self._img)
        url = items_api.image_url(item)
        if url:
            self._img_loader = images.ImageLoader("img", url)
            self._img_loader.loaded.connect(lambda k, p: self._img.setPixmap(
                p.scaled(self._img.size(), Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)))
            self._img_loader.start()

        info = QVBoxLayout()
        info.setSpacing(4)
        info.addWidget(_bold(item.get("name", "?"), 15))
        meta = item.get("type") or item.get("category") or ""
        if item.get("category") and item.get("category") not in meta:
            meta = f"{meta}  ·  {item['category']}"
        info.addWidget(QLabel(meta))

        badges = QHBoxLayout()
        badges.setSpacing(6)
        if item.get("masteryReq"):
            badges.addWidget(_badge(f"MR {item['masteryReq']}", "#94a3b8"))
        if item.get("isPrime"):
            badges.addWidget(_badge("Prime", "#f0b429"))
        if item.get("vaulted"):
            badges.addWidget(_badge("Vaulted", "#ef4444"))
        badges.addStretch()
        info.addLayout(badges)
        header.addLayout(info, 1)
        self._detail_layout.addLayout(header)

        # Description (word-wrapped so it never clips)
        desc = (item.get("description") or "").strip()
        if desc:
            dlbl = QLabel(desc)
            dlbl.setWordWrap(True)
            dlbl.setStyleSheet(f"color: {T.MUTED};")
            self._detail_layout.addWidget(dlbl)

        # How to get
        self._detail_layout.addWidget(_bold("How to Get", 12))
        drops = items_api.collect_drops(item)
        if drops:
            self._detail_layout.addWidget(self._drops_table(drops, item))
        else:
            self._detail_layout.addWidget(
                QLabel("No drop data available — check the Warframe Wiki below for how to obtain this item."))

        build = self._build_line(item)
        if build:
            lbl = QLabel(build)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color: {T.MUTED};")
            self._detail_layout.addWidget(lbl)

        # Wiki link (always available; the definitive source for locations)
        wiki_btn = QPushButton("View on Warframe Wiki ▸")
        wiki_btn.setFixedWidth(200)
        wiki_btn.clicked.connect(lambda: webbrowser.open(_wiki_url(item.get("name", ""))))
        self._detail_layout.addWidget(wiki_btn)

        # Market
        self._detail_layout.addWidget(_bold("Market (warframe.market)", 12))
        self._market_lbl = QLabel("Checking warframe.market…")
        self._market_lbl.setStyleSheet(f"color: {T.MUTED};")
        self._market_lbl.setWordWrap(True)
        self._detail_layout.addWidget(self._market_lbl)
        self._load_price(item.get("name", ""))

    def _drops_table(self, drops, item):
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["", "Part", "Location", "Chance", "Rarity", ""])
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(88)
        h = table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(0, 92)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        self._drops_tbl = table
        self._current_drops = drops[:120]
        self._drops_item = item
        from ui import widgets as W
        W.enable_header_sort(table, self._on_drops_sort)
        self._populate_drops()
        return table

    _DROP_RARITY_RANK = {"Common": 0, "Uncommon": 1, "Rare": 2, "Legendary": 3}

    def _on_drops_sort(self, col, asc):
        keys = {
            1: lambda d: (d.get("part") or "").lower(),
            2: lambda d: (d.get("location") or "").lower(),
            3: lambda d: d.get("chance", 0),
            4: lambda d: self._DROP_RARITY_RANK.get(d.get("rarity", ""), -1),
        }
        keyfn = keys.get(col)
        if keyfn:
            self._current_drops.sort(key=keyfn, reverse=not asc)
            self._populate_drops()

    def _populate_drops(self):
        table = self._drops_tbl
        item = self._drops_item
        shown = self._current_drops
        table.setRowCount(len(shown))
        self._drop_img_loaders = []
        icons_by_name = {}   # full_name -> [QLabel, ...]

        for i, dr in enumerate(shown):
            icon = QLabel()
            icon.setFixedSize(80, 80)
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setCellWidget(i, 0, icon)
            icons_by_name.setdefault(dr["full_name"], []).append(icon)

            part = QTableWidgetItem(dr["part"] or "—")
            part.setForeground(QColor("#94a3b8"))
            loc = QTableWidgetItem(dr["location"])
            chance = QTableWidgetItem(f"{dr['chance']:.2f}%")
            chance.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            rarity = QTableWidgetItem(dr["rarity"])
            rarity.setForeground(QColor(RARITY_COLOR.get(dr["rarity"], "#e8eef7")))
            table.setItem(i, 1, part)
            table.setItem(i, 2, loc)
            table.setItem(i, 3, chance)
            table.setItem(i, 4, rarity)

            relic = self._relic_name(dr["location"])
            if relic and self._open_price:
                btn = QPushButton("Check price ▸")
                btn.setFixedWidth(120)
                btn.clicked.connect(lambda _, r=relic: self._open_price(r))
                table.setCellWidget(i, 5, btn)

        # Load each unique part image once, apply to all its rows.
        # Prefer warframe.market (composited part badges); fall back to the
        # warframestat game image for resources / mods / non-market items.
        self._drop_icons_by_name = icons_by_name
        item_img = items_api.image_url(item)
        for name in icons_by_name:
            icon_url, sub_url = market.images_for_name(name)
            if not icon_url:
                icon_url, sub_url = item_img, None   # fallback: the searched item's own image
            if not icon_url:
                continue
            loader = images.ImageLoader(name, icon_url, overlay_url=sub_url)
            loader.loaded.connect(self._on_drop_icon)
            self._drop_img_loaders.append(loader)
            loader.start()

        table.setMinimumHeight(min(len(shown) * 88 + 40, 500))

    @staticmethod
    def _relic_name(location: str) -> str | None:
        """Extract a tradeable relic name from a drop location, e.g.
        'Lith M2 Relic (Radiant)' -> 'Lith M2 Relic'. None if not a relic."""
        if not location or "Relic" not in location:
            return None
        return location.split(" (")[0].strip()

    def _on_drop_icon(self, name, pix):
        for label in self._drop_icons_by_name.get(name, []):
            label.setPixmap(pix.scaled(
                label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))

    def _build_line(self, item):
        price = item.get("buildPrice")
        btime = item.get("buildTime")
        comps = item.get("components") or []
        if not price and not comps:
            return ""
        parts = []
        if comps:
            names = [c.get("name") for c in comps if c.get("name")]
            parts.append("Build recipe: " + ", ".join(names))
        if price:
            hrs = f", {btime // 3600}h build" if btime else ""
            parts.append(f"({price:,} credits{hrs})")
        return "  ".join(parts)

    # ── market price ─────────────────────────────────────────────────────

    def _load_price(self, name):
        if self._price_thread and self._price_thread.isRunning():
            return
        self._price_thread = PriceThread(name)
        self._price_thread.done.connect(self._on_price)
        self._price_thread.start()

    def _on_price(self, summary):
        if summary is None:
            self._market_lbl.setText("Not tradable / not listed on warframe.market.")
            return
        if summary["lowest"] is None:
            self._market_lbl.setText("Tradable, but no sellers online right now.")
            return
        sellers = "   ".join(f"{n} ({p}p)" for n, p, _ in summary["top"])
        self._market_lbl.setText(
            f"Tradable  ·  lowest {summary['lowest']}p  ·  {summary['online']} sellers online\n"
            f"Top sellers:  {sellers}"
        )
