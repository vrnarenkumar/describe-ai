.ONESHELL:
SHELL        := /bin/zsh
.SHELLFLAGS  := -e -o pipefail -c

VENV         := .venv
STAMP        := $(VENV)/.deps_installed
REQUIREMENTS := requirements.txt
ENV_FILE     := .env
ENV_EXAMPLE  := .env.example

# Resolve best available Python: 3.12 → 3.13 → 3 (system)
PYTHON_BIN   := $(shell command -v python3.12 2>/dev/null \
                 || command -v python3.13 2>/dev/null \
                 || command -v python3 2>/dev/null)

# Call venv binaries directly — no activation needed
PIP          := $(VENV)/bin/pip
STREAMLIT    := $(VENV)/bin/streamlit

.PHONY: backend

backend: $(ENV_FILE)
	@if [ ! -d "$(VENV)" ]; then \
		echo "Virtual environment not found — creating with $(PYTHON_BIN)..."; \
		$(PYTHON_BIN) -m venv $(VENV); \
		echo "Virtual environment created at $(VENV)/"; \
	else \
		echo "Virtual environment found at $(VENV)/"; \
	fi
	@if [ ! -f "$(STAMP)" ] || [ "$(REQUIREMENTS)" -nt "$(STAMP)" ]; then \
		echo "Installing dependencies from $(REQUIREMENTS)..."; \
		$(PIP) install --quiet --upgrade pip; \
		$(PIP) install --quiet -r $(REQUIREMENTS); \
		touch $(STAMP); \
		echo "Dependencies ready."; \
	else \
		echo "Dependencies already up to date."; \
	fi
	@echo "Starting Documentation Agent..."
	@$(STREAMLIT) run app.py

# ── Copy .env.example → .env when .env is absent ─────────────────────────────
$(ENV_FILE):
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "No .env found — copying from $(ENV_EXAMPLE)..."; \
		cp $(ENV_EXAMPLE) $(ENV_FILE); \
		echo ""; \
		echo "  ACTION REQUIRED: Edit .env and fill in your credentials:"; \
		echo "    GROQ_API_KEY  — free key at https://console.groq.com"; \
		echo "    GITHUB_TOKEN  — needed to open pull requests"; \
		echo ""; \
		echo "Then re-run: make backend"; \
		exit 1; \
	fi
