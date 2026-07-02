import httpx
import core.market_api as market

RELICS_URL = "https://drops.warframestat.us/data/relics.json"
TIMEOUT = 30
TIER_ORDER = {"Lith": 0, "Meso": 1, "Neo": 2, "Axi": 3, "Requiem": 4}
STATES = ["Intact", "Exceptional", "Flawless", "Radiant"]

_relics_cache: dict | None = None
_name_to_slug: dict | None = None
_name_to_thumb: dict | None = None
_name_to_icon: dict | None = None
_name_to_subicon: dict | None = None


def get_relics() -> dict:
    """Return {display_name: {tier, name, states: {state: [rewards]}}}.

    display_name is e.g. 'Lith A1'. reward = {itemName, rarity, chance}.
    """
    global _relics_cache
    if _relics_cache is not None:
        return _relics_cache

    raw = httpx.get(RELICS_URL, timeout=TIMEOUT).json()["relics"]
    relics: dict = {}
    for entry in raw:
        tier = entry.get("tier")
        name = entry.get("relicName")
        state = entry.get("state")
        if not tier or not name or state not in STATES:
            continue
        display = f"{tier} {name}"
        rec = relics.setdefault(display, {"tier": tier, "name": name, "states": {}})
        rec["states"][state] = [
            {
                "itemName": rw.get("itemName", ""),
                "rarity": rw.get("rarity", ""),
                "chance": rw.get("chance", 0),
            }
            for rw in entry.get("rewards", [])
        ]
    _relics_cache = relics
    return relics


def relic_sort_key(display_name: str):
    tier, _, name = display_name.partition(" ")
    return (TIER_ORDER.get(tier, 99), name)


def _slug_for(item_name: str) -> str | None:
    global _name_to_slug
    if _name_to_slug is None:
        _name_to_slug = {it["name"].lower(): it["slug"] for it in market.get_all_items()}
    n = item_name.lower()
    if n in _name_to_slug:
        return _name_to_slug[n]
    if n.endswith(" blueprint"):
        stripped = n[:-len(" blueprint")]
        if stripped in _name_to_slug:
            return _name_to_slug[stripped]
    return None


def _build_image_maps():
    global _name_to_thumb, _name_to_icon, _name_to_subicon
    if _name_to_thumb is None:
        items = market.get_all_items()
        _name_to_thumb = {it["name"].lower(): it.get("thumb") for it in items}
        _name_to_icon = {it["name"].lower(): it.get("icon") for it in items}
        _name_to_subicon = {it["name"].lower(): it.get("subicon") for it in items}


def _lookup(mapping: dict, item_name: str):
    n = item_name.lower()
    if n in mapping:
        return mapping[n]
    if n.endswith(" blueprint"):
        return mapping.get(n[:-len(" blueprint")])
    return None


def reward_thumb_url(item_name: str) -> str | None:
    """Full warframe.market thumbnail URL for a reward item, or None."""
    _build_image_maps()
    thumb = _lookup(_name_to_thumb, item_name)
    return market.asset_url(thumb) if thumb else None


# Non-tradeable relic rewards aren't on warframe.market; use the game CDN.
_FALLBACK_ICONS = [
    ("forma", "https://cdn.warframestat.us/img/Forma.png"),
    ("kuva", "https://cdn.warframestat.us/img/Kuva.png"),
    ("exilus weapon adapter", "https://cdn.warframestat.us/img/UtilityWeaponModule.png"),
]


def reward_icon_url(item_name: str) -> str | None:
    """Full-resolution icon URL for a reward item (falls back to thumb, then CDN)."""
    _build_image_maps()
    icon = _lookup(_name_to_icon, item_name) or _lookup(_name_to_thumb, item_name)
    if icon:
        return market.asset_url(icon)
    low = item_name.lower()
    for key, url in _FALLBACK_ICONS:
        if key in low:
            return url
    return None


def reward_subicon_url(item_name: str) -> str | None:
    """Part-badge sub-icon URL (weapon/warframe part indicator), or None."""
    _build_image_maps()
    sub = _lookup(_name_to_subicon, item_name)
    return market.asset_url(sub) if sub else None


def lowest_sell_price(item_name: str) -> int | None:
    """Lowest platinum among online sellers for a reward item, or None."""
    slug = _slug_for(item_name)
    if not slug:
        return None
    try:
        orders = market.get_orders(slug)
    except Exception:
        return None
    prices = [
        o.get("platinum", 0)
        for o in orders
        if o.get("type") == "sell"
        and o.get("user", {}).get("status") in ("ingame", "online")
    ]
    return min(prices) if prices else None
