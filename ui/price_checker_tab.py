from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QCompleter, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QAbstractItemView, QApplication, QToolButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QStringListModel, QSize
from PyQt6.QtGui import QColor, QPixmap, QIcon
import core.market_api as api
import core.images as images
from core import settings
from ui import widgets as W
from ui import theme as T
from ui.charts import PriceHistoryChart

FAV_KIND = "price"


class StatsLoader(QThread):
    done = pyqtSignal(dict); error = pyqtSignal(str)
    def __init__(self, slug): super().__init__(); self.slug = slug
    def run(self):
        try: self.done.emit(api.get_statistics(self.slug))
        except Exception as e: self.error.emit(str(e))

STATUS_ORDER = {"ingame": 0, "online": 1, "offline": 2}
STATUS_COLOR = {"ingame": T.GREEN, "online": T.GOLD, "offline": T.MUTED}


class ItemsLoader(QThread):
    done = pyqtSignal(list); error = pyqtSignal(str)
    def run(self):
        try: self.done.emit(api.get_all_items())
        except Exception as e: self.error.emit(str(e))


class DetailLoader(QThread):
    done = pyqtSignal(dict); error = pyqtSignal(str)
    def __init__(self, slug): super().__init__(); self.slug = slug
    def run(self):
        try: self.done.emit(api.get_item_detail(self.slug))
        except Exception as e: self.error.emit(str(e))


class OrdersLoader(QThread):
    done = pyqtSignal(list); error = pyqtSignal(str)
    def __init__(self, slug): super().__init__(); self.slug = slug
    def run(self):
        try: self.done.emit(api.get_orders(self.slug))
        except Exception as e: self.error.emit(str(e))


class PriceCheckerTab(QWidget):
    def __init__(self, _restore_state=None):
        super().__init__()
        self._name_to_slug = {}
        self._orders_thread = self._items_thread = self._detail_thread = None
        self._stats_thread = None
        self._orders = []
        self._img_loaders = []
        self._member_btns = {}
        self._active_slug = self._set_slug = None
        self._set_name = self._current_item_name = ""
        self._current_ducats = None
        self._side_sell = True
        self._sort = None   # (column, ascending) or None for default
        self._restore_state_pending = _restore_state
        self._build_ui()
        self._load_items()

    # ── UI ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(12)

        root.addWidget(W.title("Price Checker", 15))

        bar = QHBoxLayout()
        self._search = W.SearchLineEdit()
        self._search.setPlaceholderText("Loading item list…")
        self._search.setEnabled(False)
        self._search.returnPressed.connect(self._on_search)
        self._btn = QPushButton("Check")
        self._btn.setObjectName("primary")
        self._btn.setFixedWidth(100)
        self._btn.clicked.connect(self._on_search)
        self._star = W.star_button(False)
        self._star.setEnabled(False)
        self._star.clicked.connect(self._toggle_favorite)
        self._favs_btn = W.favorites_menu_button(
            lambda: settings.get_favorites(FAV_KIND), self.search_for)
        bar.addWidget(self._search)
        bar.addWidget(self._btn)
        bar.addWidget(self._star)
        bar.addWidget(self._favs_btn)
        root.addLayout(bar)

        self._status = W.muted("")
        root.addWidget(self._status)

        cols = QHBoxLayout()
        cols.setSpacing(12)

        # Left showcase
        self._showcase = W.card()
        self._showcase.setFixedWidth(300)
        self._showcase_body = self._showcase.body
        self._showcase.hide()
        cols.addWidget(self._showcase)

        # Right order book
        book = W.card()
        book.body.setSpacing(10)
        head = QHBoxLayout()
        head.addWidget(W.header("Order Book"))
        head.addStretch()
        self._sell_btn = QPushButton("Sell")
        self._buy_btn = QPushButton("Buy")
        for b in (self._sell_btn, self._buy_btn):
            b.setCheckable(True); b.setFixedWidth(70)
        self._sell_btn.setChecked(True)
        self._sell_btn.clicked.connect(lambda: self._set_side(True))
        self._buy_btn.clicked.connect(lambda: self._set_side(False))
        head.addWidget(self._sell_btn)
        head.addWidget(self._buy_btn)
        book.body.addLayout(head)

        self._book_status = W.muted("Search an item to see live orders.")
        book.body.addWidget(self._book_status)

        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(["", "Platinum", "Ducats", "Seller", "Rep", "Rank", ""])
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(42)
        h = self._table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(6, 96)
        book.body.addWidget(self._table)
        W.enable_header_sort(self._table, self._on_sort)
        cols.addWidget(book, 1)

        root.addLayout(cols, 1)

        # Price history chart
        self._chart_card = W.card()
        header_row = QHBoxLayout()
        header_row.addWidget(W.header("Price History — 90 days"))
        header_row.addStretch()
        self._trend_lbl = W.muted("")
        header_row.addWidget(self._trend_lbl)
        self._chart_card.body.addLayout(header_row)
        self._chart = PriceHistoryChart()
        self._chart_card.body.addWidget(self._chart)
        self._chart_card.hide()
        root.addWidget(self._chart_card)

    def _toggle_favorite(self):
        name = self._current_item_name
        if not name:
            return
        if settings.is_favorite(FAV_KIND, name):
            settings.remove_favorite(FAV_KIND, name)
            self._star.set_active(False)
        else:
            settings.add_favorite(FAV_KIND, name)
            self._star.set_active(True)

    def _refresh_star(self):
        name = self._current_item_name
        self._star.setEnabled(bool(name))
        self._star.set_active(bool(name) and settings.is_favorite(FAV_KIND, name))

    def _set_side(self, sell):
        self._side_sell = sell
        self._sell_btn.setChecked(sell)
        self._buy_btn.setChecked(not sell)
        self._rebuild_table()

    def _save_state(self) -> dict:
        """Save state for theme change preservation."""
        return {
            "active_slug": self._active_slug,
            "current_item_name": self._current_item_name,
            "side_sell": self._side_sell,
            "sort": self._sort,
        }

    def _restore_state(self, state: dict):
        """Restore state after items are loaded."""
        slug = state.get("active_slug")
        if slug and slug in self._name_to_slug.values():
            self._active_slug = slug
            self._current_item_name = state.get("current_item_name", "")
            side_sell = state.get("side_sell", True)
            self._set_side(side_sell)
            if self._sort:
                col, asc = self._sort
                self._on_sort(col, asc)
            self._detail_thread = DetailLoader(slug)
            self._detail_thread.done.connect(lambda d, s=slug: self._on_detail(s, d))
            self._detail_thread.start()

    # ── items / autocomplete ─────────────────────────────────────────────
    def _load_items(self):
        self._items_thread = ItemsLoader()
        self._items_thread.done.connect(self._on_items_loaded)
        self._items_thread.error.connect(lambda m: self._search.setPlaceholderText(f"Failed: {m}"))
        self._items_thread.start()

    def _on_items_loaded(self, items):
        self._name_to_slug = {it["name"]: it["slug"] for it in items}
        self._completer_model = QStringListModel(sorted(self._name_to_slug))
        self._completer = QCompleter(self._completer_model, self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.setMaxVisibleItems(12)
        self._completer.activated.connect(lambda t: (self._search.setText(t), self._on_search()))
        self._search.setCompleter(self._completer)
        self._search.setEnabled(True)
        self._search.setPlaceholderText("Type an item name (e.g. Mesa Prime Set)")
        # Restore state if pending
        if self._restore_state_pending:
            self._restore_state(self._restore_state_pending)
            self._restore_state_pending = None

    def search_for(self, name: str):
        """Programmatically search an item (used by cross-tab navigation)."""
        self._search.setText(name)
        self._on_search()

    # ── search ───────────────────────────────────────────────────────────
    def _on_search(self):
        name = self._search.text().strip()
        if not name:
            return
        slug = self._name_to_slug.get(name)
        display = name
        if not slug:
            for k, v in self._name_to_slug.items():
                if k.lower() == name.lower():
                    slug, display = v, k
                    break
        if not slug:
            self._status.setText(f"Item not found: {name}")
            return
        self._search_slug(slug, display)

    def _search_slug(self, slug, display):
        # No isRunning guard: the user should always be able to switch items.
        # Stale callbacks are filtered by comparing their slug to _active_slug.
        self._active_slug = slug
        self._current_item_name = display
        self._status.setText(f"Loading {display}…")
        self._btn.setEnabled(False)
        self._orders_thread = OrdersLoader(slug)
        self._orders_thread.done.connect(lambda orders, s=slug: self._on_orders(s, orders))
        self._orders_thread.error.connect(self._on_error)
        self._orders_thread.start()
        self._detail_thread = DetailLoader(slug)
        self._detail_thread.done.connect(lambda d, s=slug: self._on_detail(s, d))
        self._detail_thread.start()
        self._load_stats(slug)

    def _load_stats(self, slug):
        self._chart_card.show()
        self._chart.set_points([])
        self._trend_lbl.setText("loading history…")
        self._stats_thread = StatsLoader(slug)
        self._stats_thread.done.connect(lambda data, s=slug: self._on_stats(s, data))
        self._stats_thread.error.connect(lambda _: self._trend_lbl.setText(""))
        self._stats_thread.start()

    def _on_stats(self, slug, data):
        if slug != self._active_slug:
            return  # stale response from a previous item
        points = data.get("points", [])
        self._chart.set_points(points)
        if len(points) < 2:
            self._trend_lbl.setText("")
            return
        first, last = points[0]["avg"], points[-1]["avg"]
        pct = (last - first) / first * 100 if first else 0
        arrow = "▲" if pct >= 0 else "▼"
        color = T.GREEN if pct >= 0 else T.RED
        # inline color via stylesheet
        self._trend_lbl.setText(f"{arrow} {abs(pct):.1f}% (avg {int(last)}p vs {int(first)}p)")
        self._trend_lbl.setStyleSheet(f"color:{color}; font-weight:600; background:transparent;")

    def _go_to_set(self):
        if self._set_slug and self._set_slug != self._active_slug:
            self._search_slug(self._set_slug, self._set_name)

    def _on_error(self, msg):
        self._btn.setEnabled(True)
        self._status.setText(f"Error: {msg}")

    # ── showcase (left) ──────────────────────────────────────────────────
    def _on_detail(self, slug, d):
        if slug != self._active_slug:
            return  # stale response from a previous item
        self._img_loaders = []
        self._member_btns = {}
        while self._showcase_body.count():
            it = self._showcase_body.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
            elif it.layout():
                self._clear_layout(it.layout())

        self._current_ducats = d.get("ducats")
        self._rebuild_table()
        self._refresh_star()
        members = d.get("members", [])
        set_m = next((m for m in members if m["is_set"]), None)
        self._set_slug = set_m["slug"] if set_m else d["slug"]
        self._set_name = set_m["name"] if set_m else d["name"]

        img = QLabel()
        img.setFixedSize(150, 150)
        img.setScaledContents(True)
        img.setCursor(Qt.CursorShape.PointingHandCursor)
        img.setToolTip("Click to view the full set")
        img.mousePressEvent = lambda e: self._go_to_set()
        self._hero_img = img
        wrap = QHBoxLayout(); wrap.addStretch(); wrap.addWidget(img); wrap.addStretch()
        self._showcase_body.addLayout(wrap)
        if d.get("icon"):
            overlay = api.asset_url(d["subicon"]) if d.get("subicon") else None
            self._load_image("hero", api.asset_url(d["icon"]), overlay)

        name = W.title(d["name"], 13)
        name.setWordWrap(True)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._showcase_body.addWidget(name)

        chips = QHBoxLayout(); chips.setSpacing(6); chips.addStretch()
        if d.get("mastery") is not None:
            chips.addWidget(W.chip(f"MR {d['mastery']}", T.MUTED))
        if d.get("ducats") is not None:
            chips.addWidget(W.chip(f"{d['ducats']} ducats", T.BLUE))
        chips.addStretch()
        self._showcase_body.addLayout(chips)
        if d.get("trading_tax") is not None:
            tax = W.muted(f"Trading tax: {d['trading_tax']:,} cr")
            tax.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._showcase_body.addWidget(tax)

        if members:
            self._showcase_body.addWidget(W.hline())
            self._showcase_body.addWidget(W.header("Parts"))
            for m in members:
                self._showcase_body.addWidget(self._member_button(m))
        self._showcase_body.addStretch()
        self._showcase.show()

    def _member_button(self, m):
        slug = m["slug"]
        active = slug == self._active_slug
        btn = QToolButton()
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        btn.setIconSize(QSize(28, 28))
        btn.setText("  " + self._short_label(m["name"]))
        btn.setToolTip(m["name"])
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(36)
        c = T.ACCENT if active else T.BORDER
        btn.setStyleSheet(
            f"QToolButton {{ border:1px solid {c}; border-radius:8px; padding:3px 8px; "
            f"color:{T.TEXT if active else T.MUTED}; background:{W.rgba(T.ACCENT,0.10) if active else 'transparent'}; text-align:left; }}"
            f"QToolButton:hover {{ border-color:{T.ACCENT}; color:{T.TEXT}; }}")
        btn.clicked.connect(lambda _, s=slug, n=m["name"]: self._search_slug(s, n))
        self._member_btns[slug] = btn
        if m.get("icon"):
            ov = api.asset_url(m["subicon"]) if m.get("subicon") else None
            self._load_image(f"member:{slug}", api.asset_url(m["icon"]), ov)
        return btn

    @staticmethod
    def _short_label(name):
        if name.endswith(" Set"):
            return "Set"
        if " Prime " in name:
            return name.split(" Prime ", 1)[1]
        return name

    def _load_image(self, key, url, overlay=None):
        loader = images.ImageLoader(key, url, overlay_url=overlay)
        loader.loaded.connect(self._on_image)
        self._img_loaders.append(loader)
        loader.start()

    def _on_image(self, key, pix):
        if key == "hero" and hasattr(self, "_hero_img"):
            self._hero_img.setPixmap(pix)
        elif key.startswith("member:"):
            btn = self._member_btns.get(key[len("member:"):])
            if btn:
                btn.setIcon(QIcon(pix))

    def _clear_layout(self, lay):
        while lay.count():
            it = lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
            elif it.layout():
                self._clear_layout(it.layout())

    # ── order book (right) ───────────────────────────────────────────────
    def _on_orders(self, slug, orders):
        if slug != self._active_slug:
            return  # stale response from a previous item
        self._btn.setEnabled(True)
        self._orders = orders
        self._rebuild_table()

    def _on_sort(self, col, asc):
        self._sort = (col, asc)
        self._rebuild_table()

    def _rebuild_table(self):
        want = "sell" if self._side_sell else "buy"
        rows = [o for o in self._orders if o.get("type") == want]
        if self._sort:
            col, asc = self._sort
            keys = {
                0: lambda o: STATUS_ORDER.get(o.get("user", {}).get("status", "offline"), 3),
                1: lambda o: o.get("platinum", 0),
                3: lambda o: o.get("user", {}).get("ingameName", "").lower(),
                4: lambda o: o.get("user", {}).get("reputation", 0),
                5: lambda o: (o.get("rank") if o.get("rank") is not None else -1),
            }
            keyfn = keys.get(col)
            if keyfn:
                rows.sort(key=keyfn, reverse=not asc)
        else:
            rows.sort(key=lambda o: (
                STATUS_ORDER.get(o.get("user", {}).get("status", "offline"), 3),
                o.get("platinum", 0) if want == "sell" else -o.get("platinum", 0)))

        self._table.setRowCount(len(rows))
        for i, o in enumerate(rows):
            user = o.get("user", {})
            status = user.get("status", "offline")
            plat = o.get("platinum", 0)
            qty = o.get("quantity", 1)
            rank = o.get("rank")

            dot = QTableWidgetItem("●")
            dot.setForeground(QColor(STATUS_COLOR.get(status, T.MUTED)))
            dot.setToolTip(status)
            dot.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            price = QTableWidgetItem(f"{plat}p" + (f"  ×{qty}" if qty > 1 else ""))
            price.setForeground(QColor(T.TEXT))
            f = price.font(); f.setBold(True); price.setFont(f)

            duc = QTableWidgetItem("—" if self._current_ducats is None else f"{self._current_ducats}d")
            duc.setForeground(QColor(T.BLUE))
            duc.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            seller = QTableWidgetItem(user.get("ingameName", "?"))
            rep = QTableWidgetItem(str(user.get("reputation", 0)))
            rep.setForeground(QColor(T.MUTED))
            rep.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            rk = QTableWidgetItem("—" if rank is None else str(rank))
            rk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self._table.setItem(i, 0, dot)
            self._table.setItem(i, 1, price)
            self._table.setItem(i, 2, duc)
            self._table.setItem(i, 3, seller)
            self._table.setItem(i, 4, rep)
            self._table.setItem(i, 5, rk)

            msg = self._build_whisper(want, user.get("ingameName", ""), plat, rank)
            copy = QPushButton("Copy")
            copy.setCursor(Qt.CursorShape.PointingHandCursor)
            copy.setFixedSize(64, 28)
            copy.setStyleSheet(
                f"QPushButton {{ background:transparent; color:{T.ACCENT_HI}; "
                f"border:1px solid {T.BORDER}; border-radius:6px; padding:0; "
                f"font-size:12px; font-weight:600; }}"
                f"QPushButton:hover {{ border-color:{T.ACCENT}; color:{T.TEXT}; "
                f"background:{W.rgba(T.ACCENT,0.12)}; }}")
            copy.clicked.connect(lambda _, m=msg: self._copy(m))
            holder = QWidget()
            holder.setStyleSheet("background: transparent;")
            hl = QHBoxLayout(holder)
            hl.setContentsMargins(4, 0, 10, 0)   # right margin clears the scrollbar
            hl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            hl.addWidget(copy)
            self._table.setCellWidget(i, 6, holder)

        if rows:
            best = rows[0].get("platinum", 0)
            online = sum(1 for o in rows if o.get("user", {}).get("status") in ("ingame", "online"))
            self._status.setText(f"{self._current_item_name}")
            self._book_status.setText(f"{len(rows)} {want} orders · best {best}p · {online} online")
        else:
            self._book_status.setText(f"No {want} orders found.")

    def _build_whisper(self, want, seller, plat, rank):
        action = "buy" if want == "sell" else "sell"
        rank_txt = f" (rank {rank})" if rank is not None else ""
        return (f'/w {seller} Hi! I want to {action}: "{self._current_item_name}"{rank_txt} '
                f'for {plat} platinum. (warframe.market)')

    def _copy(self, message):
        QApplication.clipboard().setText(message)
        self._book_status.setText("Copied — paste in-game with Ctrl+V.")
