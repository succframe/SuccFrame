"""Theming — multiple palettes, switchable at runtime."""

# Semantic colors (kept constant across themes for consistent meaning)
GREEN = "#10b981"
RED = "#ef4444"
GOLD = "#f0b429"
BLUE = "#58a6ff"
VIOLET = "#a78bfa"

DEFAULT = "Default Bright"

THEMES = {
    "Default Bright": dict(
        BG="#f3f5fa", SURFACE="#ffffff", SURFACE_2="#eceff5", BORDER="#d3dae6",
        ACCENT="#6366f1", ACCENT_HI="#818cf8", ACCENT_DK="#4f46e5",
        TEXT="#1c2230", MUTED="#5c6675", SWATCH="#ffffff"),
    "Dark Blue": dict(
        BG="#0e121a", SURFACE="#151b26", SURFACE_2="#1b2330", BORDER="#232c3b",
        ACCENT="#6366f1", ACCENT_HI="#818cf8", ACCENT_DK="#4f46e5",
        TEXT="#e8eef7", MUTED="#94a3b8"),
    "Dark Purple": dict(
        BG="#100c18", SURFACE="#191426", SURFACE_2="#231a33", BORDER="#322747",
        ACCENT="#a855f7", ACCENT_HI="#c084fc", ACCENT_DK="#7e22ce",
        TEXT="#efe8f7", MUTED="#a498b8"),
}

# Active palette globals (set by _set / apply). Defaults so imports work.
BG = SURFACE = SURFACE_2 = BORDER = ACCENT = ACCENT_HI = ACCENT_DK = TEXT = MUTED = ""


def _set(name: str):
    global BG, SURFACE, SURFACE_2, BORDER, ACCENT, ACCENT_HI, ACCENT_DK, TEXT, MUTED
    p = THEMES.get(name, THEMES[DEFAULT])
    BG, SURFACE, SURFACE_2, BORDER = p["BG"], p["SURFACE"], p["SURFACE_2"], p["BORDER"]
    ACCENT, ACCENT_HI, ACCENT_DK = p["ACCENT"], p["ACCENT_HI"], p["ACCENT_DK"]
    TEXT, MUTED = p["TEXT"], p["MUTED"]


_set(DEFAULT)


def build_qss() -> str:
    return f"""
* {{ font-family: "Inter", "Segoe UI", sans-serif; font-size: 13px; color: {TEXT}; outline: none; }}
QMainWindow, QWidget {{ background-color: {BG}; }}

QTabWidget::pane {{ border: none; background: {BG}; }}
QTabBar {{ qproperty-drawBase: 0; }}
QTabBar::tab {{ background: transparent; color: {MUTED}; padding: 10px 20px; margin-right: 4px;
    border: none; border-bottom: 2px solid transparent; font-weight: 600; font-size: 13px; }}
QTabBar::tab:hover {{ color: {TEXT}; }}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom: 2px solid {ACCENT};
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 transparent, stop:1 {_rgba(ACCENT, 0.10)}); }}

QPushButton {{ background-color: {SURFACE_2}; color: {TEXT}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 8px 15px; font-weight: 600; }}
QPushButton:hover {{ background-color: {SURFACE_2}; border-color: {ACCENT}; }}
QPushButton:pressed {{ background-color: {SURFACE}; }}
QPushButton:disabled {{ color: {MUTED}; background-color: {SURFACE}; border-color: {BORDER}; }}

QPushButton#primary {{ background-color: {ACCENT}; border: 1px solid {ACCENT_HI}; color: white; }}
QPushButton#primary:hover {{ background-color: {ACCENT_HI}; }}
QPushButton#primary:pressed {{ background-color: {ACCENT_DK}; }}
QPushButton#primary:disabled {{ background-color: {SURFACE_2}; color: {MUTED}; border-color: {BORDER}; }}

QLineEdit, QComboBox {{ background-color: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 8px 11px; selection-background-color: {ACCENT}; }}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background-color: {SURFACE}; border: 1px solid {BORDER};
    selection-background-color: {ACCENT}; color: {TEXT}; padding: 4px; outline: none; }}

QMenu {{ background-color: {SURFACE}; border: 1px solid {BORDER}; border-radius: 8px; padding: 4px; }}
QMenu::item {{ padding: 7px 22px; border-radius: 6px; color: {TEXT}; }}
QMenu::item:selected {{ background-color: {_rgba(ACCENT, 0.20)}; }}

QTableWidget {{ background-color: {SURFACE}; alternate-background-color: {SURFACE_2};
    border: 1px solid {BORDER}; border-radius: 10px; gridline-color: transparent;
    selection-background-color: {_rgba(ACCENT, 0.25)}; }}
QTableWidget::item {{ padding: 6px 8px; border: none; }}
QTableWidget::item:selected {{ background-color: {_rgba(ACCENT, 0.30)}; color: {TEXT}; }}
QHeaderView::section {{ background-color: {BG}; color: {MUTED}; padding: 9px 8px; border: none;
    border-bottom: 1px solid {BORDER}; font-weight: 700; font-size: 12px; }}
QTableCornerButton::section {{ background-color: {BG}; border: none; }}

QProgressBar {{ background-color: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: 6px;
    height: 12px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ border-radius: 5px; }}

QCheckBox {{ color: {TEXT}; spacing: 8px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {BORDER}; border-radius: 4px; background: {SURFACE}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}

QScrollBar:vertical {{ background: {SURFACE}; width: 12px; margin: 0; border-radius: 6px; }}
QScrollBar::handle:vertical {{ background: #556074; border-radius: 6px; min-height: 34px; border: 1px solid #667186; }}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; border-color: {ACCENT_HI}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ background: {SURFACE}; height: 12px; border-radius: 6px; }}
QScrollBar::handle:horizontal {{ background: #556074; border-radius: 6px; min-width: 34px; border: 1px solid #667186; }}
QScrollBar::handle:horizontal:hover {{ background: {ACCENT}; border-color: {ACCENT_HI}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

QToolTip {{ background-color: {SURFACE_2}; color: {TEXT}; border: 1px solid {ACCENT}; border-radius: 6px; padding: 5px 9px; }}
QToolButton {{ background: transparent; border: 1px solid {BORDER}; border-radius: 8px; padding: 5px; color: {MUTED}; }}
QToolButton:hover {{ border-color: {ACCENT}; color: {TEXT}; }}
"""


def _rgba(hexc: str, a: float) -> str:
    hexc = hexc.lstrip("#")
    r, g, b = int(hexc[0:2], 16), int(hexc[2:4], 16), int(hexc[4:6], 16)
    return f"rgba({r},{g},{b},{a})"


def apply(app, name: str):
    """Switch the active theme and restyle the whole application."""
    _set(name)
    app.setStyleSheet(build_qss())
