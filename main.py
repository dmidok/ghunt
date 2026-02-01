#!/usr/bin/env python3
"""CLI for finding available GitHub usernames via LLM suggestions (Ollama)."""

import argparse
import sys

from ghunt import find_available_from_llm, get_token


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find available GitHub usernames using LLM suggestions (Ollama)."
    )
    parser.add_argument(
        "--min-length",
        type=int,
        default=4,
        help="Minimum username length in characters (default: 4)",
    )
    parser.add_argument(
        "-l", "--max-length",
        type=int,
        default=4,
        help="Maximum username length in characters (default: 4)",
    )
    parser.add_argument(
        "-n", "--limit",
        type=int,
        default=50,
        help="Number of available usernames to find (default: 50)",
    )
    parser.add_argument(
        "-t", "--token",
        type=str,
        default=None,
        help="GitHub token (required; or set GITHUB_TOKEN)",
    )
    parser.add_argument(
        "-p", "--prompt",
        type=str,
        default="short, memorable, developer",
        help="Prompt for the LLM (e.g. 'short dev names', 'gaming')",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="llama3.2",
        help="Ollama model (default: llama3.2)",
    )
    parser.add_argument(
        "--ollama-host",
        type=str,
        default="http://localhost:11434",
        help="Ollama API host (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--exclude-file",
        type=str,
        default=None,
        help="File with already-checked usernames to exclude (default: ghunt_checked.txt)",
    )
    args = parser.parse_args()

    if args.min_length > args.max_length:
        print("Error: --min-length must not be greater than --max-length.", flush=True)
        sys.exit(1)

    token = args.token or get_token()
    if not token:
        print("Error: GitHub token required. Set GITHUB_TOKEN or use -t/--token.", flush=True)
        sys.exit(1)

    print(
        f"Finding available usernames for prompt '{args.prompt}' "
        f"(min-length={args.min_length}, max-length={args.max_length}, limit={args.limit})...\n",
        flush=True,
    )
    try:
        available = find_available_from_llm(
            prompt=args.prompt,
            model=args.model,
            min_length=args.min_length,
            max_length=args.max_length,
            limit=args.limit,
            token=token,
            exclude_file=args.exclude_file,
            host=args.ollama_host,
        )
    except ImportError as e:
        print(f"Error: {e}", flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", flush=True)
        print("Ensure Ollama is running (ollama serve) and the model is pulled (e.g. ollama pull llama3.2).", flush=True)
        sys.exit(1)

    if available:
        print(f"\nFound {len(available)} available: {', '.join(available)}", flush=True)
    else:
        print("\nNo available usernames found.", flush=True)
        print("Try a different prompt, adjust --min-length/--max-length, or run again (exclude file grows each run).", flush=True)


if __name__ == "__main__":
    main()
