import os
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from ui.main_window import MainWindow
from ui import theme
from core import settings

def _base_dir() -> str:
    """Project dir normally; the PyInstaller unpack dir when frozen into an exe."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


ASSETS = os.path.join(_base_dir(), "assets")


def _icon_path() -> str | None:
    for name in ("logo.ico", "logo.png"):
        p = os.path.join(ASSETS, name)
        if os.path.isfile(p):
            return p
    return None


def _set_taskbar_app_id():
    """Windows: make the taskbar use our icon, not python.exe's."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SuccFrame.App")
        except Exception:
            pass


def main():
    _set_taskbar_app_id()
    app = QApplication(sys.argv)
    app.setApplicationName("SuccFrame")
    theme.apply(app, settings.get_theme(theme.DEFAULT))

    icon_path = _icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    if icon_path:
        window.setWindowIcon(QIcon(icon_path))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
