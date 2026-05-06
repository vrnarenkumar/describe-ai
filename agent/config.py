"""
Runtime configuration loaded from environment variables / .env file.
"""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            "Copy .env.example → .env and fill in the values."
        )
    return value


class Config:
    # LLM — free providers only
    # Supported values: groq | ollama
    MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "groq").lower()
    # Groq — free Llama inference (https://console.groq.com)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")  # 30k TPM free tier
    # Ollama — local Llama (no API key required)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")

    # GitHub
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

    # Agent behaviour
    MAX_FILE_CHARS: int = int(os.getenv("MAX_FILE_CHARS", "1500"))
    EXCLUDE_PATTERNS: list[str] = [
        p.strip()
        for p in os.getenv(
            "EXCLUDE_PATTERNS",
            "*.lock,*.min.js,*.min.css,dist/**,build/**,node_modules/**,.git/**",
        ).split(",")
        if p.strip()
    ]

    # Temp directory used for repo clones
    CLONE_BASE_DIR: Path = Path(os.getenv("CLONE_BASE_DIR", "/tmp/doc_agent_repos"))

    def validate(self) -> None:
        """Raise if mandatory credentials are missing."""
        if self.MODEL_PROVIDER == "groq":
            if not self.GROQ_API_KEY:
                raise EnvironmentError(
                    "GROQ_API_KEY is not set. "
                    "Get a free key at https://console.groq.com and add it to your .env file."
                )
        elif self.MODEL_PROVIDER == "ollama":
            pass  # No API key required for local Ollama
        else:
            raise EnvironmentError(
                f"Unknown MODEL_PROVIDER '{self.MODEL_PROVIDER}'. "
                "Use 'groq' (free, recommended) or 'ollama' (local)."
            )

        if not self.GITHUB_TOKEN:
            raise EnvironmentError("GITHUB_TOKEN is required to create pull requests.")


cfg = Config()
