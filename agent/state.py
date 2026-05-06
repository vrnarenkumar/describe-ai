"""
State schema for the documentation agent.

Each field is populated by a specific node in the LangGraph workflow:
  read_repo      → file_tree, file_contents, repo_metadata
  analyze_content → analysis
  write_docs     → readme_content
  create_pr      → pr_url
"""
from __future__ import annotations

import operator
from typing import Annotated, Optional

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class FileContent(TypedDict):
    """Represents a single file read from the repository."""
    path: str
    content: str
    language: str        # e.g. "python", "typescript", "unknown"
    truncated: bool      # True when file was larger than MAX_FILE_CHARS


class RepoMetadata(TypedDict):
    """Basic metadata extracted from the cloned repository."""
    owner: str           # GitHub owner (user or org)
    name: str            # Repository name
    default_branch: str  # e.g. "main" or "master"
    local_path: str      # Absolute path to local clone


class AgentState(TypedDict):
    # ── Input ─────────────────────────────────────────────────────────────────
    repo_url: str        # https://github.com/owner/repo  (or owner/repo)
    target_branch: str   # Branch to open the PR against (default: default branch)

    # ── Node outputs ──────────────────────────────────────────────────────────
    repo_metadata: Optional[RepoMetadata]
    file_tree: Optional[str]            # Formatted directory listing
    file_contents: Optional[list[FileContent]]

    analysis: Optional[str]             # Structured codebase analysis from LLM
    readme_content: Optional[str]       # Full generated README markdown

    pr_url: Optional[str]               # URL of the opened pull-request

    # ── Cross-cutting ─────────────────────────────────────────────────────────
    # Accumulated conversation / reasoning messages (reducer = list append)
    messages: Annotated[list[BaseMessage], operator.add]
    error: Optional[str]                # Non-empty when any node fails
