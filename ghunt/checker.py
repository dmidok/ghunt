"""Check if a GitHub username is available via the REST API."""

import os
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


GITHUB_API_BASE = "https://api.github.com"


def is_username_available(username: str, token: str | None = None) -> bool:
    """
    Check if a GitHub username is available.
    Returns True if available (404), False if taken (200) or on error.
    Token is required; no anonymous GitHub API usage.
    """
    if not token:
        raise ValueError("GitHub token required. Set GITHUB_TOKEN or pass token=.")
    url = f"{GITHUB_API_BASE}/users/{username}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {token}",
    }
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=10) as resp:
            return False  # 200 = user exists
    except HTTPError as e:
        if e.code == 404:
            return True
        if e.code == 403:
            raise RuntimeError("GitHub API rate limit exceeded. Set GITHUB_TOKEN for higher limits.")
        return False
    except URLError:
        return False


def get_token() -> str | None:
    """Get GitHub token from environment."""
    return os.environ.get("GITHUB_TOKEN")


def check_with_rate_limit(username: str, token: str | None = None, delay: float = 0.5) -> bool:
    """
    Check availability with a small delay. Token is required; no anonymous GitHub API usage.
    """
    if not token:
        raise ValueError("GitHub token required. Set GITHUB_TOKEN or pass token=.")
    result = is_username_available(username, token)
    time.sleep(delay)
    return result
