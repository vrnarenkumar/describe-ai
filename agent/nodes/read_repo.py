"""
Node 1 — read_repo

Clones (or refreshes) the repository and reads all non-excluded files.
Populates: repo_metadata, file_tree, file_contents.
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage

from ..config import cfg
from ..state import AgentState, RepoMetadata
from ..tools.git_clone import clone_or_fetch
from ..utils import build_file_tree, normalise_repo_url, read_repo_files

logger = logging.getLogger(__name__)


def read_repo(state: AgentState) -> dict[str, Any]:
    logger.info("Node: read_repo — %s", state["repo_url"])

    try:
        clone_url, owner, repo_name = normalise_repo_url(state["repo_url"])

        # Embed token for private-repo access
        if cfg.GITHUB_TOKEN:
            clone_url = clone_url.replace("https://", f"https://{cfg.GITHUB_TOKEN}@")

        clone_dir = cfg.CLONE_BASE_DIR / f"{owner}__{repo_name}"

        _, default_branch = clone_or_fetch(clone_url, clone_dir)
        target = state.get("target_branch") or default_branch

        metadata = RepoMetadata(
            owner=owner,
            name=repo_name,
            default_branch=default_branch,
            local_path=str(clone_dir),
        )
        file_tree = build_file_tree(clone_dir)
        file_contents = read_repo_files(clone_dir)

        return {
            "repo_metadata": metadata,
            "target_branch": target,
            "file_tree": file_tree,
            "file_contents": file_contents,
            "messages": [
                AIMessage(
                    content=(
                        f"Repository **{owner}/{repo_name}** cloned. "
                        f"Read {len(file_contents)} files."
                    )
                )
            ],
            "error": None,
        }

    except Exception as exc:
        logger.exception("read_repo failed")
        return {"error": str(exc), "messages": [AIMessage(content=f"read_repo error: {exc}")]}
