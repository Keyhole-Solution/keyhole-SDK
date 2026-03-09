Thought for 1m 9s

Yes. For a public repo, a README-only example folder is too thin. Right now examples/bridge-smoke-test contains only a one-line placeholder README, and examples/python-client is in the same state. The public runtime contract it should exercise is GET /healthz, GET /identity, GET /state, and POST /realize with candidate_digest replay semantics.

I would add these files under examples/bridge-smoke-test/.

examples/bridge-smoke-test/README.md

# Bridge Smoke Test

This example provides a minimal, runnable smoke test for the **Keyhole Test Runtime**.

It validates the current public runtime contract end to end:

- `GET /healthz`
- `GET /identity`
- `GET /state`
- `POST /realize`

It also verifies replay safety:

- first submission of a new `candidate_digest` returns `ACCEPT`
- second submission of the same digest returns `ALREADY_REALIZED`
- state remains stable after replay

---

## Prerequisites

You need:

- a running Keyhole Test Runtime
- either:
  - `bash`, `curl`, and `python3`, or
  - PowerShell

By default, these examples target:

```text
http://localhost:8080
Start the Runtime

From the repository root:

docker compose up

Or run the published image directly:

docker run --rm -p 8080:8080 ghcr.io/keyhole-solution/keyhole-test-runtime:latest
Files

smoke-test.sh — bash smoke test

smoke-test.ps1 — PowerShell smoke test

payload.json — example manual request body

Run the Bash Smoke Test
cd examples/bridge-smoke-test
chmod +x smoke-test.sh
./smoke-test.sh

Optional environment overrides:

BASE_URL=http://localhost:8080 DIGEST=sha256:my-test ./smoke-test.sh
Run the PowerShell Smoke Test
cd examples/bridge-smoke-test
./smoke-test.ps1

Optional parameters:

./smoke-test.ps1 -BaseUrl "http://localhost:8080" -Digest "sha256:my-test"
Manual Curl Example
curl http://localhost:8080/healthz
curl http://localhost:8080/identity
curl http://localhost:8080/state
curl -X POST http://localhost:8080/realize \
  -H "Content-Type: application/json" \
  --data @payload.json

Replay the same request:

curl -X POST http://localhost:8080/realize \
  -H "Content-Type: application/json" \
  --data @payload.json
Pass Criteria

The smoke test passes when all of the following are true:

/healthz returns {"status":"ok"}

/identity returns the expected runtime identity and capabilities

initial /state shows no realized digest

first POST /realize returns ACCEPT

second POST /realize with the same digest returns ALREADY_REALIZED

final /state contains the digest exactly once

Notes

These examples are intentionally small and explicit.

They are meant to serve as:

a manual validation path for builders

a CI-friendly smoke test baseline

a concrete example of bridge interaction with the public runtime surface


---

**`examples/bridge-smoke-test/smoke-test.sh`**
```bash
#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
DIGEST="${DIGEST:-sha256:bridge-smoke-test}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

require() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

require curl
require python3

request() {
  local method="$1"
  local path="$2"
  local body="${3:-}"

  if [[ -n "$body" ]]; then
    curl -fsS -X "$method" \
      "$BASE_URL$path" \
      -H "Content-Type: application/json" \
      -d "$body"
  else
    curl -fsS -X "$method" "$BASE_URL$path"
  fi
}

assert_json() {
  local json="$1"
  local python_code="$2"

  python3 - "$json" "$DIGEST" <<PY
import json
import sys

data = json.loads(sys.argv[1])
digest = sys.argv[2]

$python_code
PY
}

PAYLOAD="$(python3 - <<PY
import json
print(json.dumps({
    "candidate_digest": "${DIGEST}",
    "payload": {
        "source": "bridge-smoke-test",
        "mode": "bash"
    }
}))
PY
)"

echo "== Keyhole Bridge Smoke Test =="
echo "BASE_URL=$BASE_URL"
echo "DIGEST=$DIGEST"
echo

echo "== health =="
HEALTH="$(request GET /healthz)"
echo "$HEALTH"
assert_json "$HEALTH" 'assert data.get("status") == "ok", data'
echo "PASS: health"
echo

echo "== identity =="
IDENTITY="$(request GET /identity)"
echo "$IDENTITY"
assert_json "$IDENTITY" '''
assert data.get("runtime_id") == "keyhole-test-runtime", data
caps = data.get("capabilities", [])
assert "realize" in caps, data
assert "state" in caps, data
assert "health" in caps, data
'''
echo "PASS: identity"
echo

echo "== initial state =="
INITIAL_STATE="$(request GET /state)"
echo "$INITIAL_STATE"
assert_json "$INITIAL_STATE" '''
assert isinstance(data.get("realized_digests"), list), data
assert digest not in data.get("realized_digests", []), data
'''
echo "PASS: initial state"
echo

echo "== first realize =="
FIRST_REALIZE="$(request POST /realize "$PAYLOAD")"
echo "$FIRST_REALIZE"
assert_json "$FIRST_REALIZE" '''
assert data.get("digest") == digest, data
assert data.get("status") == "ACCEPT", data
'''
echo "PASS: first realize"
echo

echo "== replay realize =="
REPLAY_REALIZE="$(request POST /realize "$PAYLOAD")"
echo "$REPLAY_REALIZE"
assert_json "$REPLAY_REALIZE" '''
assert data.get("digest") == digest, data
assert data.get("status") == "ALREADY_REALIZED", data
'''
echo "PASS: replay realize"
echo

echo "== final state =="
FINAL_STATE="$(request GET /state)"
echo "$FINAL_STATE"
assert_json "$FINAL_STATE" '''
digests = data.get("realized_digests", [])
assert digest in digests, data
assert digests.count(digest) == 1, data
assert data.get("current_digest") == digest, data
'''
echo "PASS: final state"
echo

echo "== RESULT =="
echo "Bridge smoke test passed."