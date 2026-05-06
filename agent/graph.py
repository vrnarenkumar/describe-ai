"""
LangGraph workflow definition for the documentation agent.

Graph topology (linear pipeline with error short-circuit):

  [read_repo] → [analyze_content] → [write_docs] → [create_pr] → END

Each node's returned dict is merged into AgentState.
If any node sets state["error"], subsequent nodes skip their work gracefully.
"""
from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from .config import cfg
from .nodes import analyze_content, create_pr, read_repo, write_docs
from .state import AgentState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Conditional edge — abort the run on error
# ---------------------------------------------------------------------------


def _should_continue(state: AgentState) -> str:
    """Route to END immediately if any node reported an error."""
    if state.get("error"):
        logger.warning("Aborting pipeline due to error: %s", state["error"])
        return "abort"
    return "continue"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_graph() -> StateGraph:
    """Construct and compile the documentation agent graph."""
    cfg.validate()  # fail fast if credentials are missing

    builder = StateGraph(AgentState)

    builder.add_node("read_repo", read_repo)
    builder.add_node("analyze_content", analyze_content)
    builder.add_node("write_docs", write_docs)
    builder.add_node("create_pr", create_pr)

    builder.add_edge(START, "read_repo")
    builder.add_conditional_edges(
        "read_repo",
        _should_continue,
        {"continue": "analyze_content", "abort": END},
    )
    builder.add_conditional_edges(
        "analyze_content",
        _should_continue,
        {"continue": "write_docs", "abort": END},
    )
    builder.add_conditional_edges(
        "write_docs",
        _should_continue,
        {"continue": "create_pr", "abort": END},
    )
    builder.add_edge("create_pr", END)

    return builder.compile()


# ---------------------------------------------------------------------------
# Convenience runner
# ---------------------------------------------------------------------------


def run_agent(repo_url: str, target_branch: str = "") -> dict[str, Any]:
    """
    Execute the full documentation pipeline.

    Args:
        repo_url:      GitHub repository URL (https or owner/repo shorthand).
        target_branch: Branch to open the PR against. Defaults to the repo's
                       default branch if left empty.

    Returns:
        Final AgentState as a plain dict.
    """
    graph = build_graph()

    initial_state: AgentState = {
        "repo_url": repo_url,
        "target_branch": target_branch,
        "repo_metadata": None,
        "file_tree": None,
        "file_contents": None,
        "analysis": None,
        "readme_content": None,
        "pr_url": None,
        "messages": [],
        "error": None,
    }

    logger.info("Starting documentation agent for: %s", repo_url)
    final_state = graph.invoke(initial_state)

    if final_state.get("error"):
        logger.error("Agent finished with error: %s", final_state["error"])
    else:
        logger.info("Agent finished successfully. PR: %s", final_state.get("pr_url"))

    return final_state
