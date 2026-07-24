"""
Public demo API — analyse a GitHub repo and generate a README.

Wraps the existing LangGraph pipeline (read_repo -> analyze_content ->
write_docs) behind a streaming HTTP endpoint for the portfolio site.
Deliberately does NOT expose create_pr — this is a read-only public demo,
not a bot that can open pull requests on arbitrary repos.

Run with:
    uvicorn api:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
from typing import AsyncIterator, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from agent.config import cfg
from agent.nodes import analyze_content, read_repo, write_docs

logger = logging.getLogger(__name__)

GITHUB_REPO_RE = re.compile(r"^(https?://github\.com/)?[\w.-]+/[\w.-]+(\.git)?/?$")

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="describe-ai demo API")
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    lambda request, exc: JSONResponse(
        {"error": "Too many requests — please wait a minute and try again."}, status_code=429
    ),
)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://vrnarenkumar.github.io",
        "http://localhost:5183",
        "http://localhost:5173",
    ],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    repo_url: str = Field(..., max_length=200)
    target_branch: Optional[str] = None


def _event(**kwargs) -> str:
    return json.dumps(kwargs) + "\n"


async def _run_pipeline(repo_url: str, target_branch: Optional[str]) -> AsyncIterator[str]:
    repo_url = repo_url.strip()

    if not GITHUB_REPO_RE.match(repo_url):
        yield _event(
            type="error",
            message="Please provide a public GitHub repo URL, e.g. https://github.com/owner/repo",
        )
        return

    if not cfg.GROQ_API_KEY:
        yield _event(type="error", message="Demo server is misconfigured (missing GROQ_API_KEY).")
        return

    state = {
        "repo_url": repo_url,
        "target_branch": target_branch or "",
        "repo_metadata": None,
        "file_tree": None,
        "file_contents": None,
        "analysis": None,
        "readme_content": None,
        "pr_url": None,
        "messages": [],
        "error": None,
    }

    steps = [
        (1, "Cloning repository", ["GitPython", "PyGithub"], read_repo),
        (2, "Analysing codebase", ["LangGraph", "Groq — Llama 3.1"], analyze_content),
        (3, "Generating README.md", ["LangGraph", "Groq — Llama 3.1"], write_docs),
    ]

    try:
        for step_num, label, tech, fn in steps:
            yield _event(step=step_num, total=3, label=label, tech=tech, status="running")
            try:
                result = await asyncio.to_thread(fn, state)
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Step %d failed", step_num)
                yield _event(step=step_num, total=3, label=label, tech=tech, status="error", detail=str(exc))
                return

            state.update(result)

            if state.get("error"):
                yield _event(
                    step=step_num, total=3, label=label, tech=tech, status="error", detail=state["error"]
                )
                return

            detail = None
            if step_num == 1:
                detail = f"{len(state.get('file_contents') or [])} files read"
            elif step_num == 3:
                detail = f"{len(state.get('readme_content') or ''):,} chars generated"
            yield _event(step=step_num, total=3, label=label, tech=tech, status="done", detail=detail)

        metadata = state.get("repo_metadata") or {}
        yield _event(
            type="result",
            analysis=state.get("analysis"),
            readme=state.get("readme_content"),
            owner=metadata.get("owner"),
            name=metadata.get("name"),
        )
    finally:
        shutil.rmtree(cfg.CLONE_BASE_DIR, ignore_errors=True)


@app.post("/analyze")
@limiter.limit("5/minute")
async def analyze(request: Request, body: AnalyzeRequest):
    return StreamingResponse(
        _run_pipeline(body.repo_url, body.target_branch), media_type="application/x-ndjson"
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
