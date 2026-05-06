"""
Node 4 — create_pr

Pushes the generated README to a dedicated branch and opens a GitHub PR.
Populates: pr_url.
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage

from ..config import cfg
from ..state import AgentState
from ..tools.github import push_readme_and_open_pr

logger = logging.getLogger(__name__)


def create_pr(state: AgentState) -> dict[str, Any]:
    logger.info("Node: create_pr")

    if state.get("error") or not state.get("readme_content"):
        return {}

    if not cfg.GITHUB_TOKEN or not cfg.GITHUB_TOKEN.strip():
        msg = (
            "GITHUB_TOKEN is not set. "
            "Add it to your .env file: GITHUB_TOKEN=ghp_... "
            "(create one at https://github.com/settings/tokens with 'repo' scope)"
        )
        logger.error(msg)
        return {"error": msg, "messages": [AIMessage(content=msg)]}

    metadata = state["repo_metadata"]
    base_branch = state.get("target_branch") or metadata["default_branch"]

    try:
        pr_url = push_readme_and_open_pr(
            owner=metadata["owner"],
            repo_name=metadata["name"],
            base_branch=base_branch,
            readme_content=state["readme_content"],
            token=cfg.GITHUB_TOKEN,
        )
        return {
            "pr_url": pr_url,
            "messages": [AIMessage(content=f"Pull request opened: {pr_url}")],
            "error": None,
        }

    except Exception as exc:
        msg = f"create_pr failed: {exc}"
        logger.exception(msg)
        return {"error": msg, "messages": [AIMessage(content=msg)]}
