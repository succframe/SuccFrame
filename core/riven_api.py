import re
import json
import httpx

MARKET = "https://api.warframe.market/v2"
AUCTIONS = "https://api.warframe.market/v1/auctions/search"
ASSET_BASE = "https://warframe.market/static/assets/"
RIVEN_PARSER_JS = "https://calamity-inc.github.io/warframe-riven-info/RivenParser.js"
TIMEOUT = 20

# From RivenParser.js (open-source). Index = number of buffs (or curses).
NUM_BUFFS_ATTEN = [0, 1, 0.66000003, 0.5, 0.40000001, 0.34999999]
NUM_BUFFS_CURSE_ATTEN = [0, 1, 0.33000001, 0.5, 1.25, 1.5]
_SPECIFIC_FIT = 1.5
_BASE_DRAIN = 10
_MAX_RANK = 8  # rank 8 -> (lvl+1) = 9

# v2 rivenType -> RivenParser.js base-value table key
TYPE_MAP = {
    "rifle": "LotusRifleRandomModRare",
    "shotgun": "LotusShotgunRandomModRare",
    "pistol": "LotusPistolRandomModRare",
    "melee": "PlayerMeleeWeaponRandomModRare",
    "zaw": "LotusModularMeleeRandomModRare",
    "kitgun": "LotusModularPistolRandomModRare",
    "archgun": "LotusArchgunRandomModRare",
}

_weapons = None
_attributes = None
_base_tags = None


def asset_url(path: str) -> str:
    return ASSET_BASE + path.lstrip("/")


# ── static data ──────────────────────────────────────────────────────────

def get_weapons() -> list:
    """[{name, slug, disposition, riven_type, group, mr, icon}] sorted by name."""
    global _weapons
    if _weapons is not None:
        return _weapons
    with httpx.Client(timeout=TIMEOUT, headers={"Language": "en"}) as c:
        r = c.get(f"{MARKET}/riven/weapons")
        r.raise_for_status()
        raw = r.json()["data"]
    out = []
    for w in raw:
        en = w.get("i18n", {}).get("en", {})
        out.append({
            "name": en.get("name", w.get("slug")),
            "slug": w.get("slug"),
            "disposition": w.get("disposition", 1.0),
            "riven_type": w.get("rivenType"),
            "group": w.get("group"),
            "mr": w.get("reqMasteryRank"),
            "icon": en.get("icon"),
        })
    out.sort(key=lambda x: x["name"])
    _weapons = out
    return out


def get_attributes() -> list:
    """[{slug, name, tag, unit, prefix, suffix}] for the 32 riven stats."""
    global _attributes
    if _attributes is not None:
        return _attributes
    with httpx.Client(timeout=TIMEOUT, headers={"Language": "en"}) as c:
        r = c.get(f"{MARKET}/riven/attributes")
        r.raise_for_status()
        raw = r.json()["data"]
    out = []
    for a in raw:
        en = a.get("i18n", {}).get("en", {})
        out.append({
            "slug": a.get("slug"),
            "name": en.get("name", a.get("slug")),
            "tag": a.get("gameRef"),
            "unit": a.get("unit"),          # "percent" or None
        })
    out.sort(key=lambda x: x["name"])
    _attributes = out
    return out


def _get_base_tags() -> dict:
    global _base_tags
    if _base_tags is not None:
        return _base_tags
    src = httpx.get(RIVEN_PARSER_JS, timeout=TIMEOUT).text
    i = src.find("const riven_tags = ")
    start = src.find("{", i)
    depth = 0
    end = start
    for j in range(start, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                end = j + 1
                break
    obj = re.sub(r",(\s*[}\]])", r"\1", src[start:end])  # strip trailing commas
    _base_tags = json.loads(obj)
    return _base_tags


def _base_value(riven_type: str, tag: str) -> float | None:
    key = TYPE_MAP.get(riven_type)
    if not key:
        return None
    for entry in _get_base_tags().get(key, []):
        if entry["tag"] == tag:
            return entry["value"]
    return None


# ── grading math (ported from RivenParser.js) ──────────────────────────────

def _display_factor(unit: str | None) -> float:
    return 100.0 if unit == "percent" else 1.0


def _center_buff(base, disposition, num_buffs, num_curses) -> float:
    atten = _SPECIFIC_FIT * disposition * _BASE_DRAIN
    curse_atten = 1.25 ** num_curses
    return base * atten * curse_atten * NUM_BUFFS_ATTEN[min(num_buffs, 5)] * (_MAX_RANK + 1)


def _center_curse(base, disposition, num_buffs, num_curses) -> float:
    atten = _SPECIFIC_FIT * disposition * _BASE_DRAIN
    return (base * atten * NUM_BUFFS_CURSE_ATTEN[min(num_buffs, 5)]
            * NUM_BUFFS_ATTEN[min(num_curses, 5)] * (_MAX_RANK + 1))


def grade(disposition, riven_type, tag, unit, value,
          num_buffs, num_curses, is_negative=False) -> dict | None:
    """Grade one stat. Returns {percentile, letter, low, high} in display units.

    percentile: 0..100 where the value sits in the possible [0.9c, 1.1c] band.
    For negatives, a smaller magnitude is better (percentile is inverted for grading).
    """
    base = _base_value(riven_type, tag)
    if base is None:
        return None
    factor = _display_factor(unit)
    if is_negative:
        center = abs(_center_curse(base, disposition, num_buffs, num_curses)) * factor
    else:
        center = _center_buff(base, disposition, num_buffs, num_curses) * factor
    low, high = center * 0.9, center * 1.1
    if high == low:
        return None
    frac = (abs(value) - low) / (high - low)
    frac = max(0.0, min(1.0, frac))
    quality = (1.0 - frac) if is_negative else frac  # small negative = good
    return {
        "percentile": round(quality * 100),
        "letter": _letter(quality),
        "low": round(low, 2),
        "high": round(high, 2),
    }


def _letter(q: float) -> str:
    if q >= 0.90:
        return "S"
    if q >= 0.66:
        return "A"
    if q >= 0.33:
        return "B"
    return "F"


# ── auctions (Module 3) ────────────────────────────────────────────────────

def search_auctions(weapon_slug: str) -> list:
    """Active riven auctions for a weapon, cheapest first."""
    params = {
        "type": "riven",
        "weapon_url_name": weapon_slug,
        "sort_by": "price_asc",
    }
    with httpx.Client(timeout=TIMEOUT, headers={"Platform": "pc", "Language": "en"}) as c:
        r = c.get(AUCTIONS, params=params)
        r.raise_for_status()
        return r.json().get("payload", {}).get("auctions", [])


def positive_popularity_by_slug(auctions: list) -> dict:
    """slug -> % of this weapon's riven listings carrying it as a POSITIVE."""
    total = 0
    counts: dict = {}
    for a in auctions:
        item = a.get("item", {})
        if item.get("type") != "riven":
            continue
        total += 1
        for at in item.get("attributes", []):
            if at.get("positive") and at.get("url_name"):
                counts[at["url_name"]] = counts.get(at["url_name"], 0) + 1
    if not total:
        return {}
    return {s: round(c / total * 100) for s, c in counts.items()}


def desirability_tier(pct: int) -> tuple[str, str]:
    """Classify a positive-popularity % into (label, color)."""
    if pct >= 35:
        return ("sought-after", "#10b981")
    if pct >= 12:
        return ("situational", "#f0b429")
    return ("rarely wanted", "#ef4444")


def combo_tier(user_pos: list[str], user_neg: str | None, pop_by_slug: dict) -> dict:
    """Rate the whole attribute combination against market demand.

    Returns {tier, hits, num_pos, neg_bad, top3} where top3 is the weapon's
    most-demanded positive attribute slugs.
    """
    top3 = [s for s, _ in sorted(pop_by_slug.items(), key=lambda kv: -kv[1])[:3]]
    np = len(user_pos)
    hits = sum(1 for s in user_pos if s in top3)
    sit = sum(1 for s in user_pos if s not in top3 and pop_by_slug.get(s, 0) >= 12)
    junk = np - hits - sit
    neg_bad = bool(user_neg) and pop_by_slug.get(user_neg, 0) >= 12

    if np == 0:
        tier = "Trash"
    elif hits == np and np >= 2 and not neg_bad:
        tier = "God Roll"
    elif hits == np and np >= 2:            # all meta but negative hurts
        tier = "Near God Roll"
    elif hits >= 2 and junk == 0:           # 2 meta + a situational
        tier = "Near God Roll"
    elif hits >= 2:
        tier = "Good"
    elif hits == 1 and junk == 0:
        tier = "Good"
    elif hits == 1:
        tier = "Mid"
    elif sit >= 1:
        tier = "Low"
    else:
        tier = "Trash"
    return {"tier": tier, "hits": hits, "num_pos": np, "neg_bad": neg_bad, "top3": top3}


def attribute_popularity(auctions: list, slug_to_name: dict) -> list[tuple[str, int]]:
    """% of this weapon's riven listings that carry each positive attribute."""
    by_slug = positive_popularity_by_slug(auctions)
    out = [(slug_to_name.get(s, s.replace("_", " ").title()), pct)
           for s, pct in by_slug.items()]
    out.sort(key=lambda x: -x[1])
    return out


def price_stats(auctions: list) -> dict | None:
    """Median (typical) and floor (base) buyout price from active listings."""
    prices = sorted(
        a["buyout_price"] for a in auctions
        if a.get("item", {}).get("type") == "riven" and a.get("buyout_price")
    )
    if not prices:
        return None
    n = len(prices)
    median = prices[n // 2] if n % 2 else (prices[n // 2 - 1] + prices[n // 2]) / 2
    floor = prices[min(n - 1, int(n * 0.05))]   # ~5th percentile = base/bad-roll price
    return {"median": round(median), "floor": round(floor), "min": prices[0], "count": n}


def similarity(user_pos: list[str], user_neg: str | None, auction_item: dict) -> int:
    """Jaccard overlap (%) between the user's attribute slugs and an auction's."""
    user = set(user_pos)
    if user_neg:
        user.add(user_neg)
    a_attrs = auction_item.get("attributes", [])
    auc = {at.get("url_name") for at in a_attrs if at.get("url_name")}
    if not user or not auc:
        return 0
    inter = len(user & auc)
    union = len(user | auc)
    return round(inter / union * 100) if union else 0


def recommend_price(combo_rating: dict, price_stats_data: dict, auctions: list,
                   user_pos: list[str], user_neg: str | None) -> dict | None:
    """Calculate recommended sell price based on combo rating and market listings.

    Returns {price, breakdown} where breakdown is a string explaining the calculation.
    """
    if not price_stats_data or not auctions:
        return None

    median = price_stats_data.get("median")
    if not median:
        return None

    # Combo tier multipliers (relative to median)
    tier_mult = {
        "God Roll": 1.35,
        "Near God Roll": 1.20,
        "Good": 1.08,
        "Mid": 0.95,
        "Low": 0.80,
        "Trash": 0.60,
    }

    tier = combo_rating.get("tier", "Mid")
    multiplier = tier_mult.get(tier, 1.0)

    # Get average price of very similar listings (70%+ similarity)
    similar_prices = []
    for a in auctions:
        item = a.get("item", {})
        if item.get("type") != "riven":
            continue
        price = a.get("buyout_price") or a.get("starting_price")
        if not price:
            continue
        sim = similarity(user_pos, user_neg, item)
        if sim >= 70:
            similar_prices.append(price)

    # Use similar listings average if available, otherwise use median
    if similar_prices:
        base = sum(similar_prices) / len(similar_prices)
        source = f"avg of {len(similar_prices)} very similar (70%+)"
    else:
        base = median
        source = "market median"

    recommended = round(base * multiplier)
    breakdown = f"{tier} combo ({multiplier:.0%} of {source} {int(base)}p) = {recommended}p"

    return {"price": recommended, "breakdown": breakdown}
