"""
Node 3 — write_docs

Generates a full README.md from the structured codebase analysis.
Populates: readme_content.
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage

from ..llm import get_llm
from ..prompts import DOCS_SYSTEM
from ..state import AgentState

logger = logging.getLogger(__name__)


def write_docs(state: AgentState) -> dict[str, Any]:
    logger.info("Node: write_docs")

    if state.get("error") or not state.get("analysis"):
        return {}

    llm = get_llm()
    metadata = state["repo_metadata"]

    user_prompt = (
        f"Project: **{metadata['owner']}/{metadata['name']}**\n\n"
        f"## Codebase Analysis\n\n{state['analysis']}\n\n"
        "Now write the complete README.md following the template."
    )

    messages = [HumanMessage(content=DOCS_SYSTEM + "\n\n" + user_prompt)]
    response = llm.invoke(messages)
    readme = response.content.strip()

    # Strip accidental markdown code fences from the LLM output
    if readme.startswith("```markdown"):
        readme = readme[len("```markdown"):].lstrip()
    if readme.startswith("```"):
        readme = readme[3:].lstrip()
    if readme.endswith("```"):
        readme = readme[:-3].rstrip()

    logger.info("README generated (%d chars).", len(readme))

    return {
        "readme_content": readme,
        "messages": [HumanMessage(content="Write the README."), response],
        "error": None,
    }
