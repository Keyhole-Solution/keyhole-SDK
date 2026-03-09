# Python Client Example

This example shows how to use the **Keyhole Python SDK** against the **Keyhole Test Runtime**.

It is intended as the simplest end-to-end example of a Python client interacting with the public runtime surface.

---

## What This Example Covers

This example demonstrates how to:

- connect to a running Keyhole Test Runtime,
- inspect runtime identity,
- inspect runtime-local state,
- submit a realization request,
- replay the same request and observe the runtime response.

This example uses the SDK exactly as it currently exists in this repository.

---

## Prerequisites

Before running this example, make sure you have:

- Python 3.10+ installed
- the repository cloned locally
- the Keyhole Test Runtime running on `http://localhost:8080`

---

## Start the Runtime

From the repository root:

```bash
docker compose up

You can verify the runtime manually:

curl http://localhost:8080/healthz
curl http://localhost:8080/identity
Install the SDK

From the repository root:

pip install -e packages/python/keyhole-sdk

This installs the SDK in editable mode for local development.

Example Code

Create a file such as example.py with the following contents:

from keyhole_sdk.client import RuntimeBridgeClient

client = RuntimeBridgeClient("http://localhost:8080")

print("== identity ==")
identity = client.identity()
print(identity)

print()
print("== initial state ==")
initial_state = client.state()
print(initial_state)

print()
print("== first realize ==")
first_receipt = client.realize(
    {
        "candidate_digest": "sha256:python-client-example",
        "payload": {
            "source": "python-client-example"
        }
    }
)
print(first_receipt)

print()
print("== replay realize ==")
replay_receipt = client.realize(
    {
        "candidate_digest": "sha256:python-client-example",
        "payload": {
            "source": "python-client-example"
        }
    }
)
print(replay_receipt)

print()
print("== final state ==")
final_state = client.state()
print(final_state)

Run it with:

python example.py
Expected Behavior

When the runtime is working correctly:

identity() returns the runtime identity and declared capabilities.

state() initially shows no realized digest for this example.

the first realize(...) call is accepted and mutates runtime-local state.

the second realize(...) call with the same digest should demonstrate replay-safe behavior.

the final state() call should show the realized digest in runtime state.

Manual Mapping to Runtime Endpoints

The current SDK client methods map to the runtime like this:

client.identity() → GET /identity

client.state() → GET /state

client.realize({...}) → POST /realize

If you want to inspect runtime health directly, use:

curl http://localhost:8080/healthz
Notes on Request Shape

The public runtime docs in this repository describe /realize using a candidate_digest and optional payload.

This example uses that same request shape so it stays aligned with the current public runtime contract.

Related Files

For more information, see:

packages/python/keyhole-sdk/README.md

packages/python/keyhole-sdk/keyhole_sdk/client.py

docs/test-runtime.md

examples/bridge-smoke-test/README.md

Why This Example Exists

The bridge smoke test shows the runtime contract with shell scripts.

This Python client example shows the same idea from the perspective of a Python developer using the SDK directly.

That makes it the simplest SDK-facing example in the repository.