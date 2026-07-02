import os
import json

_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "SuccFrame")
_PATH = os.path.join(_DIR, "settings.json")


def _load() -> dict:
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict):
    os.makedirs(_DIR, exist_ok=True)
    try:
        with open(_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass


def get_theme(default: str) -> str:
    return _load().get("theme", default)


def set_theme(name: str):
    data = _load()
    data["theme"] = name
    _save(data)


def get_remember_tab() -> bool:
    return bool(_load().get("remember_tab", False))


def set_remember_tab(value: bool):
    data = _load()
    data["remember_tab"] = bool(value)
    _save(data)


def get_last_tab() -> int:
    return int(_load().get("last_tab", 0))


def set_last_tab(index: int):
    data = _load()
    data["last_tab"] = int(index)
    _save(data)


# ── favorites ────────────────────────────────────────────────────────────
# 'kind' scopes favorites per tab, e.g. "search" and "price".

def get_favorites(kind: str) -> list[str]:
    return list(_load().get("favorites", {}).get(kind, []))


def add_favorite(kind: str, name: str):
    data = _load()
    favs = data.setdefault("favorites", {}).setdefault(kind, [])
    if name and name not in favs:
        favs.append(name)
        _save(data)


def remove_favorite(kind: str, name: str):
    data = _load()
    favs = data.get("favorites", {}).get(kind, [])
    if name in favs:
        favs.remove(name)
        _save(data)


def is_favorite(kind: str, name: str) -> bool:
    return name in _load().get("favorites", {}).get(kind, [])
