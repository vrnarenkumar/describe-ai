"""
File system and URL utilities for the documentation agent.

Provides helpers for language detection, exclusion filtering, directory tree
building, file reading, and repository URL normalisation.
"""
from __future__ import annotations

import fnmatch
from pathlib import Path

from .config import cfg
from .state import FileContent

# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

_LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".java": "java",
    ".kt": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".sh": "bash",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".md": "markdown",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".sql": "sql",
    ".tf": "terraform",
    ".dockerfile": "dockerfile",
}


def detect_language(path: str) -> str:
    """Return a lowercase language identifier for the given file path."""
    if Path(path).name.lower() == "dockerfile":
        return "dockerfile"
    return _LANGUAGE_MAP.get(Path(path).suffix.lower(), "unknown")


# ---------------------------------------------------------------------------
# Exclusion filtering
# ---------------------------------------------------------------------------


def is_excluded(rel_path: str) -> bool:
    """Return True if *rel_path* matches any configured exclusion glob."""
    for pattern in cfg.EXCLUDE_PATTERNS:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        # Also match against individual path components (e.g. "node_modules")
        for part in Path(rel_path).parts:
            if fnmatch.fnmatch(part, pattern.rstrip("/**")):
                return True
    return False


# ---------------------------------------------------------------------------
# Directory tree
# ---------------------------------------------------------------------------


def build_file_tree(root: Path) -> str:
    """Return a compact indented directory listing (like `tree`)."""
    lines: list[str] = []

    def _walk(directory: Path, prefix: str) -> None:
        try:
            entries = sorted(directory.iterdir(), key=lambda e: (e.is_file(), e.name))
        except PermissionError:
            return
        for i, entry in enumerate(entries):
            rel = entry.relative_to(root).as_posix()
            if is_excluded(rel):
                continue
            connector = "└── " if i == len(entries) - 1 else "├── "
            lines.append(f"{prefix}{connector}{entry.name}")
            if entry.is_dir():
                extension = "    " if i == len(entries) - 1 else "│   "
                _walk(entry, prefix + extension)

    lines.append(root.name + "/")
    _walk(root, "")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# File reading
# ---------------------------------------------------------------------------


def read_repo_files(root: Path) -> list[FileContent]:
    """Walk *root* and return file contents, respecting exclusion rules."""
    results: list[FileContent] = []
    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(root).as_posix()
        if is_excluded(rel):
            continue
        try:
            raw = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        truncated = len(raw) > cfg.MAX_FILE_CHARS
        results.append(
            FileContent(
                path=rel,
                content=raw[: cfg.MAX_FILE_CHARS],
                language=detect_language(rel),
                truncated=truncated,
            )
        )
    return results


# ---------------------------------------------------------------------------
# URL normalisation
# ---------------------------------------------------------------------------


def normalise_repo_url(repo_url: str) -> tuple[str, str, str]:
    """
    Return ``(https_clone_url, owner, repo_name)`` from various input formats:

    * ``https://github.com/owner/repo``
    * ``https://github.com/owner/repo.git``
    * ``owner/repo``
    """
    repo_url = repo_url.strip().rstrip("/")
    if repo_url.startswith("http"):
        clean = repo_url.removesuffix(".git")
        parts = clean.rstrip("/").split("/")
        owner, name = parts[-2], parts[-1]
        clone_url = f"https://github.com/{owner}/{name}.git"
    elif "/" in repo_url:
        owner, name = repo_url.split("/", 1)
        clone_url = f"https://github.com/{owner}/{name}.git"
    else:
        raise ValueError(f"Cannot parse repo URL: {repo_url!r}")
    return clone_url, owner, name
