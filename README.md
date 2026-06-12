# Keyhole SDK

The Keyhole SDK is a public, forkable starter repository for building applications that can participate in a governed Keyhole workflow.

This repository contains:

- Python SDK and CLI packages.
- Local governance declaration validation.
- Capability passport validation.
- Governed request submission helpers.
- Receipt models for responses returned by a configured governed server.
- A minimal starter app in `my-first-app`.

This repository is not the Keyhole server. It does not contain server-side governance authority, private infrastructure, event-spine persistence, production deployment details, or local run evidence.

## Install From A Fresh Clone

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

The editable install exposes both the `keyhole_sdk` Python package and the `keyhole` CLI.

## Configure A Governed Server

Local validation does not require a server. Live governed commands require a server URL and token supplied by your Keyhole operator:

```powershell
$env:KEYHOLE_MCP_URL = "https://your-keyhole-server.example.com"
$env:KEYHOLE_MCP_TOKEN = "replace_me"
```

Do not commit real tokens or local `.env` files.

When no governed server is configured, local commands still work and live governed commands fail closed with repair guidance.

## Common Commands

```powershell
keyhole doctor
keyhole validate
keyhole validate .\my-first-app
keyhole governed run --repo-dir .\my-first-app --no-live
```

Live governed flow:

```powershell
keyhole repo register --repo-dir .\my-first-app
keyhole context compile --repo-dir .\my-first-app
keyhole run --repo-dir .\my-first-app --context auto
keyhole governed status --repo-dir .\my-first-app
keyhole governed receipt --repo-dir .\my-first-app
```

## Python SDK

```python
from keyhole_sdk import KeyholeClient, KeyholeConfig

config = KeyholeConfig(
    base_url="https://your-keyhole-server.example.com",
    token="replace_me",
)

client = KeyholeClient.from_config(config)
```

The SDK is a client boundary. It submits requests to a configured server and parses responses. It does not decide canonical governance outcomes locally.

## `my-first-app`

`my-first-app` is the minimal public example. It shows where a developer edits app logic and how governance declarations are shaped.

Developer-owned files:

- `my-first-app/src/greet.py`
- `my-first-app/keyhole.yaml`
- `my-first-app/governance_contract.yaml`
- `my-first-app/capability_passport.yaml`
- `my-first-app/dependencies.yaml`
- `my-first-app/tests/`

Generated local state is ignored:

- `.keyhole/`
- `governed-runs/`
- `runs/`
- `proof_bundle/`
- `*.receipt.json`
- `*.proof.json`
- `*.evidence.json`
- `*.attestation.json`

Run the local walkthrough:

```powershell
keyhole validate .\my-first-app
pytest .\my-first-app\tests
keyhole governed run --repo-dir .\my-first-app --no-live
```

## Repository Layout

```text
packages/python/keyhole-sdk/   Python SDK source
packages/python/keyhole-cli/   Public CLI source
schemas/                       Public JSON schemas
my-first-app/                  Minimal starter app
tests/                         Public contract tests
docs/                          Public release and usage notes
```

## Contributing

Public contributions should keep the SDK boundary clear:

- Client code may validate local declarations and submit requests.
- Client code may normalize and display server receipts.
- Client code must fail safely when no server is configured.
- Client code must not embed private server names, personal paths, tokens, generated run receipts, or server-owned authority.

Run before opening a pull request:

```powershell
keyhole doctor
keyhole validate
keyhole validate .\my-first-app
pytest
```
