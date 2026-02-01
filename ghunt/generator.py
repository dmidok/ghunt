"""Generate short GitHub usernames and find available ones."""

import itertools
from typing import Iterator

from .checker import check_with_rate_limit, get_token

# Valid chars: alphanumeric + hyphen (no hyphen at start/end for short names)
CHARS = "abcdefghijklmnopqrstuvwxyz0123456789"


def generate_short_usernames(max_length: int = 4) -> Iterator[str]:
    """
    Generate usernames from shortest to longest.
    Length 1: a-z, 0-9
    Length 2+: same, no leading/trailing hyphen, no consecutive hyphens.
    """
    for length in range(1, max_length + 1):
        for combo in itertools.product(CHARS, repeat=length):
            yield "".join(combo)


def find_shortest_available(
    max_length: int = 4,
    limit: int = 50,
    token: str | None = None,
) -> list[str]:
    """
    Find the shortest available GitHub usernames.
    Returns up to `limit` available usernames, sorted by length then alphabetically.
    """
    token = token or get_token()
    available: list[str] = []
    for username in generate_short_usernames(max_length):
        if len(available) >= limit:
            break
        if check_with_rate_limit(username, token):
            available.append(username)
            print(f"  + {username}", flush=True)
    return available
