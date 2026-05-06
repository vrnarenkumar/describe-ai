"""
Node 2 — analyze_content

Sends the file tree and source files to the LLM and produces a structured
codebase analysis.
Populates: analysis.
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage

from ..llm import get_llm
from ..prompts import ANALYSIS_SYSTEM, CODE_PRIORITY, MAX_PROMPT_CHARS
from ..state import AgentState

logger = logging.getLogger(__name__)


def analyze_content(state: AgentState) -> dict[str, Any]:
    logger.info("Node: analyze_content")

    if state.get("error"):
        return {}  # skip if upstream failed

    llm = get_llm()
    tree_block = f"```\n{state['file_tree']}\n```"

    # Sort: source code first, then config, then docs/assets
    sorted_files = sorted(
        state["file_contents"] or [],
        key=lambda fc: CODE_PRIORITY.get(fc["language"], 5),
    )

    # Build file blocks up to MAX_PROMPT_CHARS
    file_blocks: list[str] = []
    used = 0
    skipped = 0
    for fc in sorted_files:
        header = f"### `{fc['path']}`" + (" *(truncated)*" if fc["truncated"] else "") + "\n"
        block  = f"{header}```{fc['language']}\n{fc['content']}\n```"
        if used + len(block) > MAX_PROMPT_CHARS:
            skipped += 1
            continue
        file_blocks.append(block)
        used += len(block)

    if skipped:
        logger.info("Skipped %d files to stay within prompt size limit.", skipped)
        file_blocks.append(
            f"_... {skipped} additional file(s) omitted to stay within context limits._"
        )

    files_section = (
        "\n\n".join(file_blocks) if file_blocks else "_No readable source files found._"
    )

    user_prompt = (
        f"## Repository: {state['repo_metadata']['owner']}/{state['repo_metadata']['name']}\n\n"
        f"### File Tree\n{tree_block}\n\n"
        f"### Source Files\n{files_section}\n\n"
        "Please produce the structured codebase analysis as described."
    )

    messages = [HumanMessage(content=ANALYSIS_SYSTEM + "\n\n" + user_prompt)]
    response = llm.invoke(messages)
    analysis = response.content

    logger.info("Analysis generated (%d chars).", len(analysis))

    return {
        "analysis": analysis,
        "messages": [HumanMessage(content="Analyze the repository."), response],
        "error": None,
    }
