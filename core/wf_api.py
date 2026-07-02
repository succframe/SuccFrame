import httpx

BASE = "https://api.warframestat.us/pc"
TIMEOUT = 20


def _get(endpoint: str):
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.get(f"{BASE}/{endpoint}", params={"language": "en"})
        r.raise_for_status()
        return r.json()


CYCLE_ENDPOINTS = (
    "earthCycle", "cetusCycle", "vallisCycle",
    "cambionCycle", "zarimanCycle", "duviriCycle",
)

_DICT_ENDPOINTS = {"voidTrader", "sortie", "nightwave", *CYCLE_ENDPOINTS}


def get_world_state() -> dict:
    endpoints = [
        "fissures", "alerts", "voidTrader", "nightwave",
        "invasions", "sortie", "dailyDeals", "syndicateMissions", "globalUpgrades",
        *CYCLE_ENDPOINTS,
    ]
    result = {}
    for ep in endpoints:
        try:
            result[ep] = _get(ep)
        except Exception:
            result[ep] = {} if ep in _DICT_ENDPOINTS else []
    return result
