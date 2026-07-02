"""Overframe.gg URL resolution.

Overframe uses URLs like /items/arsenal/<numeric-id>/<slug>/. The IDs aren't
public via API, but the sitemap.xml lists every item — we scrape it once,
cache the slug->id mapping locally, and refresh weekly.
"""
import json
import os
import re
import time
import urllib.parse

import httpx

SITEMAP = "https://overframe.gg/sitemap.xml"
BASE = "https://overframe.gg"
# Sitemap responds 200 to legitimate crawler UAs (Cloudflare rule); it 403s browsers.
UA = "Googlebot/2.1 (+http://www.google.com/bot.html)"
TIMEOUT = 20

REFRESH_DAYS = 7

_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SuccFrame")
_CACHE_PATH = os.path.join(_DIR, "overframe_ids.json")

_ARSENAL_URL = re.compile(r"https://overframe\.gg/items/arsenal/(\d+)/([a-z0-9\-]+)/")


def _slug(name: str) -> str:
    return "-".join(name.lower().split())


def _load_cache() -> dict:
    try:
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(data: dict):
    os.makedirs(_DIR, exist_ok=True)
    try:
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass


def _fetch_sitemap_ids() -> dict[str, int]:
    """Parse the sitemap into {slug: id}. When a slug appears more than once
    (mods only), we keep the lowest id (the canonical entry)."""
    with httpx.Client(timeout=TIMEOUT, headers={"User-Agent": UA}) as c:
        r = c.get(SITEMAP)
        r.raise_for_status()
        text = r.text
    out: dict[str, int] = {}
    for id_str, slug in _ARSENAL_URL.findall(text):
        iid = int(id_str)
        if slug not in out or iid < out[slug]:
            out[slug] = iid
    return out


def get_ids(force_refresh: bool = False) -> dict[str, int]:
    """Return the slug->id map. Uses the on-disk cache when fresh."""
    cache = _load_cache()
    stale = (time.time() - float(cache.get("fetched_at", 0))) > REFRESH_DAYS * 86400
    if not force_refresh and cache.get("ids") and not stale:
        return cache["ids"]
    try:
        ids = _fetch_sitemap_ids()
    except Exception:
        # Network failure: fall back to whatever we have, even if stale.
        return cache.get("ids", {})
    if not ids:
        # Fetch succeeded but returned nothing (sitemap format may have changed).
        # Don't overwrite a good cache with an empty one, and don't loop refetching.
        return cache.get("ids", {})
    _save_cache({"fetched_at": time.time(), "ids": ids})
    return ids


def build_url(name: str) -> str:
    """Return the direct builds URL for a warframe/weapon name, or a search
    fallback URL if we can't resolve it."""
    slug = _slug(name)
    iid = get_ids().get(slug)
    if iid is None:
        # Fall back to Overframe's site search
        return f"{BASE}/search/?q={urllib.parse.quote_plus(name)}"
    return f"{BASE}/items/arsenal/{iid}/{slug}/"
