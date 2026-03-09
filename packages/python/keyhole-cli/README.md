keyhole-cli

keyhole-cli is the command-line interface for interacting with the Keyhole Developer Kit and the Keyhole Test Runtime.

The CLI provides a simple way to:

inspect runtime identity

check runtime health

inspect runtime state

submit realization requests

validate integration behavior during development

It is primarily intended for local development, testing, and automation.

Installation

From the repository root:

pip install -e packages/python/keyhole-cli

This installs the CLI in editable mode.

To confirm installation:

keyhole --help
Quick Example

Start the test runtime:

docker compose up

Check runtime health:

keyhole runtime health

Inspect runtime identity:

keyhole runtime identity

Inspect runtime state:

keyhole runtime state

Submit a realization request:

keyhole runtime realize sha256:abc123

Replay the same digest:

keyhole runtime realize sha256:abc123

The runtime should return ALREADY_REALIZED.

Commands
keyhole runtime health

Checks runtime health.

Example:

keyhole runtime health

Equivalent to:

GET /healthz
keyhole runtime identity

Returns runtime identity and capabilities.

Example:

keyhole runtime identity

Equivalent to:

GET /identity
keyhole runtime state

Displays the current runtime state.

Example:

keyhole runtime state

Equivalent to:

GET /state
keyhole runtime realize

Submits a realization request using a candidate digest.

Example:

keyhole runtime realize sha256:abc123

Equivalent to:

POST /realize

Request body:

{
  "candidate_digest": "sha256:abc123",
  "payload": {}
}
Configuration

The CLI defaults to:

http://localhost:8080

You can override the runtime URL:

KEYHOLE_RUNTIME_URL=http://localhost:8080 keyhole runtime health

Future versions may support configuration files or profiles.

Relationship to the SDK

The CLI is built on top of the Keyhole Python SDK.

The SDK provides the programmatic interface used by the CLI.

See:

packages/python/keyhole-sdk
Intended Use

The CLI is designed for:

developer workflows

smoke testing integrations

CI validation

debugging runtime behavior

simple bridge validation

It is not intended to replace SDK integrations in production systems.

Related Documentation

For more information:

README.md — repository overview

docs/test-runtime.md — runtime behavior

docs/bridge-contract.md — integration model

examples/bridge-smoke-test — integration example