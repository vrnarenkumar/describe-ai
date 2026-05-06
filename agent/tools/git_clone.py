"""
Git clone / fetch tool.

Provides a single function that clones a repository on first run and
fetches the latest commits on subsequent runs.
"""
from __future__ import annotations

import logging
from pathlib import Path

from git import GitCommandError, Repo

logger = logging.getLogger(__name__)


def clone_or_fetch(clone_url: str, clone_dir: Path) -> tuple[Repo, str]:
    """
    Ensure *clone_dir* contains an up-to-date copy of *clone_url*.

    - If the directory does not exist, the repository is cloned.
    - If it already exists, ``origin`` is fetched to pick up new commits.

    Args:
        clone_url: Authenticated HTTPS clone URL (token already embedded).
        clone_dir: Local destination directory.

    Returns:
        ``(repo, default_branch)`` — the GitPython Repo object and the name
        of the active branch at the time of clone / fetch.

    Raises:
        GitCommandError: If the git operation fails.
    """
    clone_dir.parent.mkdir(parents=True, exist_ok=True)

    if clone_dir.exists():
        logger.info("Repo already cloned at %s — fetching latest.", clone_dir)
        repo = Repo(clone_dir)
        repo.remotes.origin.fetch()
    else:
        logger.info("Cloning %s → %s", clone_url, clone_dir)
        repo = Repo.clone_from(clone_url, clone_dir)

    default_branch = repo.active_branch.name
    return repo, default_branch
