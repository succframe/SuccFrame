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
