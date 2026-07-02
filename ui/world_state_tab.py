from datetime import datetime, timezone
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import core.wf_api as api
from ui import widgets as W
from ui import theme as T

TIER_COLOR = {
    "Lith": "#f0b429", "Meso": "#58a6ff", "Neo": "#10b981",
    "Axi": "#ef4444", "Requiem": "#a78bfa", "Omnia": "#f8c0f0",
}
TIER_ORDER = ["Lith", "Meso", "Neo", "Axi", "Requiem", "Omnia"]

# (endpoint, location label, {state: color}) for planetary cycle timers.
CYCLE_META = [
    ("earthCycle",   "Earth",                     {"day": T.GOLD, "night": T.BLUE}),
    ("cetusCycle",   "Cetus · Plains of Eidolon", {"day": T.GOLD, "night": T.VIOLET}),
    ("vallisCycle",  "Orb Vallis · Fortuna",      {"warm": T.RED, "cold": T.BLUE}),
    ("cambionCycle", "Cambion Drift · Deimos",    {"fass": T.RED, "vome": T.BLUE}),
    ("zarimanCycle", "Zariman",                   {"grineer": T.RED, "corpus": T.BLUE}),
    ("duviriCycle",  "Duviri",                    {"joy": T.GOLD, "anger": T.RED,
                                                   "envy": T.GREEN, "sorrow": T.BLUE,
                                                   "fear": T.VIOLET}),
]


def eta_from(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        target = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return ""
    secs = (target - datetime.now(timezone.utc)).total_seconds()
    if secs <= 0:
        return "now"
    d, rem = divmod(int(secs), 86400)
    h, rem = divmod(rem, 3600)
    m, _ = divmod(rem, 60)
    if d:
        return f"{d}d {h}h"
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


class FetchThread(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def run(self):
        try:
            self.done.emit(api.get_world_state())
        except Exception as e:
            self.error.emit(str(e))


class WorldStateTab(QWidget):
    def __init__(self):
        super().__init__()
        self._thread = None
        self._content = None
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        bar = QHBoxLayout()
        bar.addWidget(W.title("World State", 15))
        self._status = W.muted("Loading…")
        bar.addWidget(self._status)
        bar.addStretch()
        self._btn = QPushButton("Refresh")
        self._btn.setObjectName("primary")
        self._btn.setFixedWidth(100)
        self._btn.clicked.connect(self.refresh)
        bar.addWidget(self._btn)
        root.addLayout(bar)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        root.addWidget(self._scroll)

    def refresh(self):
        if self._thread and self._thread.isRunning():
            return
        self._btn.setEnabled(False)
        self._status.setText("Loading…")
        self._thread = FetchThread()
        self._thread.done.connect(self._populate)
        self._thread.error.connect(self._on_error)
        self._thread.start()

    def _on_error(self, msg):
        self._status.setText(f"Error: {msg}")
        self._btn.setEnabled(True)

    # ── layout ─────────────────────────────────────────────────────────────

    def _populate(self, data: dict):
        self._btn.setEnabled(True)
        self._status.setText("Live")

        content = QWidget()
        v = QVBoxLayout(content)
        v.setContentsMargins(0, 0, 12, 0)
        v.setSpacing(14)
        v.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Planetary cycle timers
        v.addWidget(self._cycles_panel(data))

        # Highlight tiles
        hl = QHBoxLayout()
        hl.setSpacing(12)
        for w in (self._baro_card(data.get("voidTrader", {})),
                  self._sortie_card(data.get("sortie", {})),
                  self._boosters_card(data.get("globalUpgrades", [])),
                  self._darvo_card(data.get("dailyDeals", []))):
            hl.addWidget(w, 1)
        v.addLayout(hl)

        # Two-column grid of panels
        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        fis = data.get("fissures", [])
        normal = [f for f in fis if not f.get("isHard")]
        steel = [f for f in fis if f.get("isHard")]
        top = Qt.AlignmentFlag.AlignTop
        grid.addWidget(self._fissure_panel("Void Fissures — Normal", normal), 0, 0, top)
        grid.addWidget(self._fissure_panel("Void Fissures — Steel Path", steel), 0, 1, top)
        grid.addWidget(self._invasions_panel(data.get("invasions", [])), 1, 0, top)
        grid.addWidget(self._syndicate_panel(data.get("syndicateMissions", [])), 1, 1, top)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        v.addLayout(grid)

        self._scroll.setWidget(content)
        self._content = content

    # ── cycle timers ───────────────────────────────────────────────────────

    def _cycles_panel(self, data):
        c = W.card(accent=True)
        c.body.addWidget(W.header("Timers & Events"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(9)
        r = 0
        for ep, label, colors in CYCLE_META:
            cyc = data.get(ep) or {}
            state = cyc.get("state")
            if not state:
                continue
            color = colors.get(state, T.MUTED)
            grid.addWidget(W.value(label, size=12), r, 0)
            grid.addWidget(W.pill(state.capitalize(), color, width=90), r, 1)
            grid.addWidget(W.muted(f"changes in {eta_from(cyc.get('expiry'))}"), r, 2,
                           Qt.AlignmentFlag.AlignRight)
            r += 1
        if r == 0:
            c.body.addWidget(W.muted("Cycle data unavailable."))
        else:
            grid.setColumnStretch(2, 1)
            grid.setColumnMinimumWidth(0, 210)
            c.body.addLayout(grid)
        return c

    # ── highlight cards ──────────────────────────────────────────────────

    def _baro_card(self, baro):
        c = W.card()
        c.body.addWidget(W.header("Baro Ki'Teer"))
        location = baro.get("location", "Unknown")
        now = datetime.now(timezone.utc)

        def _dt(iso):
            try:
                return datetime.fromisoformat(iso.replace("Z", "+00:00")) if iso else None
            except ValueError:
                return None

        act, exp = _dt(baro.get("activation")), _dt(baro.get("expiry"))
        present = act is not None and act <= now and (exp is None or now < exp)
        c.body.addWidget(W.title(location, 13))
        if present:
            n = len(baro.get("inventory", []) or [])
            c.body.addWidget(W.pill(f"⏱ leaves in {eta_from(baro.get('expiry'))}", T.RED))
            c.body.addWidget(W.muted(f"{n} items in stock"))
        else:
            c.body.addWidget(W.pill(f"⏳ arrives in {eta_from(baro.get('activation'))}", T.VIOLET))
        c.body.addStretch()
        return c

    def _sortie_card(self, sortie):
        c = W.card()
        c.body.addWidget(W.header("Daily Sortie"))
        if not sortie or sortie.get("expired", True):
            c.body.addWidget(W.muted("No active sortie."))
            c.body.addStretch()
            return c
        c.body.addWidget(W.title(sortie.get("faction", ""), 13, T.RED))
        for v in sortie.get("variants", []):
            c.body.addWidget(W.muted(f"• {v.get('missionType','')} — {v.get('modifier','')}"))
        c.body.addWidget(W.pill(f"⟳ {eta_from(sortie.get('expiry'))}", T.VIOLET))
        c.body.addStretch()
        return c

    def _boosters_card(self, upgrades):
        c = W.card()
        c.body.addWidget(W.header("Active Boosters"))
        active = [u for u in upgrades if not u.get("expired", True)]
        if not active:
            c.body.addWidget(W.muted("No global boosters active."))
        for u in active:
            desc = u.get("desc") or u.get("upgrade", "")
            c.body.addWidget(W.value(desc, T.GREEN, 12))
            c.body.addWidget(W.muted(f"ends {eta_from(u.get('expiry'))}"))
        c.body.addStretch()
        return c

    def _darvo_card(self, deals):
        c = W.card()
        c.body.addWidget(W.header("Darvo Daily Deal"))
        if not deals:
            c.body.addWidget(W.muted("No deal today."))
            c.body.addStretch()
            return c
        d = deals[0]
        c.body.addWidget(W.title(d.get("item", ""), 13))
        row = QHBoxLayout()
        row.addWidget(W.value(f"{d.get('salePrice','')}p", T.GREEN, 15))
        row.addWidget(W.muted(f"was {d.get('originalPrice','')}p  (-{d.get('discount','')}%)"))
        row.addStretch()
        c.body.addLayout(row)
        sold, total = d.get("sold", 0), d.get("total", 0)
        c.body.addWidget(W.muted(f"{sold}/{total} sold · ends {eta_from(d.get('expiry'))}"))
        c.body.addStretch()
        return c

    # ── grid panels ────────────────────────────────────────────────────────

    def _fissure_panel(self, heading, items):
        c = W.card()
        c.body.addWidget(W.header(heading))
        if not items:
            c.body.addWidget(W.muted("None active."))
            return c
        items.sort(key=lambda f: TIER_ORDER.index(f.get("tier", "Lith"))
                   if f.get("tier") in TIER_ORDER else 99)
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(7)
        for r, f in enumerate(items):
            tier = f.get("tier", "?")
            grid.addWidget(W.pill(tier, TIER_COLOR.get(tier, "#fff"), width=64), r, 0)
            grid.addWidget(W.value(f.get("missionType", ""), size=12), r, 1)
            grid.addWidget(W.muted(f.get("node", "")), r, 2)
            grid.addWidget(W.pill(eta_from(f.get("expiry")), T.RED), r, 3,
                           Qt.AlignmentFlag.AlignRight)
        grid.setColumnStretch(2, 1)
        c.body.addLayout(grid)
        return c

    def _invasions_panel(self, invasions):
        c = W.card()
        c.body.addWidget(W.header("Invasions"))
        active = [i for i in invasions if not i.get("completed", True)]
        if not active:
            c.body.addWidget(W.muted("No active invasions."))
            return c
        for inv in active[:8]:
            att = inv.get("attacker", {})
            dfn = inv.get("defender", {})
            c.body.addWidget(W.value(inv.get("node", ""), size=12))
            row = QHBoxLayout()
            row.addWidget(W.chip(self._reward_str(dfn.get("reward")), T.BLUE))
            vs = QLabel("vs")
            vs.setStyleSheet(f"color:{T.MUTED}; background:transparent; border:none;")
            row.addWidget(vs)
            row.addWidget(W.chip(self._reward_str(att.get("reward")), T.RED))
            row.addStretch()
            c.body.addLayout(row)
        return c

    @staticmethod
    def _reward_str(reward):
        if not reward:
            return "—"
        parts = []
        for ci in reward.get("countedItems", []):
            cnt = ci.get("count", 1)
            parts.append(f"{cnt}x {ci.get('type','')}" if cnt > 1 else ci.get("type", ""))
        parts += [it for it in reward.get("items", []) if it]
        if reward.get("credits"):
            parts.append(f"{reward['credits']:,} cr")
        return ", ".join(p for p in parts if p) or "—"

    def _syndicate_panel(self, missions):
        main = {"Steel Meridian", "Arbiters of Hexis", "Cephalon Suda",
                "Perrin Sequence", "Red Veil", "New Loka"}
        shown = [m for m in missions if m.get("syndicate") in main]
        c = W.card()
        c.body.addWidget(W.header("Syndicate Missions"))
        if not shown:
            c.body.addWidget(W.muted("No syndicate missions."))
            return c
        for s in shown:
            row = QHBoxLayout()
            row.addWidget(W.value(s.get("syndicate", ""), size=12))
            row.addStretch()
            row.addWidget(W.pill(f"⟳ {eta_from(s.get('expiry'))}", T.VIOLET))
            c.body.addLayout(row)
            nodes = s.get("nodes", []) or []
            if nodes:
                c.body.addWidget(W.muted(" · ".join(nodes)))
        return c
