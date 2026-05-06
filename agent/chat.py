"""
Chat conversation helpers for the Streamlit UI.

Houses stage constants, the LLM system prompt, and stateless helper
functions so that app.py contains only Streamlit rendering logic.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# ---------------------------------------------------------------------------
# Stage constants
# ---------------------------------------------------------------------------

S_CHAT        = "chat"          # LLM-driven conversation; collects repo + branch
S_RUNNING     = "running"       # Pipeline executing
S_AWAIT_PR    = "await_pr"      # Docs ready, awaiting PR decision
S_CREATING_PR = "creating_pr"   # Creating PR via GitHub API
S_DONE        = "done"
S_ERROR       = "error"

# ---------------------------------------------------------------------------
# Sidebar status labels (keyed by stage constant)
# ---------------------------------------------------------------------------

STAGE_LABELS: dict[str, str] = {
    S_CHAT:        "💬 Chatting with agent…",
    S_RUNNING:     "⚙️  Pipeline running…",
    S_AWAIT_PR:    "✅  Docs ready",
    S_CREATING_PR: "🔀  Creating PR…",
    S_DONE:        "🎉  Complete",
    S_ERROR:       "❌  Error",
}

# ---------------------------------------------------------------------------
# Default Streamlit session-state values
# ---------------------------------------------------------------------------

DEFAULT_SESSION_STATE: dict[str, Any] = {
    "messages":      [],
    "stage":         S_CHAT,
    "repo_url":      "",
    "target_branch": "",
    "repo_metadata":  None,
    "file_tree":      None,
    "file_contents":  None,
    "analysis":       None,
    "readme_content": None,
    "pr_url":         None,
    "error":          None,
    "_greeted":       False,
}

# ---------------------------------------------------------------------------
# LLM system prompt for the chat conversation
# ---------------------------------------------------------------------------

CHAT_SYSTEM = """\
You are a friendly, concise AI assistant called "Docs Agent".
Your job is to help users auto-generate documentation for their GitHub repositories.

Conversation flow:
1. Greet the user warmly (first message only). Briefly explain what you do:
   clone their GitHub repo, analyse the code with an LLM, write a README.md,
   and optionally open a Pull Request.
2. Ask for their GitHub repository URL (accept https:// or owner/repo shorthand).
3. Once they provide a valid-looking URL, ask which branch the PR should target.
   Offer "just use the default branch" as the easy option.
4. Once you have BOTH the repo URL AND the branch decision, emit this sentinel
   on its own line — nothing else on that line:
   PIPELINE_START:{"repo_url": "<url>", "branch": "<branch or empty string>"}

Rules:
- Keep every reply short and friendly.
- If the user goes off-topic, gently steer back.
- For branch: if they say "default", "skip", "none" or just press enter, use "".
- Never invent or guess a repo URL.
- After emitting PIPELINE_START, stop writing.
"""

# ---------------------------------------------------------------------------
# Stateless helpers
# ---------------------------------------------------------------------------


def sync_cfg() -> None:
    """Sync :data:`cfg` from current environment variables and bust the LLM cache."""
    from .config import cfg
    from .llm import get_llm

    cfg.MODEL_PROVIDER  = os.environ.get("MODEL_PROVIDER", "groq")
    cfg.GROQ_API_KEY    = os.environ.get("GROQ_API_KEY",   "")
    cfg.GROQ_MODEL      = os.environ.get("GROQ_MODEL",     "llama-3.3-70b-versatile")
    cfg.OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    cfg.OLLAMA_MODEL    = os.environ.get("OLLAMA_MODEL",   "llama3.2")
    cfg.GITHUB_TOKEN    = os.environ.get("GITHUB_TOKEN",   "")
    get_llm.cache_clear()


def call_llm(history: list[dict]) -> str:
    """Call the LLM with *history* and return the raw reply text."""
    sync_cfg()
    from .llm import get_llm

    lc_messages = [SystemMessage(content=CHAT_SYSTEM)]
    for msg in history:
        lc_messages.append(
            HumanMessage(content=msg["content"])
            if msg["role"] == "user"
            else AIMessage(content=msg["content"])
        )
    return get_llm().invoke(lc_messages).content.strip()


def extract_pipeline_trigger(text: str) -> dict | None:
    """Return the parsed JSON payload from a ``PIPELINE_START:`` sentinel, or ``None``."""
    match = re.search(r"PIPELINE_START:\s*(\{.*?\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None


def clean_display_text(text: str) -> str:
    """Strip the ``PIPELINE_START`` sentinel from text before displaying it."""
    return re.sub(r"\s*PIPELINE_START:\s*\{.*?\}", "", text, flags=re.DOTALL).strip()
