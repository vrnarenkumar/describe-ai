#!/usr/bin/env python3
"""
Documentation Agent — entry point.

Usage:
  python main.py <repo_url> [--branch <branch>] [--verbose]

Examples:
  python main.py https://github.com/owner/my-repo
  python main.py owner/my-repo --branch develop
  python main.py owner/my-repo --verbose
"""
from __future__ import annotations

import argparse
import logging
import sys


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )
    # Suppress noisy third-party loggers unless verbose
    if not verbose:
        for noisy in ("httpx", "openai", "anthropic", "git"):
            logging.getLogger(noisy).setLevel(logging.WARNING)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auto-generate repository documentation and open a GitHub PR.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "repo_url",
        help="GitHub repository (https URL or owner/repo shorthand)",
    )
    parser.add_argument(
        "--branch",
        default="",
        metavar="BRANCH",
        help="Target branch for the PR (default: repo default branch)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    _configure_logging(args.verbose)

    # Import after logging is configured so module-level loggers pick it up
    from agent import run_agent

    print(f"\n Documentation Agent")
    print(f"{'─' * 50}")
    print(f"  Repository : {args.repo_url}")
    print(f"  PR target  : {args.branch or '(default branch)'}")
    print(f"{'─' * 50}\n")

    result = run_agent(repo_url=args.repo_url, target_branch=args.branch)

    print(f"\n{'─' * 50}")
    if result.get("error"):
        print(f"  FAILED: {result['error']}")
        return 1

    print(f"  Status     : Success")
    if result.get("pr_url"):
        print(f"  PR URL     : {result['pr_url']}")
    print(f"  README     : {len(result.get('readme_content', ''))} chars generated")
    print(f"{'─' * 50}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
