"""Generate short GitHub usernames using a local LLM (Ollama)."""

import re
from pathlib import Path
from typing import Iterator

from .checker import check_with_rate_limit, get_token

DEFAULT_EXCLUDE_FILE = "ghunt_checked.txt"


def _load_checked(path: str) -> set[str]:
    """Load already-checked usernames from file (one per line)."""
    p = Path(path)
    if not p.exists():
        return set()
    return {line.strip().lower() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()}


def _append_checked(path: str, username: str) -> None:
    """Append one username to the exclude file."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(username.strip().lower() + "\n")

def _normalize(username: str) -> str:
    """Lowercase and strip. GitHub usernames are case-insensitive for URLs."""
    return username.strip().lower()


def _is_valid_username(s: str, min_length: int = 4, max_length: int = 4) -> bool:
    """Check if string is a valid GitHub username within length range."""
    s = _normalize(s)
    if not (min_length <= len(s) <= min(max_length, 39)):
        return False
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", s):
        return False
    return True


def _extract_usernames(text: str, min_length: int = 4, max_length: int = 4) -> list[str]:
    """Extract valid usernames from LLM output."""
    seen: set[str] = set()
    result: list[str] = []
    # Match: alphanumeric sequences, optionally with single hyphens
    for match in re.finditer(r"\b([a-z0-9]+(?:-[a-z0-9]+)*)\b", text, re.IGNORECASE):
        cand = _normalize(match.group(1))
        if _is_valid_username(cand, min_length, max_length) and cand not in seen:
            seen.add(cand)
            result.append(cand)
    return result


def generate_from_llm(
    prompt: str,
    model: str = "llama3.2",
    min_length: int = 4,
    max_length: int = 4,
    limit: int = 50,
    count: int = 20,
    exclude: set[str] | None = None,
    host: str = "http://localhost:11434",
    client: "object | None" = None,
) -> Iterator[str]:
    """
    Ask a local LLM (Ollama) for short GitHub username suggestions.
    Yields valid usernames parsed from the response (min_length to max_length).
    Pass client= for testing (avoids ollama import).
    """
    if client is None:
        try:
            from ollama import Client as OllamaClient
            client = OllamaClient(host=host)
        except ImportError:
            raise ImportError("Install ollama: pip install ollama. Then run: ollama pull llama3.2") from None

    if min_length == max_length:
        length_constraint = f"- Exactly {max_length} characters per username."
    else:
        length_constraint = f"- Between {min_length} and {max_length} characters per username."
    user_lines = [
        f"Suggest {count} short GitHub usernames with these constraints:",
        length_constraint,
        f"- Your prompt: {prompt}",
        "- Rules: only lowercase letters, digits, and single hyphens. No spaces. Output ONLY the usernames, one per line. Nothing else.",
    ]
    if exclude:
        exclude_list = sorted(exclude)[:100]
        user_lines.append(f"- Do NOT suggest these (already checked): {', '.join(exclude_list)}")
        user_lines.append(f"- Suggest exactly {count} NEW usernames, none from the list above.")
    user_lines.append(f"Output exactly {count} usernames, one per line, nothing else.")
    user = "\n".join(user_lines)

    print("Prompt sent to LLM:", flush=True)
    print("  " + user.replace("\n", "\n  "), flush=True)
    print(flush=True)
    response = client.chat(
        model=model,
        messages=[{"role": "user", "content": user}],
    )
    content = response.message.content or ""
    for name in _extract_usernames(content, min_length, max_length):
        yield name


def find_available_from_llm(
    prompt: str,
    model: str = "llama3.2",
    min_length: int = 4,
    max_length: int = 4,
    limit: int = 50,
    token: str | None = None,
    exclude_file: str | None = None,
    host: str = "http://localhost:11434",
    client: "object | None" = None,
) -> list[str]:
    """
    Generate username suggestions from LLM, check GitHub availability, return available ones.
    Keeps asking the LLM (excluding already-checked names from exclude_file) until we have limit available.
    Pass client= for testing.
    """
    if not token:
        token = get_token()
    if not token:
        raise ValueError("GitHub token required. Set GITHUB_TOKEN or pass token=.")

    path = exclude_file or DEFAULT_EXCLUDE_FILE
    already_checked: set[str] = _load_checked(path)
    if already_checked:
        print(f"Loaded {len(already_checked)} already-checked usernames from {path}\n", flush=True)
    available: list[str] = []
    round_num = 0
    empty_rounds = 0
    max_empty_rounds = 5  # stop only after this many rounds in a row with no new candidates

    while len(available) < limit:
        round_num += 1
        print(f"--- Round {round_num} ---\n", flush=True)

        # 1. Ask LLM for suggestions, excluding already-checked
        candidates = list(
            generate_from_llm(
                prompt,
                model=model,
                min_length=min_length,
                max_length=max_length,
                limit=limit,
                count=limit,
                exclude=already_checked if already_checked else None,
                host=host,
                client=client,
            )
        )

        # 2. Filter out any we already checked (LLM might still return some)
        new_candidates = [c for c in candidates if c not in already_checked]
        if not new_candidates:
            empty_rounds += 1
            print("No new candidates from LLM.", flush=True)
            if empty_rounds >= max_empty_rounds:
                print(f"Stopping after {max_empty_rounds} rounds with no new suggestions.\n", flush=True)
                break
            print(f"Retrying ({empty_rounds}/{max_empty_rounds})...\n", flush=True)
            continue
        empty_rounds = 0  # reset when we get new candidates

        print("LLM output (candidates, after filtering already-checked):", flush=True)
        print("  " + ", ".join(new_candidates), flush=True)
        print(f"  ({len(new_candidates)} new)\n", flush=True)

        # 3. Check new candidates on GitHub until we have enough available
        for username in new_candidates:
            if len(available) >= limit:
                break
            already_checked.add(username)
            _append_checked(path, username)
            if check_with_rate_limit(username, token):
                available.append(username)
                print(f"  + {username} (available)", flush=True)
            else:
                print(f"  - {username} (taken)", flush=True)

        print(
            f"\nRound {round_num} stats: {len(already_checked)} total checked → {len(available)} available so far\n",
            flush=True,
        )

    print(
        f"Final: {len(available)} available (target {limit}), {len(already_checked)} total checked",
        flush=True,
    )
    return available
