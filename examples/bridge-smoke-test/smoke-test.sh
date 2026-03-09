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
assert data.get("governance_mode") in ("local-only", "governed", "misconfigured"), data
'''
GOV_MODE="$(python3 -c "import json,sys; print(json.loads(sys.argv[1]).get('governance_mode','unknown'))" "$IDENTITY")"
echo "governance_mode=$GOV_MODE"
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
assert "governance_verdict" in data, f"missing governance_verdict: {data}"
assert "version" in data, f"missing version: {data}"
assert "pointer" in data, f"missing pointer: {data}"
'''
echo "PASS: first realize"
echo

echo "== replay realize =="
REPLAY_REALIZE="$(request POST /realize "$PAYLOAD")"
echo "$REPLAY_REALIZE"
assert_json "$REPLAY_REALIZE" '''
assert data.get("digest") == digest, data
assert data.get("status") == "ALREADY_REALIZED", data
assert "governance_verdict" in data, f"missing governance_verdict: {data}"
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
echo "Bridge smoke test passed (governance_mode=$GOV_MODE)."
