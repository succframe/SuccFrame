"""API health checks — every external endpoint SuccFrame depends on."""
import httpx

TIMEOUT = 12

# name, tab(s) it powers, url, optional headers
CHECKS = [
    {"name": "World State (warframestat.us)", "tab": "World State",
     "url": "https://api.warframestat.us/pc/fissures"},
    {"name": "Item Database (warframestat.us)", "tab": "Search Item",
     "url": "https://api.warframestat.us/items/search/boltor"},
    {"name": "Market — Item List", "tab": "Price Checker / Relic Planner",
     "url": "https://api.warframe.market/v2/items", "headers": {"Language": "en"}},
    {"name": "Market — Item Detail", "tab": "Price Checker",
     "url": "https://api.warframe.market/v2/item/mesa_prime_set", "headers": {"Language": "en"}},
    {"name": "Market — Orders", "tab": "Price Checker",
     "url": "https://api.warframe.market/v2/orders/item/mesa_prime_set", "headers": {"Platform": "pc"}},
    {"name": "Market — Riven Weapons", "tab": "Riven Mods",
     "url": "https://api.warframe.market/v2/riven/weapons", "headers": {"Language": "en"}},
    {"name": "Market — Riven Attributes", "tab": "Riven Mods",
     "url": "https://api.warframe.market/v2/riven/attributes", "headers": {"Language": "en"}},
    {"name": "Market — Riven Auctions", "tab": "Riven Mods",
     "url": "https://api.warframe.market/v1/auctions/search?type=riven&weapon_url_name=boltor",
     "headers": {"Platform": "pc"}},
    {"name": "Relic Drop Data (drops.warframestat.us)", "tab": "Relic Planner",
     "url": "https://drops.warframestat.us/data/relics.json", "range": True},
    {"name": "Riven Math Data (calamity-inc)", "tab": "Riven Mods",
     "url": "https://calamity-inc.github.io/warframe-riven-info/RivenParser.js"},
    {"name": "Market — Price History", "tab": "Price Checker",
     "url": "https://api.warframe.market/v1/items/mesa_prime_set/statistics",
     "headers": {"Platform": "pc", "Language": "en"}},
    {"name": "Item Images (market CDN)", "tab": "Price Checker / Relic Planner",
     "url": "https://warframe.market/static/assets/items/images/en/thumbs/"
            "mesa_prime_set.34d67af54de052f6de1d5ae64ed40197.128x128.png"},
    {"name": "Fallback Images (warframestat CDN)", "tab": "Relic Planner",
     "url": "https://cdn.warframestat.us/img/Forma.png"},
    {"name": "Overframe Sitemap (build IDs)", "tab": "Builds",
     "url": "https://overframe.gg/sitemap.xml",
     "headers": {"User-Agent": "Googlebot/2.1 (+http://www.google.com/bot.html)"},
     "range": True},
]


def check_one(entry: dict) -> tuple[bool, str]:
    """Return (ok, message). ok=True if the endpoint responds 200."""
    headers = dict(entry.get("headers", {}))
    headers.setdefault("User-Agent", "SuccFrame/1.0")
    if entry.get("range"):
        headers["Range"] = "bytes=0-1023"   # avoid downloading huge payloads
    try:
        r = httpx.get(entry["url"], headers=headers, timeout=TIMEOUT, follow_redirects=True)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
    if r.status_code in (200, 206):
        return True, f"Up ({r.status_code})"
    return False, f"HTTP {r.status_code}"
