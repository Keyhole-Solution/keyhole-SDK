#!/usr/bin/env bash
# .devcontainer/setup.sh
# Post-create setup for the Keyhole Developer Kit devcontainer.
# Runs automatically after 'docker compose up' completes for the devcontainer
# service. Safe to re-run manually.
set -euo pipefail

WORKSPACE="/workspace"
cd "$WORKSPACE"

echo "────────────────────────────────────────────────────────────"
echo " Keyhole Developer Kit — devcontainer setup"
echo "────────────────────────────────────────────────────────────"

# ── Python virtual environment ────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
    echo "▸ Creating virtual environment (.venv)..."
    python3 -m venv .venv
fi

echo "▸ Installing SDK + CLI in editable mode..."
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -e packages/python/keyhole-sdk
.venv/bin/pip install --quiet -e packages/python/keyhole-cli

echo "▸ Installing dev / test tools..."
.venv/bin/pip install --quiet pytest pytest-cov ruff

# ── Environment file ──────────────────────────────────────────────────────────
if [ ! -f .env ]; then
    cp .env.example .env
    echo "▸ Copied .env.example → .env"
fi

# ── Verify ────────────────────────────────────────────────────────────────────
echo ""
echo "✅ Setup complete."
echo "   Test runtime : http://localhost:8080  (port-forwarded from test-runtime:8080)"
echo "   Internal URL : http://test-runtime:8080"
echo "   Verify       : keyhole doctor"
echo "   Run tests    : pytest tests/ -v"
echo "────────────────────────────────────────────────────────────"
