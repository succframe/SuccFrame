import httpx

BASE = "https://api.warframe.market/v2"
ASSET_BASE = "https://warframe.market/static/assets/"
HEADERS = {
    "accept": "application/json",
    "Platform": "pc",
    "Language": "en",
}
TIMEOUT = 15

_items_cache: list | None = None
_id_to_item: dict | None = None


def asset_url(path: str) -> str:
    return ASSET_BASE + path.lstrip("/")


def _client() -> httpx.Client:
    return httpx.Client(timeout=TIMEOUT, headers=HEADERS)


def get_all_items() -> list:
    """Full catalog normalized to [{name, slug}, ...]. Cached in-process."""
    global _items_cache
    if _items_cache is not None:
        return _items_cache
    with _client() as client:
        r = client.get(f"{BASE}/items")
        r.raise_for_status()
        raw = r.json()["data"]
    items = []
    for it in raw:
        en = it.get("i18n", {}).get("en", {})
        name = en.get("name")
        slug = it.get("slug")
        if name and slug:
            items.append({
                "name": name,
                "slug": slug,
                "id": it.get("id"),
                "thumb": en.get("thumb"),
                "icon": en.get("icon"),
                "subicon": en.get("subIcon"),
            })
    _items_cache = items
    return items


def _id_map() -> dict:
    """Map item id -> {name, slug, thumb}."""
    global _id_to_item
    if _id_to_item is None:
        _id_to_item = {it["id"]: it for it in get_all_items() if it.get("id")}
    return _id_to_item


def get_item_detail(slug: str) -> dict:
    """Item detail plus all set members for navigation.

    'members' is every item in the set (the set itself + parts), each as
    {name, slug, icon, subicon, is_set}, set listed first. Empty if not a set.
    """
    with _client() as client:
        r = client.get(f"{BASE}/item/{slug}")
        r.raise_for_status()
        d = r.json()["data"]
    en = d.get("i18n", {}).get("en", {})
    id_map = _id_map()

    members = []
    for pid in d.get("setParts", []):
        part = id_map.get(pid)
        if not part:
            continue
        members.append({
            "name": part["name"],
            "slug": part["slug"],
            "icon": part.get("icon"),
            "subicon": part.get("subicon"),
            "is_set": part["name"].endswith(" Set"),
        })
    members.sort(key=lambda m: (not m["is_set"], m["name"]))  # set first

    return {
        "name": en.get("name", slug),
        "slug": slug,
        "icon": en.get("icon"),
        "thumb": en.get("thumb"),
        "subicon": en.get("subIcon"),
        "ducats": d.get("ducats"),
        "trading_tax": d.get("tradingTax"),
        "mastery": d.get("reqMasteryRank"),
        "members": members,
    }


def get_orders(slug: str) -> list:
    """All active orders for an item (v2)."""
    with _client() as client:
        r = client.get(f"{BASE}/orders/item/{slug}")
        r.raise_for_status()
        return r.json()["data"]


_name_to_slug_ci: dict | None = None
_name_to_item_ci: dict | None = None


def images_for_name(name: str) -> tuple[str | None, str | None]:
    """Resolve a display name to (icon_url, subicon_url), or (None, None)."""
    global _name_to_item_ci
    if _name_to_item_ci is None:
        _name_to_item_ci = {it["name"].lower(): it for it in get_all_items()}
    n = name.lower()
    it = _name_to_item_ci.get(n)
    if it is None and n.endswith(" blueprint"):
        it = _name_to_item_ci.get(n[:-len(" blueprint")])
    if it is None:
        return (None, None)
    icon = asset_url(it["icon"]) if it.get("icon") else None
    sub = asset_url(it["subicon"]) if it.get("subicon") else None
    return (icon, sub)


def slug_for_name(name: str) -> str | None:
    """Resolve a display name to a market slug. Falls back to '<name> Set'."""
    global _name_to_slug_ci
    if _name_to_slug_ci is None:
        _name_to_slug_ci = {it["name"].lower(): it["slug"] for it in get_all_items()}
    n = name.lower()
    if n in _name_to_slug_ci:
        return _name_to_slug_ci[n]
    return _name_to_slug_ci.get(f"{n} set")


def price_summary(name: str) -> dict | None:
    """Lowest online sell price + top sellers for a name, or None if not listed."""
    slug = slug_for_name(name)
    if not slug:
        return None
    try:
        orders = get_orders(slug)
    except Exception:
        return None
    sells = [
        o for o in orders
        if o.get("type") == "sell"
        and o.get("user", {}).get("status") in ("ingame", "online")
    ]
    sells.sort(key=lambda o: o.get("platinum", 0))
    if not sells:
        return {"slug": slug, "lowest": None, "online": 0, "top": []}
    top = [
        (o.get("user", {}).get("ingameName", "?"),
         o.get("platinum", 0),
         o.get("user", {}).get("status", ""))
        for o in sells[:5]
    ]
    return {"slug": slug, "lowest": sells[0].get("platinum"), "online": len(sells), "top": top}
