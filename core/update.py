"""App version and GitHub release update check."""
import httpx

__version__ = "1.1.0"

GITHUB_REPO = "succframe/SuccFrame"

RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"
_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
TIMEOUT = 10


def _parse_version(v: str) -> tuple:
    """'v1.2.3' or '1.2.3' -> (1, 2, 3). Non-numeric parts become 0."""
    v = v.strip().lstrip("vV")
    out = []
    for part in v.split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        out.append(int(digits) if digits else 0)
    return tuple(out)


def check_for_update() -> tuple[str, str | None, str]:
    """Compare the running version against the latest GitHub release.

    Returns (state, latest_version, url):
      state = 'current'  -> running the latest (or newer) version
      state = 'outdated' -> a newer release exists
      state = 'error'    -> couldn't reach GitHub / no releases yet
    """
    try:
        r = httpx.get(_API_URL, timeout=TIMEOUT, follow_redirects=True,
                      headers={"Accept": "application/vnd.github+json",
                               "User-Agent": f"SuccFrame/{__version__}"})
        r.raise_for_status()
        tag = r.json().get("tag_name", "")
    except Exception:
        return ("error", None, RELEASES_URL)
    if not tag:
        return ("error", None, RELEASES_URL)
    latest = tag.lstrip("vV")
    if _parse_version(tag) > _parse_version(__version__):
        return ("outdated", latest, RELEASES_URL)
    return ("current", latest, RELEASES_URL)
