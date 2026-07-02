"""Builds — a launcher for community build pages on Overframe.gg."""
import webbrowser
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QComboBox,
    QCompleter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QStringListModel

import core.items_api as items_api
import core.overframe as overframe
from ui import widgets as W
from ui import theme as T


BASE = "https://overframe.gg"


class ItemsLoader(QThread):
    done = pyqtSignal(dict); error = pyqtSignal(str)
    def run(self):
        try:
            frames = items_api.search("prime") + items_api.search("warframe")
            guns = items_api.search("rifle") + items_api.search("shotgun")
            pistols = items_api.search("pistol")
            melees = items_api.search("melee")
            self.done.emit({
                "Warframes": sorted({f["name"] for f in frames if f.get("category") == "Warframes"}),
                "Primary":   sorted({g["name"] for g in guns if g.get("category") == "Primary"}),
                "Secondary": sorted({p["name"] for p in pistols if p.get("category") == "Secondary"}),
                "Melee":     sorted({m["name"] for m in melees if m.get("category") == "Melee"}),
            })
        except Exception as e:
            self.error.emit(str(e))


class OverframeIdsWarmer(QThread):
    """Refresh the Overframe id map on tab open so the first click is instant."""
    def run(self):
        try:
            overframe.get_ids()
        except Exception:
            pass


class UrlResolver(QThread):
    """Resolve a name -> build URL off the UI thread.

    `overframe.build_url` may block on an HTTP sitemap fetch when the cache is
    empty, so we never call it directly from a slot.
    """
    done = pyqtSignal(str, str)   # name, url

    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def run(self):
        try:
            url = overframe.build_url(self.name)
        except Exception:
            url = f"{BASE}/"
        self.done.emit(self.name, url)


class BuildsTab(QWidget):
    def __init__(self, _restore_state=None):
        super().__init__()
        self._items = {"Warframes": [], "Primary": [], "Secondary": [], "Melee": []}
        self._loader = None
        self._id_warmer = None
        self._resolver = None
        self._build_ui()
        self._load_items()
        # Warm the Overframe id cache in the background so "Open builds" is instant.
        self._id_warmer = OverframeIdsWarmer()
        self._id_warmer.start()
        if _restore_state:
            self._restore_state(_restore_state)

    def _save_state(self) -> dict:
        return {
            "category": self._category.currentText(),
            "search_text": self._search.text(),
        }

    def _restore_state(self, state: dict):
        cat = state.get("category", "")
        idx = self._category.findText(cat)
        if idx >= 0:
            self._category.setCurrentIndex(idx)
        self._search.setText(state.get("search_text", ""))

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(12)

        root.addWidget(W.title("Builds — powered by Overframe", 15))
        root.addWidget(W.muted(
            "Look up community builds for any warframe or weapon. "
            "Picking one opens the build page on overframe.gg in your browser."))

        card = W.card()
        card.body.addWidget(W.header("Find a build"))

        pick = QHBoxLayout()
        self._category = QComboBox()
        self._category.addItems(list(self._items.keys()))
        self._category.setFixedWidth(140)
        self._category.currentTextChanged.connect(self._rebuild_completer)
        pick.addWidget(self._category)

        self._search = W.SearchLineEdit()
        self._search.setPlaceholderText("Loading items…")
        self._search.setEnabled(False)
        self._search.returnPressed.connect(self._go)
        pick.addWidget(self._search, 1)

        self._go_btn = QPushButton("Open builds ↗")
        self._go_btn.setObjectName("primary")
        self._go_btn.setFixedWidth(150)
        self._go_btn.clicked.connect(self._go)
        pick.addWidget(self._go_btn)
        card.body.addLayout(pick)

        self._status = W.muted("")
        card.body.addWidget(self._status)
        root.addWidget(card)

        # Extra shortcuts card
        shortcuts = W.card()
        shortcuts.body.addWidget(W.header("Quick links"))
        row = QHBoxLayout()
        for label, path in (
            ("Warframe Builds", "/builds/warframes/"),
            ("Primary Builds", "/builds/primary-weapons/"),
            ("Secondary Builds", "/builds/secondary-weapons/"),
            ("Melee Builds", "/builds/melee-weapons/"),
            ("Overframe Home", "/"),
        ):
            b = QPushButton(f"{label} ↗")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _, p=path: webbrowser.open(BASE + p))
            row.addWidget(b)
        row.addStretch()
        shortcuts.body.addLayout(row)
        root.addWidget(shortcuts)

        root.addStretch()

    def _load_items(self):
        self._search.setPlaceholderText("Loading items…")
        self._loader = ItemsLoader()
        self._loader.done.connect(self._on_items)
        self._loader.error.connect(lambda m: self._status.setText(f"Item list failed to load: {m}"))
        self._loader.start()

    def _on_items(self, items: dict):
        self._items = items
        self._search.setEnabled(True)
        self._search.setPlaceholderText("Type a name (e.g. Mesa Prime, Kuva Bramma)")
        self._rebuild_completer()

    def _rebuild_completer(self):
        names = self._items.get(self._category.currentText(), [])
        # Store model and completer on self so Python doesn't GC them out from
        # under Qt — the reason the dropdown was silently empty.
        self._completer_model = QStringListModel(names, self)
        self._completer = QCompleter(self._completer_model, self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.setMaxVisibleItems(12)
        # Picking a suggestion instantly opens the builds page.
        self._completer.activated.connect(
            lambda t: (self._search.setText(t), self._go()))
        self._search.setCompleter(self._completer)

    def _go(self):
        name = self._search.text().strip()
        if not name:
            self._status.setText("Type a name first.")
            return
        if self._resolver and self._resolver.isRunning():
            return
        self._go_btn.setEnabled(False)
        self._status.setText(f"Resolving {name}…")
        self._resolver = UrlResolver(name)
        self._resolver.done.connect(self._on_url_resolved)
        self._resolver.start()

    def _on_url_resolved(self, name: str, url: str):
        self._go_btn.setEnabled(True)
        webbrowser.open(url)
        if "/search/" in url:
            self._status.setText(
                f"Couldn't find a direct build page for '{name}' — opened Overframe search instead.")
        else:
            self._status.setText(f"Opened: {url}")
