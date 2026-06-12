# Public Quickstart

This guide is for a fresh public clone.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

## Validate Locally

```powershell
keyhole doctor
keyhole validate
keyhole validate .\my-first-app
pytest
```

## Configure Live Governance

Live governed commands require a server URL and token supplied outside this repository:

```powershell
$env:KEYHOLE_MCP_URL = "https://your-keyhole-server.example.com"
$env:KEYHOLE_MCP_TOKEN = "replace_me"
```

Without these values, live governed commands must fail closed. That is expected.

## Run The Starter App Flow

```powershell
pytest .\my-first-app\tests
keyhole governed run --repo-dir .\my-first-app --no-live
```

When a governed server is configured:

```powershell
keyhole repo register --repo-dir .\my-first-app
keyhole context compile --repo-dir .\my-first-app
keyhole run --repo-dir .\my-first-app --context auto
keyhole governed receipt --repo-dir .\my-first-app
```
