"""Reusable dashboard components shared across tabs."""
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMenu, QLineEdit,
    QComboBox
)
from PyQt6.QtCore import Qt, QEvent, QObject
from PyQt6.QtGui import QFont
from ui import theme as T


def rgba(hexc: str, a: float) -> str:
    hexc = hexc.lstrip("#")
    r, g, b = int(hexc[0:2], 16), int(hexc[2:4], 16), int(hexc[4:6], 16)
    return f"rgba({r},{g},{b},{a})"


def card(accent: bool = False) -> QFrame:
    """A rounded panel. Access its layout via `.body`."""
    f = QFrame()
    f.setObjectName("card")
    border = T.ACCENT if accent else T.BORDER
    f.setStyleSheet(
        f"#card {{ background:{T.SURFACE}; border:1px solid {border}; border-radius:12px; }}")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(16, 13, 16, 14)
    lay.setSpacing(9)
    f.body = lay
    return f


def header(text: str, color: str | None = None) -> QLabel:
    lbl = QLabel(text.upper())
    font = QFont(); font.setBold(True); font.setPointSize(10)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.3)
    lbl.setFont(font)
    lbl.setStyleSheet(f"color:{color or T.ACCENT_HI}; background:transparent;")
    return lbl


def title(text: str, size: int = 15, color: str | None = None) -> QLabel:
    lbl = QLabel(str(text))
    font = QFont(); font.setBold(True); font.setPointSize(size)
    lbl.setFont(font)
    lbl.setStyleSheet(f"color:{color or T.TEXT}; background:transparent;")
    return lbl


def value(text: str, color: str | None = None, size: int = 13, bold: bool = True) -> QLabel:
    lbl = QLabel(str(text))
    font = QFont(); font.setBold(bold); font.setPointSize(size)
    lbl.setFont(font)
    lbl.setStyleSheet(f"color:{color or T.TEXT}; background:transparent;")
    return lbl


def muted(text: str, size: int = 14) -> QLabel:
    lbl = QLabel(str(text))
    lbl.setWordWrap(True)
    lbl.setStyleSheet(f"color:{T.MUTED}; font-size:{size}px; background:transparent;")
    return lbl


def chip(text: str, color: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color:{color}; background:{rgba(color,0.13)}; border:1px solid {rgba(color,0.42)}; "
        f"border-radius:9px; padding:2px 10px; font-size:12px; font-weight:600;")
    return lbl


def pill(text: str, color: str, width: int | None = None) -> QLabel:
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if width:
        lbl.setFixedWidth(width)
    lbl.setStyleSheet(
        f"color:{color}; background:{rgba(color,0.14)}; border:1px solid {rgba(color,0.45)}; "
        f"border-radius:8px; padding:2px 8px; font-size:12px; font-weight:700;")
    return lbl


def status_dot(color: str, text: str = "") -> QLabel:
    """A ● colored dot, optionally with trailing text."""
    lbl = QLabel(f"●  {text}" if text else "●")
    lbl.setStyleSheet(f"color:{color}; font-size:12px;")
    return lbl


def stat_tile(label: str, val: str, color: str | None = None) -> QFrame:
    """A small number-card: big value over a muted label."""
    f = QFrame()
    f.setObjectName("tile")
    f.setStyleSheet(
        f"#tile {{ background:{T.SURFACE_2}; border:1px solid {T.BORDER}; border-radius:10px; }}")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(12, 8, 12, 8)
    lay.setSpacing(1)
    lay.addWidget(value(val, color or T.TEXT, size=16))
    lay.addWidget(muted(label, size=11))
    return f


def enable_header_sort(table, on_sort):
    """Make column headers clickable; toggles asc/desc and calls
    on_sort(column:int, ascending:bool). Data-driven so embedded cell
    widgets stay aligned (unlike QTableWidget's built-in sort)."""
    header = table.horizontalHeader()
    header.setSectionsClickable(True)
    header.setSortIndicatorShown(True)
    state = {"col": -1, "asc": True}

    def clicked(col):
        state["asc"] = not state["asc"] if state["col"] == col else True
        state["col"] = col
        order = Qt.SortOrder.AscendingOrder if state["asc"] else Qt.SortOrder.DescendingOrder
        header.setSortIndicator(col, order)
        on_sort(col, state["asc"])

    header.sectionClicked.connect(clicked)


def hline() -> QFrame:
    f = QFrame()
    f.setFixedHeight(1)
    f.setStyleSheet(f"background:{T.BORDER}; border:none;")
    return f


def star_button(active: bool = False) -> QPushButton:
    """A toggleable star button. Toggle state with `.set_active(bool)`.

    Not `setCheckable` on purpose — the caller owns the truth (settings.json),
    the widget just reflects it, so we avoid Qt's internal state drifting.
    """
    btn = QPushButton("★")
    btn.setFixedSize(36, 36)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setToolTip("Toggle favorite")
    _style_star(btn, active)
    def _set_active(a: bool):
        _style_star(btn, a)
    btn.set_active = _set_active   # type: ignore[attr-defined]
    return btn


def _style_star(btn: QPushButton, active: bool):
    color = T.GOLD if active else T.MUTED
    hover = T.GOLD if active else T.ACCENT
    btn.setStyleSheet(
        f"QPushButton {{ background:transparent; color:{color}; border:1px solid {T.BORDER}; "
        f"border-radius:8px; font-size:18px; padding:0; }}"
        f"QPushButton:hover {{ color:{hover}; border-color:{hover}; }}")


def _cycle_completer_popup(completer, direction: int):
    """Move popup selection by `direction` (+1 = down, -1 = up), wrapping."""
    popup = completer.popup()
    model = popup.model()
    n = model.rowCount()
    if n == 0:
        return
    current = popup.currentIndex()
    row = current.row() if current.isValid() else (-1 if direction > 0 else 0)
    row = (row + direction) % n
    popup.setCurrentIndex(model.index(row, 0))


class SearchLineEdit(QLineEdit):
    """QLineEdit whose Tab / Shift+Tab cycle through the completer popup while
    it's visible. Falls back to normal focus navigation otherwise.

    Overriding `event()` (not `keyPressEvent`) is required because Qt handles
    Tab-for-focus inside `event()` before `keyPressEvent` is ever called.
    """
    def event(self, e):
        if e.type() == QEvent.Type.KeyPress:
            c = self.completer()
            if c is not None and c.popup().isVisible():
                key = e.key()
                if key == Qt.Key.Key_Tab:
                    _cycle_completer_popup(c, 1)
                    return True
                if key == Qt.Key.Key_Backtab:  # Shift+Tab
                    _cycle_completer_popup(c, -1)
                    return True
        return super().event(e)


class SearchComboBox(QComboBox):
    """Editable QComboBox whose Tab / Shift+Tab cycle through the completer
    popup. Same trick as SearchLineEdit but at the combo level so the internal
    line edit doesn't need to be replaced (replacing it disturbs the combo's
    rendering).
    """
    def event(self, e):
        if e.type() == QEvent.Type.KeyPress:
            c = self.completer()
            if c is not None and c.popup().isVisible():
                key = e.key()
                if key == Qt.Key.Key_Tab:
                    _cycle_completer_popup(c, 1)
                    return True
                if key == Qt.Key.Key_Backtab:
                    _cycle_completer_popup(c, -1)
                    return True
        return super().event(e)


class _TabCyclesCompleter(QObject):
    """Event filter for a QLineEdit (including a QComboBox's own line edit):
    while its completer popup is visible, Tab / Shift+Tab cycle the suggestions.

    Used where we can't swap in `SearchLineEdit` — e.g. a QComboBox owns its
    line edit and replacing it disturbs the combo's rendering.
    """
    def eventFilter(self, obj, e):
        if e.type() == QEvent.Type.KeyPress:
            get = getattr(obj, "completer", None)
            c = get() if get else None
            if c is not None and c.popup().isVisible():
                key = e.key()
                if key == Qt.Key.Key_Tab:
                    _cycle_completer_popup(c, 1)
                    return True
                if key == Qt.Key.Key_Backtab:  # Shift+Tab
                    _cycle_completer_popup(c, -1)
                    return True
        return False


def install_tab_cycles_completer(line_edit):
    """Attach Tab-cycling to a line edit without replacing it. The filter is
    parented to the line edit so it lives as long as the widget."""
    filt = _TabCyclesCompleter(line_edit)
    line_edit.installEventFilter(filt)
    return filt


def favorites_menu_button(get_favorites, on_pick) -> QPushButton:
    """A button that pops a menu of favorites, calls on_pick(name) when clicked.

    One QMenu is created and reused; its actions are cleared and repopulated
    just before it opens so the list always reflects the current saved set.
    """
    btn = QPushButton("Favorites ▾")
    btn.setFixedHeight(36)
    btn.setToolTip("Your saved favorites")
    menu = QMenu(btn)
    btn.setMenu(menu)
    def _rebuild():
        menu.clear()
        favs = get_favorites()
        if not favs:
            act = menu.addAction("(no favorites yet)")
            act.setEnabled(False)
        else:
            for name in favs:
                menu.addAction(name, lambda n=name: on_pick(n))
    _rebuild()
    # Both signals fire before the menu opens; either alone would work, but
    # connecting both guards against edge cases where Qt suppresses aboutToShow.
    menu.aboutToShow.connect(_rebuild)
    btn.pressed.connect(_rebuild)
    return btn
