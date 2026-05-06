"""
LLM prompt templates and GitHub PR content for the documentation agent.

All string constants used by the LangGraph nodes live here so that prompt
engineering changes never require touching node logic.
"""
from __future__ import annotations

import textwrap

# ---------------------------------------------------------------------------
# analyze_content node
# ---------------------------------------------------------------------------

ANALYSIS_SYSTEM = textwrap.dedent(
    """
    You are a senior software engineer performing a thorough codebase analysis.
    Given a repository's file tree and source files, produce a structured
    analysis that a technical writer can use to write great documentation.

    Your analysis MUST cover:
    1. **Purpose** – What does this project do? Who is it for?
    2. **Architecture** – High-level design, key modules / packages, data flow.
    3. **Tech Stack** – Languages, frameworks, libraries, infrastructure tools.
    4. **Entry Points** – How to start / invoke the project.
    5. **Configuration** – Environment variables, config files, feature flags.
    6. **Key APIs / Interfaces** – Public functions, REST endpoints, CLI commands.
    7. **Data Models** – Important classes, types, database schemas.
    8. **Testing** – Test frameworks, coverage indicators, how to run tests.
    9. **Deployment** – Docker, CI/CD, cloud, etc. if present.
    10. **Notable Patterns** – Design patterns, conventions, anything unusual.

    Be concise but complete. Use markdown headings.
    """
)

# Maximum total characters of file content sent to the LLM in one request.
# Groq free tier: llama3-8b-8192 ≈ 30k TPM, ~6k tokens budget for prompt.
# 20 000 chars ≈ 5 000 tokens — leaves headroom for system prompt + response.
MAX_PROMPT_CHARS: int = 20_000

# Code languages ranked by relevance for analysis (highest priority first).
CODE_PRIORITY: dict[str, int] = {
    "python": 0, "typescript": 0, "javascript": 0, "java": 0, "go": 0,
    "rust": 0, "kotlin": 0, "cpp": 0, "c": 0, "csharp": 0, "ruby": 0,
    "swift": 0, "php": 0,
    "bash": 1, "dockerfile": 1, "terraform": 1, "sql": 1,
    "yaml": 2, "toml": 2, "json": 2,
    "markdown": 3, "html": 3, "css": 3, "scss": 3,
    "unknown": 4,
}

# ---------------------------------------------------------------------------
# write_docs node
# ---------------------------------------------------------------------------

DOCS_SYSTEM = textwrap.dedent(
    """
    You are a technical writer creating a best-in-class README.md for an
    open-source project.

    Using the structured codebase analysis provided, write a comprehensive
    README that follows this template (include ALL sections, skip none):

    # <Project Name>

    > One-sentence tagline

    ## Table of Contents
    (auto-linked list of all sections)

    ## Overview
    Clear, friendly description of what the project does and why it exists.

    ## Features
    Bullet list of key features / capabilities.

    ## Architecture
    Explain the high-level design. Include a text diagram if helpful.

    ## Tech Stack
    Table: Layer | Technology | Purpose

    ## Prerequisites
    Minimum versions, OS requirements, accounts needed.

    ## Installation
    Step-by-step commands using code blocks.

    ## Configuration
    Table or list of every environment variable / config key with description
    and default value.

    ## Usage
    Practical examples — CLI commands, API calls, code snippets.

    ## API Reference
    (If applicable) Key endpoints / functions with parameters and return types.

    ## Running Tests
    How to execute the test suite.

    ## Deployment
    How to deploy (Docker, Kubernetes, cloud, etc.) if applicable.

    ## Contributing
    Branch naming, commit conventions, PR checklist.

    ## License
    License type and brief note.

    ---

    Rules:
    - Write in clear, simple English suitable for new contributors.
    - Use fenced code blocks with language tags.
    - Do NOT invent features not present in the analysis.
    - The output must be ONLY the markdown content — no extra commentary.
    """
)

# ---------------------------------------------------------------------------
# create_pr node
# ---------------------------------------------------------------------------

PR_BRANCH = "docs/auto-generated-readme"
COMMIT_MSG = "docs: add auto-generated README via documentation agent"
PR_TITLE = "docs: auto-generated README"
PR_BODY = textwrap.dedent(
    """\
    ## Summary
    This pull request adds a comprehensive `README.md` automatically generated
    by the **Documentation Agent** (LangGraph + LLM).

    ### What was analysed
    - Repository file tree
    - All non-excluded source files
    - Project structure, tech stack, entry points, configuration, and APIs

    ### Review checklist
    - [ ] Tagline and overview accurately describe the project
    - [ ] Installation steps are correct
    - [ ] All environment variables are listed
    - [ ] Usage examples are accurate
    - [ ] Any sensitive information has been removed

    > *Generated automatically — please review before merging.*
    """
)
