import urllib.parse
import httpx

BASE = "https://api.warframestat.us"
IMG_BASE = "https://cdn.warframestat.us/img/"
TIMEOUT = 15


def search(query: str) -> list:
    """Search all Warframe items. Returns raw item dicts (exact matches first)."""
    q = urllib.parse.quote(query.strip())
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.get(f"{BASE}/items/search/{q}")
        r.raise_for_status()
        results = r.json()
    ql = query.strip().lower()
    results.sort(key=lambda it: (
        it.get("name", "").lower() != ql,          # exact name first
        not it.get("name", "").lower().startswith(ql),
        len(it.get("name", "")),
    ))
    return results


def image_url(item: dict) -> str | None:
    name = item.get("imageName")
    return IMG_BASE + name if name else None


def collect_drops(item: dict) -> list[dict]:
    """Flatten all drop sources for an item and its components.

    Returns [{part, location, chance, rarity}], sorted by chance desc.
    'part' is the component name, or '' for a direct item drop.
    """
    item_name = item.get("name", "")
    rows = []
    for dr in item.get("drops") or []:
        rows.append({
            "part": "",
            "full_name": dr.get("type") or item_name,
            "location": dr.get("location", ""),
            "chance": _pct(dr.get("chance")),
            "rarity": dr.get("rarity", ""),
        })
    for comp in item.get("components") or []:
        pname = comp.get("name", "")
        for dr in comp.get("drops") or []:
            rows.append({
                "part": pname,
                "full_name": dr.get("type") or f"{item_name} {pname}".strip(),
                "location": dr.get("location", ""),
                "chance": _pct(dr.get("chance")),
                "rarity": dr.get("rarity", ""),
            })
    rows.sort(key=lambda r: r["chance"], reverse=True)
    return rows


def _pct(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
