"""Custom drawn charts. Avoids pulling in QChart to keep the exe smaller."""
from PyQt6.QtWidgets import QWidget, QToolTip
from PyQt6.QtCore import Qt, QRectF, QPointF, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPolygonF
from ui import theme as T


class PriceHistoryChart(QWidget):
    """Daily average-price line + shaded min/max band + volume bars underneath.

    Hovering shows a vertical indicator at the nearest day and a tooltip with
    that day's date, avg/min/max prices, and trade volume.
    """

    # Layout padding (must match values used in _plot_bounds and paintEvent).
    _PAD_L = 40
    _PAD_R = 12
    _PAD_T = 14
    _PAD_B = 30
    _VOL_H = 34

    def __init__(self, parent=None):
        super().__init__(parent)
        self._points: list[dict] = []
        self._hover_idx: int | None = None
        self.setMinimumHeight(180)
        self.setMouseTracking(True)   # emits mouseMove without a click

    def set_points(self, points: list[dict]):
        self._points = list(points or [])
        self._hover_idx = None
        self.update()

    # ── hover ──────────────────────────────────────────────────────────────

    def _plot_bounds(self) -> tuple[int, int, int, int]:
        """Return (chart_l, chart_r, chart_top, chart_bot) in widget pixels."""
        w, h = self.width(), self.height()
        chart_l = self._PAD_L
        chart_r = w - self._PAD_R
        chart_top = self._PAD_T
        chart_bot = h - self._PAD_B - self._VOL_H
        return chart_l, chart_r, chart_top, chart_bot

    def _index_at(self, mx: int, my: int) -> int | None:
        """Which data point is closest to widget coord (mx, my)?"""
        if not self._points:
            return None
        chart_l, chart_r, chart_top, chart_bot = self._plot_bounds()
        # Allow hover across the whole chart+volume area, not just the line band.
        if mx < chart_l or mx > chart_r or my < chart_top or my > chart_bot + self._VOL_H + 8:
            return None
        n = len(self._points)
        if n <= 1:
            return 0
        frac = (mx - chart_l) / max(1, chart_r - chart_l)
        idx = round(frac * (n - 1))
        return max(0, min(n - 1, idx))

    def mouseMoveEvent(self, e):
        idx = self._index_at(e.position().x(), e.position().y())
        if idx != self._hover_idx:
            self._hover_idx = idx
            self.update()
        if idx is not None:
            d = self._points[idx]
            text = (
                f"<b>{d['date']}</b><br>"
                f"Avg: <b>{d['avg']:.1f}p</b><br>"
                f"Range: {d['min']:.0f}p – {d['max']:.0f}p<br>"
                f"Volume: {d['volume']:,}"
            )
            QToolTip.showText(e.globalPosition().toPoint() + QPoint(14, 14), text, self)
        else:
            QToolTip.hideText()

    def leaveEvent(self, _e):
        if self._hover_idx is not None:
            self._hover_idx = None
            self.update()
        QToolTip.hideText()

    # ── paint ──────────────────────────────────────────────────────────────

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(T.SURFACE))

        if not self._points:
            p.setPen(QColor(T.MUTED))
            f = QFont(); f.setPointSize(10); p.setFont(f)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "No price history available.")
            return

        chart_l, chart_r, chart_top, chart_bot = self._plot_bounds()

        pts = self._points
        n = len(pts)
        avgs = [d["avg"] for d in pts]
        mins = [d["min"] for d in pts]
        maxs = [d["max"] for d in pts]
        vols = [d["volume"] for d in pts]
        lo = min(mins); hi = max(maxs)
        if hi == lo:
            hi = lo + 1
        span = hi - lo
        vmax = max(vols) or 1

        def x(i):
            return chart_l + (chart_r - chart_l) * (i / max(1, n - 1))

        def y(v):
            return chart_bot - (chart_bot - chart_top) * (v - lo) / span

        # y-axis grid + labels (4 lines)
        p.setPen(QColor(T.BORDER))
        f = QFont(); f.setPointSize(9); p.setFont(f)
        for k in range(4):
            v = lo + span * (k / 3.0)
            yy = y(v)
            p.setPen(QPen(QColor(T.BORDER), 1, Qt.PenStyle.DotLine))
            p.drawLine(chart_l, int(yy), chart_r, int(yy))
            p.setPen(QColor(T.MUTED))
            p.drawText(QRectF(0, yy - 8, self._PAD_L - 6, 16),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       f"{v:.0f}p")

        # Min/max band (shaded)
        band_color = QColor(T.ACCENT); band_color.setAlpha(40)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(band_color)
        band = QPolygonF()
        for i, d in enumerate(pts):
            band.append(QPointF(x(i), y(d["max"])))
        for i in range(n - 1, -1, -1):
            band.append(QPointF(x(i), y(pts[i]["min"])))
        p.drawPolygon(band)

        # Volume bars
        bar_top = chart_bot + 8
        bar_bot = h - self._PAD_B + 4
        bar_h = bar_bot - bar_top
        step = (chart_r - chart_l) / max(1, n)
        bw = max(1.0, step * 0.7)
        vol_color = QColor(T.MUTED); vol_color.setAlpha(140)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(vol_color)
        for i, v in enumerate(vols):
            bh = bar_h * (v / vmax)
            cx = x(i) - bw / 2
            p.drawRect(QRectF(cx, bar_bot - bh, bw, bh))

        # Average line
        line_color = QColor(T.ACCENT_HI)
        p.setPen(QPen(line_color, 2))
        for i in range(n - 1):
            p.drawLine(QPointF(x(i), y(avgs[i])), QPointF(x(i + 1), y(avgs[i + 1])))

        # Endpoint dot
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(T.ACCENT))
        p.drawEllipse(QPointF(x(n - 1), y(avgs[-1])), 3.5, 3.5)

        # Hover indicator: vertical line across chart + volume area, dot at avg
        if self._hover_idx is not None and 0 <= self._hover_idx < n:
            hx = x(self._hover_idx)
            hover_pen = QPen(QColor(T.ACCENT_HI), 1, Qt.PenStyle.DashLine)
            p.setPen(hover_pen)
            p.drawLine(QPointF(hx, chart_top), QPointF(hx, bar_bot))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(T.ACCENT))
            p.drawEllipse(QPointF(hx, y(avgs[self._hover_idx])), 4.5, 4.5)

        # X-axis labels: first, middle, last date
        p.setPen(QColor(T.MUTED))
        for idx, align in ((0, Qt.AlignmentFlag.AlignLeft),
                           (n // 2, Qt.AlignmentFlag.AlignHCenter),
                           (n - 1, Qt.AlignmentFlag.AlignRight)):
            p.drawText(QRectF(x(idx) - 40, h - self._PAD_B + 14, 80, 14),
                       align | Qt.AlignmentFlag.AlignVCenter, pts[idx]["date"])
