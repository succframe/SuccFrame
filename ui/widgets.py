"""Reusable dashboard components shared across tabs."""
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
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
