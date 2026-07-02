import os
import hashlib
import httpx
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QPixmap, QPainter

_CACHE_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SuccFrame", "cache"
)
TIMEOUT = 15


def _cache_path(url: str) -> str:
    key = hashlib.sha1(url.encode()).hexdigest()
    ext = os.path.splitext(url.split("?")[0])[1] or ".png"
    return os.path.join(_CACHE_DIR, key + ext)


def fetch_bytes(url: str) -> bytes | None:
    """Return image bytes, from disk cache if present, else download and cache."""
    path = _cache_path(url)
    if os.path.isfile(path):
        try:
            with open(path, "rb") as f:
                return f.read()
        except OSError:
            pass
    try:
        r = httpx.get(url, timeout=TIMEOUT, follow_redirects=True)
        r.raise_for_status()
        data = r.content
    except Exception:
        return None
    os.makedirs(_CACHE_DIR, exist_ok=True)
    try:
        with open(path, "wb") as f:
            f.write(data)
    except OSError:
        pass
    return data


def _pixmap(url: str) -> QPixmap | None:
    data = fetch_bytes(url)
    if not data:
        return None
    pix = QPixmap()
    return pix if pix.loadFromData(data) else None


def _composite(base: QPixmap, overlay: QPixmap, size: int = 160) -> QPixmap:
    """Overlay a small badge in the bottom-left corner, like warframe.market."""
    base = base.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
    ov = overlay.scaled(size * 42 // 100, size * 42 // 100,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)
    result = QPixmap(base.size())
    result.fill(Qt.GlobalColor.transparent)
    p = QPainter(result)
    p.drawPixmap(0, 0, base)
    p.drawPixmap(0, base.height() - ov.height(), ov)
    p.end()
    return result


class ImageLoader(QThread):
    """Loads one image (cached) and emits it as a QPixmap tagged with a key."""

    loaded = pyqtSignal(str, QPixmap)   # key, pixmap

    def __init__(self, key: str, url: str, overlay_url: str | None = None,
                 composite_size: int = 160):
        super().__init__()
        self.key = key
        self.url = url
        self.overlay_url = overlay_url
        self.composite_size = composite_size

    def run(self):
        pix = _pixmap(self.url)
        if pix is None:
            return
        if self.overlay_url:
            ov = _pixmap(self.overlay_url)
            if ov is not None:
                pix = _composite(pix, ov, self.composite_size)
        self.loaded.emit(self.key, pix)
