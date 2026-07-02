from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QCompleter, QFrame, QScrollArea, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
import core.riven_api as riven
from ui import widgets as W
from ui import theme as T

GRADE_COLOR = {"S": T.GOLD, "A": T.GREEN, "B": T.BLUE, "F": T.RED}

COMBO_COLOR = {
    "God Roll": T.GOLD, "Near God Roll": T.GREEN, "Good": T.BLUE,
    "Mid": T.MUTED, "Low": "#f97316", "Trash": T.RED,
}


class StaticLoader(QThread):
    done = pyqtSignal(list, list); error = pyqtSignal(str)
    def run(self):
        try:
            weapons = riven.get_weapons(); attrs = riven.get_attributes()
            riven._get_base_tags()
            self.done.emit(weapons, attrs)
        except Exception as e:
            self.error.emit(str(e))


class AuctionThread(QThread):
    done = pyqtSignal(list); error = pyqtSignal(str)
    def __init__(self, slug): super().__init__(); self.slug = slug
    def run(self):
        try: self.done.emit(riven.search_auctions(self.slug))
        except Exception as e: self.error.emit(str(e))


class RivenModsTab(QWidget):
    def __init__(self, _restore_state=None):
        super().__init__()
        self._weapon_by_name = {}
        self._attr_by_name = {}
        self._attr_slug_to_name = {}
        self._static_thread = self._auction_thread = None
        self._pending = None
        self._restore_state_pending = _restore_state
        self._build_ui()
        self._load_static()

    def _save_state(self) -> dict:
        """Save current inputs and results for state preservation across theme changes."""
        pos_data = []
        for combo, val in self._pos_rows:
            pos_data.append({"attr": combo.currentText(), "value": val.text()})
        neg_data = None
        if self._neg_row:
            neg_data = {"attr": self._neg_row[0].currentText(), "value": self._neg_row[1].text()}
        return {
            "weapon": self._weapon.currentText(),
            "positives": pos_data,
            "negative": neg_data,
            "pending": self._pending,
            "user_pos": getattr(self, "_user_pos", []),
            "user_neg": getattr(self, "_user_neg", None),
        }

    def _restore_state(self, state: dict):
        """Restore saved state after tab recreation."""
        # Restore weapon selection
        w_name = state.get("weapon", "")
        idx = self._weapon.findText(w_name)
        if idx >= 0:
            self._weapon.setCurrentIndex(idx)

        # Restore positive stats
        pos_data = state.get("positives", [])
        for i, data in enumerate(pos_data):
            if i < len(self._pos_rows):
                combo, val = self._pos_rows[i]
                idx = combo.findText(data.get("attr", ""))
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                val.setText(data.get("value", ""))

        # Restore negative stat
        neg_data = state.get("negative")
        if neg_data and self._neg_row:
            combo, val = self._neg_row
            idx = combo.findText(neg_data.get("attr", ""))
            if idx >= 0:
                combo.setCurrentIndex(idx)
            val.setText(neg_data.get("value", ""))

        # Trigger grade if there was a pending result
        if state.get("pending"):
            self._pending = state["pending"]
            self._user_pos = state.get("user_pos", [])
            self._user_neg = state.get("user_neg")
            if self._pending and self._user_pos:
                w = self._weapon_by_name.get(self._weapon.currentText())
                if w:
                    self._load_auctions(w["slug"])

    # ── UI ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(12)
        root.addWidget(W.title("Riven Mods — Grader & Price Scout", 15))
        self._status = W.muted("Loading riven data…")
        root.addWidget(self._status)

        cols = QHBoxLayout()
        cols.setSpacing(12)

        # Left input card
        inp = W.card()
        inp.setFixedWidth(340)
        inp.body.addWidget(W.header("Your Riven"))
        self._weapon = QComboBox()
        self._weapon.setEditable(True); self._weapon.setEnabled(False)
        self._weapon.currentIndexChanged.connect(self._on_weapon)
        inp.body.addWidget(self._weapon)
        self._dispo_chip = W.muted("")
        inp.body.addWidget(self._dispo_chip)

        inp.body.addWidget(W.header("Positive stats", T.GREEN))
        self._pos_rows = []
        for _ in range(3):
            row = QHBoxLayout()
            combo = QComboBox(); val = QLineEdit()
            val.setPlaceholderText("value"); val.setFixedWidth(80)
            row.addWidget(combo, 1); row.addWidget(val)
            inp.body.addLayout(row)
            self._pos_rows.append((combo, val))

        inp.body.addWidget(W.header("Negative stat", T.RED))
        nrow = QHBoxLayout()
        ncombo = QComboBox(); nval = QLineEdit()
        nval.setPlaceholderText("value"); nval.setFixedWidth(80)
        nrow.addWidget(ncombo, 1); nrow.addWidget(nval)
        inp.body.addLayout(nrow)
        self._neg_row = (ncombo, nval)

        self._grade_btn = QPushButton("Grade && Find Listings")
        self._grade_btn.setObjectName("primary")
        self._grade_btn.setEnabled(False)
        self._grade_btn.clicked.connect(self._on_grade)
        inp.body.addWidget(self._grade_btn)
        inp.body.addStretch()
        cols.addWidget(inp)

        # Right results scroll
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._results = QWidget()
        self._results_layout = QVBoxLayout(self._results)
        self._results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.setSpacing(10)
        self._scroll.setWidget(self._results)
        cols.addWidget(self._scroll, 1)

        root.addLayout(cols, 1)

    # ── static load ──────────────────────────────────────────────────────
    def _load_static(self):
        self._static_thread = StaticLoader()
        self._static_thread.done.connect(self._on_static)
        self._static_thread.error.connect(lambda m: self._status.setText(f"Load failed: {m}"))
        self._static_thread.start()

    def _on_static(self, weapons, attrs):
        self._weapon_by_name = {w["name"]: w for w in weapons}
        self._attr_by_name = {a["name"]: a for a in attrs}
        self._attr_slug_to_name = {a["slug"]: a["name"] for a in attrs}
        self._weapon.addItems([w["name"] for w in weapons])
        comp = QCompleter([w["name"] for w in weapons], self)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setFilterMode(Qt.MatchFlag.MatchContains)
        self._weapon.setCompleter(comp)
        self._weapon.setEnabled(True)
        names = [""] + [a["name"] for a in attrs]
        for combo, _ in self._pos_rows:
            combo.addItems(names)
        self._neg_row[0].addItems(names)
        self._grade_btn.setEnabled(True)
        self._status.setText("Select a weapon and enter your Riven's stats.")
        self._on_weapon()
        # Restore state if pending (after static data is loaded)
        if self._restore_state_pending:
            self._restore_state(self._restore_state_pending)
            self._restore_state_pending = None

    def _on_weapon(self):
        w = self._weapon_by_name.get(self._weapon.currentText())
        if w:
            self._dispo_chip.setText(f"Disposition {w['disposition']}  ·  {w['riven_type']}")

    # ── grading ──────────────────────────────────────────────────────────
    def _collect_inputs(self):
        positives = []
        for combo, val in self._pos_rows:
            n, v = combo.currentText().strip(), val.text().strip()
            if n and v:
                try: positives.append((self._attr_by_name[n], float(v)))
                except ValueError: pass
        neg = None
        n, v = self._neg_row[0].currentText().strip(), self._neg_row[1].text().strip()
        if n and v:
            try: neg = (self._attr_by_name[n], float(v))
            except ValueError: pass
        return positives, neg

    def _clear_results(self):
        while self._results_layout.count():
            it = self._results_layout.takeAt(0)
            if it.widget(): it.widget().deleteLater()
            elif it.layout(): self._clear_layout(it.layout())

    def _clear_layout(self, lay):
        while lay.count():
            it = lay.takeAt(0)
            if it.widget(): it.widget().deleteLater()
            elif it.layout(): self._clear_layout(it.layout())

    def _on_grade(self):
        w = self._weapon_by_name.get(self._weapon.currentText())
        if not w:
            self._status.setText("Pick a weapon first."); return
        positives, neg = self._collect_inputs()
        if not positives and not neg:
            self._status.setText("Enter at least one stat."); return
        self._clear_results()
        self._pending = {"w": w, "positives": positives, "neg": neg,
                         "num_buffs": len(positives), "num_curses": 1 if neg else 0}
        self._user_pos = [a["slug"] for a, _ in positives]
        self._user_neg = neg[0]["slug"] if neg else None
        self._status.setText("Analyzing roll quality and live market…")
        self._results_layout.addWidget(W.muted("Analyzing live market…"))
        self._load_auctions(w["slug"])

    def _render_full(self, auctions):
        self._clear_results()
        p = self._pending
        w, positives, neg = p["w"], p["positives"], p["neg"]
        nb, nc = p["num_buffs"], p["num_curses"]
        pop = riven.positive_popularity_by_slug(auctions)

        # Verdict banner
        desirable = sum(1 for a, _ in positives if pop.get(a["slug"], 0) >= 35)
        neg_harmless = (pop.get(neg[0]["slug"], 0) < 12) if neg else None
        verdict, vcolor = self._verdict(len(positives), desirable, neg, neg_harmless)
        banner = W.card(accent=True)
        banner.setStyleSheet(
            f"#card {{ background:{W.rgba(vcolor,0.10)}; border:1px solid {W.rgba(vcolor,0.5)}; border-radius:12px; }}")
        banner.body.addWidget(W.value(verdict, vcolor, 12))
        self._results_layout.addWidget(banner)

        # Stat gauges
        self._results_layout.addWidget(W.header("Stat Grades"))
        for attr, value in positives:
            g = riven.grade(w["disposition"], w["riven_type"], attr["tag"], attr["unit"],
                            value, nb, nc, is_negative=False)
            pct = pop.get(attr["slug"], 0)
            tier, tcolor = riven.desirability_tier(pct)
            self._results_layout.addWidget(
                self._grade_card(attr["name"], value, g, False, pct, tier, tcolor))
        if neg:
            attr, value = neg
            g = riven.grade(w["disposition"], w["riven_type"], attr["tag"], attr["unit"],
                            value, nb, nc, is_negative=True)
            pct = pop.get(attr["slug"], 0)
            tier = "harmless negative ✓" if neg_harmless else "hurts a wanted stat ✗"
            tcolor = T.GREEN if neg_harmless else T.RED
            self._results_layout.addWidget(
                self._grade_card(attr["name"], value, g, True, pct, tier, tcolor))

        # Price tiles
        self._results_layout.addWidget(W.header("Price Overview"))
        stats = riven.price_stats(auctions)
        tiles = QHBoxLayout(); tiles.setSpacing(10)
        if stats:
            tiles.addWidget(W.stat_tile("Typical (median)", f"{stats['median']}p", T.TEXT))
            tiles.addWidget(W.stat_tile("Base / floor", f"{stats['floor']}p", T.MUTED))
            tiles.addWidget(W.stat_tile("Cheapest", f"{stats['min']}p", T.GREEN))
            tiles.addWidget(W.stat_tile("Listings", str(stats["count"]), T.BLUE))
        else:
            tiles.addWidget(W.muted("No priced listings."))
        tiles.addStretch()
        self._results_layout.addLayout(tiles)

        # Attribute-combination rating (popularity-driven)
        self._results_layout.addWidget(W.header("Attribute Combo Rating"))
        rating = riven.combo_tier(self._user_pos, self._user_neg, pop)
        self._results_layout.addWidget(self._combo_card(rating))

        # Recommended price
        rec = riven.recommend_price(rating, stats, auctions, self._user_pos, self._user_neg)
        if rec:
            rec_card = W.card(accent=True)
            rec_card.setStyleSheet(
                f"#card {{ background:{W.rgba(T.GOLD,0.10)}; border:1px solid {W.rgba(T.GOLD,0.5)}; border-radius:12px; }}")
            top = QHBoxLayout()
            top.addWidget(W.header("Recommended Sell Price", T.GOLD))
            top.addStretch()
            price_lbl = W.value(f"{rec['price']}p", T.GOLD, 18)
            top.addWidget(price_lbl)
            rec_card.body.addLayout(top)
            rec_card.body.addWidget(W.muted(rec['breakdown'], 11))
            self._results_layout.addWidget(rec_card)

        # Popularity — ranked list with bars
        self._results_layout.addWidget(W.header("Attribute Popularity (live listings)"))
        popular = riven.attribute_popularity(auctions, self._attr_slug_to_name)[:12]
        pop_card = W.card()
        if not popular:
            pop_card.body.addWidget(W.muted("No data."))
        else:
            maxpct = max(pct for _, pct in popular) or 1
            grid = QGridLayout()
            grid.setHorizontalSpacing(14)
            grid.setVerticalSpacing(9)
            for i, (name, pct) in enumerate(popular):
                rank = QLabel(f"#{i+1}")
                rank.setStyleSheet(f"color:{T.MUTED}; font-weight:bold;")
                rank.setFixedWidth(30)
                color = T.GREEN if pct >= 35 else T.GOLD if pct >= 12 else T.MUTED
                bar = QProgressBar()
                bar.setRange(0, maxpct)
                bar.setValue(pct)
                bar.setTextVisible(False)
                bar.setFixedHeight(14)
                bar.setStyleSheet(
                    f"QProgressBar {{ background:{T.SURFACE_2}; border:1px solid {T.BORDER}; border-radius:7px; }}"
                    f"QProgressBar::chunk {{ border-radius:6px; background: qlineargradient("
                    f"x1:0,y1:0,x2:1,y2:0, stop:0 {W.rgba(color,0.45)}, stop:1 {color}); }}")
                grid.addWidget(rank, i, 0)
                grid.addWidget(W.value(name, size=12), i, 1)
                grid.addWidget(bar, i, 2)
                grid.addWidget(W.value(f"{pct}%", color, 12), i, 3,
                               Qt.AlignmentFlag.AlignRight)
            grid.setColumnStretch(2, 1)
            grid.setColumnMinimumWidth(1, 170)
            pop_card.body.addLayout(grid)
        self._results_layout.addWidget(pop_card)

        # Listings
        self._results_layout.addWidget(W.header("Similar Market Listings"))
        self._table = self._new_auction_table()
        self._results_layout.addWidget(self._table)
        self._fill_auction_table(auctions)
        self._status.setText(f"Graded {nb} positive / {nc} negative.")

    def _verdict(self, num_pos, desirable, neg, neg_harmless):
        if desirable == 0:
            return ("Rolls land on stats few players want — low market value.", T.RED)
        note = ("  Negative is harmless." if neg_harmless else "  Negative hurts a wanted stat.") if neg else ""
        if desirable >= 2:
            return (f"{desirable} sought-after stats — strong roll for this weapon.{note}", T.GREEN)
        return (f"1 sought-after stat — decent but not premium.{note}", T.GOLD)

    def _combo_card(self, r):
        color = COMBO_COLOR.get(r["tier"], T.MUTED)
        card = W.card()
        card.setStyleSheet(
            f"#card {{ background:{W.rgba(color,0.10)}; border:1px solid {W.rgba(color,0.5)}; border-radius:12px; }}")
        top = QHBoxLayout()
        badge = QLabel(r["tier"])
        badge.setStyleSheet(
            f"background:{color}; color:#0e121a; border-radius:9px; padding:4px 16px; "
            f"font-weight:bold; font-size:15px;")
        top.addWidget(badge)
        top.addStretch()
        top.addWidget(W.value(f"{r['hits']}/{r['num_pos']} top-demanded stats", color, 12))
        card.body.addLayout(top)

        if r["num_pos"]:
            if self._user_neg is None:
                neg_note = "no negative"
            else:
                neg_note = "negative hurts value" if r["neg_bad"] else "harmless negative"
            card.body.addWidget(W.muted(
                f"How desirable your attribute combination is for this weapon · {neg_note}"))
        top_names = [self._attr_slug_to_name.get(s, s) for s in r["top3"]]
        if top_names:
            card.body.addWidget(W.muted("Most wanted on this weapon: " + ", ".join(top_names)))
        return card

    def _grade_card(self, name, value, g, is_negative, pct, tier, tcolor):
        c = W.card()
        top = QHBoxLayout()
        sign = "" if str(value).startswith("-") else ("+" if not is_negative else "")
        top.addWidget(W.value(f"{sign}{value}  {name}", size=12))
        top.addWidget(W.chip(f"{tier} · {pct}%", tcolor))
        top.addStretch()
        if not g:
            top.addWidget(W.muted("no roll data"))
            c.body.addLayout(top)
            return c
        color = GRADE_COLOR.get(g["letter"], T.MUTED)
        top.addWidget(W.value(f"{g['percentile']}%", color, 12))
        badge = QLabel(g["letter"]); badge.setFixedWidth(30)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"background:{color}; border-radius:8px; color:#0e121a; font-weight:bold; padding:2px 0;")
        top.addWidget(badge)
        c.body.addLayout(top)

        gauge = QProgressBar()
        gauge.setRange(0, 100); gauge.setValue(g["percentile"]); gauge.setTextVisible(False)
        gauge.setFixedHeight(10)
        gauge.setStyleSheet(
            f"QProgressBar {{ background:{T.SURFACE_2}; border:1px solid {T.BORDER}; border-radius:5px; }}"
            f"QProgressBar::chunk {{ border-radius:4px; background: qlineargradient("
            f"x1:0,y1:0,x2:1,y2:0, stop:0 {W.rgba(color,0.4)}, stop:1 {color}); }}")
        c.body.addWidget(gauge)
        c.body.addWidget(W.muted(f"roll range for this config: {g['low']} – {g['high']}"))
        return c

    # ── auctions ─────────────────────────────────────────────────────────
    def _new_auction_table(self):
        t = QTableWidget()
        t.setColumnCount(6)
        t.setHorizontalHeaderLabels(["Match", "Price", "Rank", "Rerolls", "Seller", "Stats"])
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setAlternatingRowColors(True)
        t.verticalHeader().setVisible(False)
        h = t.horizontalHeader()
        for c in range(5):
            h.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        t.setMinimumHeight(320)
        return t

    def _load_auctions(self, slug):
        if self._auction_thread and self._auction_thread.isRunning():
            return
        self._auction_thread = AuctionThread(slug)
        self._auction_thread.done.connect(self._render_full)
        self._auction_thread.error.connect(lambda m: self._status.setText(f"Auction search failed: {m}"))
        self._auction_thread.start()

    def _fill_auction_table(self, auctions):
        rows = []
        for a in auctions:
            item = a.get("item", {})
            if item.get("type") != "riven":
                continue
            owner = a.get("owner", {})
            if owner.get("status") not in ("ingame", "online"):
                continue
            sim = riven.similarity(self._user_pos, self._user_neg, item)
            price = a.get("buyout_price") or a.get("starting_price") or 0
            rows.append((sim, price, item, owner))
        rows.sort(key=lambda r: (-r[0], r[1] if r[1] else 1e9))
        self._auction_rows = rows[:60]
        W.enable_header_sort(self._table, self._on_auction_sort)
        self._paint_auctions()

    def _on_auction_sort(self, col, asc):
        keys = {
            0: lambda r: r[0],
            1: lambda r: r[1] if r[1] else 1e9,
            2: lambda r: r[2].get("mod_rank", 0),
            3: lambda r: r[2].get("re_rolls", 0),
            4: lambda r: r[3].get("ingame_name", "").lower(),
        }
        keyfn = keys.get(col)
        if keyfn:
            self._auction_rows.sort(key=keyfn, reverse=not asc)
            self._paint_auctions()

    def _paint_auctions(self):
        rows = self._auction_rows
        self._table.setRowCount(len(rows))
        for i, (sim, price, item, owner) in enumerate(rows):
            sim_it = QTableWidgetItem(f"{sim}%")
            sim_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            sim_it.setForeground(QColor(T.GREEN if sim >= 75 else T.BLUE if sim >= 40 else T.MUTED))
            price_it = QTableWidgetItem(str(price) if price else "—")
            price_it.setForeground(QColor(T.TEXT))
            rank_it = QTableWidgetItem(f"{item.get('mod_rank', 0)}/8")
            rank_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            rr_it = QTableWidgetItem(str(item.get("re_rolls", 0)))
            rr_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            seller_it = QTableWidgetItem(owner.get("ingame_name", "?"))
            stats = "  ".join(
                ("+" if at.get("positive") else "−") + f"{at.get('value')} {at.get('url_name','').replace('_',' ')}"
                for at in item.get("attributes", []))
            self._table.setItem(i, 0, sim_it)
            self._table.setItem(i, 1, price_it)
            self._table.setItem(i, 2, rank_it)
            self._table.setItem(i, 3, rr_it)
            self._table.setItem(i, 4, seller_it)
            self._table.setItem(i, 5, QTableWidgetItem(stats))
