# Keyhole Developer Kit — Makefile
# Cross-platform: works on Linux, macOS, and Windows with Git Bash / WSL2.
# Windows-native (no Git Bash): run .\bootstrap.ps1 instead of 'make setup'.

# ── OS Detection ──────────────────────────────────────────────────────────────
ifeq ($(OS),Windows_NT)
    PYTHON   := python
    VENV_BIN := .venv/Scripts
else
    PYTHON   := python3
    VENV_BIN := .venv/bin
endif

.DEFAULT_GOAL := help
.PHONY: help setup bootstrap runtime-up runtime-down runtime-logs runtime-build \
        test test-unit test-smoke lint clean

# ── Help ──────────────────────────────────────────────────────────────────────
help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  Quick start : make setup && make runtime-up && make test"
	@echo "  Windows     : .\\bootstrap.ps1  (then docker compose up -d)"

# ── Environment Setup ─────────────────────────────────────────────────────────
setup: ## Create .venv, install SDK + CLI (editable), install dev tools
	$(PYTHON) -m venv .venv
	$(VENV_BIN)/pip install --upgrade pip
	$(VENV_BIN)/pip install -e packages/python/keyhole-sdk
	$(VENV_BIN)/pip install -e packages/python/keyhole-cli
	$(VENV_BIN)/pip install pytest pytest-cov ruff
	@test -f .env || (cp .env.example .env && echo "Copied .env.example → .env")
	@echo "✅ Setup complete.  Activate: source .venv/bin/activate"

bootstrap: ## Windows PowerShell bootstrap (same as .\bootstrap.ps1)
	powershell -ExecutionPolicy Bypass -File bootstrap.ps1

# ── Local Test Runtime ────────────────────────────────────────────────────────
runtime-up: ## Start the test runtime container (detached)
	docker compose up -d
	@echo "⏳ Waiting for health check (up to 10 s)..."
	@bash -c 'for i in 1 2 3 4 5; do \
	    curl -sf http://localhost:8080/healthz \
	      && echo "✅ Runtime ready → http://localhost:8080" && exit 0 \
	      || sleep 2; \
	  done; echo "⚠️  Not ready yet — run: make runtime-logs"'

runtime-down: ## Stop the test runtime container
	docker compose down

runtime-logs: ## Tail test runtime logs
	docker compose logs -f test-runtime

runtime-build: ## Rebuild the test runtime image (no cache)
	docker compose build --no-cache test-runtime

# ── Tests ─────────────────────────────────────────────────────────────────────
test: ## Run all tests
	$(VENV_BIN)/pytest tests/ -v

test-unit: ## Run unit tests only
	$(VENV_BIN)/pytest tests/unit/ -v

test-smoke: ## Run smoke tests (requires runtime + MCP_AVAILABLE=true)
	$(VENV_BIN)/pytest tests/smoke/ -v

# ── Code Quality ──────────────────────────────────────────────────────────────
lint: ## Run ruff linter across packages and tests
	$(VENV_BIN)/ruff check packages/ tests/

# ── Clean ─────────────────────────────────────────────────────────────────────
clean: ## Remove .venv, caches, and build artefacts
	rm -rf .venv __pycache__ .pytest_cache .ruff_cache
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
