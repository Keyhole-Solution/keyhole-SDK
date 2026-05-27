"""Minimal probe: check gap state, then dispatch workspace.provision."""
import json, sys, time, urllib.error, urllib.request, uuid
from pathlib import Path

BASE = "https://mcp.keyholesolution.com"
GAP_ID = "gap_810669d1c41e2041"
REPO = "my-first-app"

creds = json.loads(Path.home().joinpath(".keyhole", "credentials.json").read_text())
token = creds["access_token"]
H = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}


def call(run_type, input_data=None, ctxpack_digest=None):
    rid = str(uuid.uuid4())
    payload = {"run_type": run_type, "repo": REPO}
    if ctxpack_digest:
        payload["ctxpack_digest"] = ctxpack_digest
    if input_data:
        payload["input"] = input_data
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE}/mcp/v1/runs/start", data=body,
        headers={**H, "X-Request-Id": rid, "X-Idempotency-Key": rid}
    )
    try:
        r = urllib.request.urlopen(req, timeout=15)
        raw = json.loads(r.read())
        sys.stdout.write(f"  FULL RESPONSE: {json.dumps(raw)[:600]}\n"); sys.stdout.flush()
        return raw
    except urllib.error.HTTPError as e:
        rb = e.read().decode()
        sys.stdout.write(f"HTTP {e.code}: {rb[:400]}\n")
        sys.stdout.flush()
        return None


def poll(run_id, label=""):
    url = f"{BASE}/mcp/v1/runs/{run_id}"
    for ms in [50, 100, 200, 500, 1000, 2000, 3000, 5000, 8000]:
        time.sleep(ms / 1000)
        r = urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=10)
        d = json.loads(r.read())
        ok, payload, err = d.get("ok"), d.get("data"), d.get("error", {})
        ec = (err or {}).get("code", "")
        sys.stdout.write(f"  {label} {ms}ms ok={ok} ec={ec} data={json.dumps(payload)[:80] if payload else None}\n")
        sys.stdout.flush()
        if ok and payload is not None:
            sys.stdout.write(f"  RESULT: {json.dumps(payload, indent=2)}\n")
            return payload
        if ec and ec != "not_found":
            sys.stdout.write(f"  ERROR: {json.dumps(err, indent=2)}\n")
            return None
    sys.stdout.write(f"  {label} result never appeared (TTL issue)\n")
    return None


# Step -1: get canonical digest for governed runs
def get_canonical_digest():
    r = call("gaps.status", {})
    if r and r.get("ok"):
        canonical = (r.get("data") or {}).get("canonical", {})
        d = canonical.get("current_canonical_digest") or ""
        return d.replace("sha256:", "") if d else None
    return None


# Step 0: check gap state
sys.stdout.write("=== gaps.get ===\n"); sys.stdout.flush()
r0 = call("gaps.get", {"gap_id": GAP_ID})
if r0:
    sys.stdout.write(f"ok={r0.get('ok')} error={r0.get('error')}\n")
    if r0.get("ok") and r0.get("data"):
        d = r0["data"]
        sys.stdout.write(json.dumps({k: d.get(k) for k in ["status","claimed_by","claim_expires_ts","workspace_id"]}, indent=2) + "\n")
    else:
        sys.stdout.write(f"data={json.dumps(r0.get('data'))}\n")
sys.stdout.flush()

# Step 1: re-claim (requires ctxpack_digest)
sys.stdout.write("\n=== gaps.claim ===\n"); sys.stdout.flush()
digest = get_canonical_digest()
sys.stdout.write(f"  canonical_digest={digest}\n"); sys.stdout.flush()
claim_input = {"gap_id": GAP_ID}
r1 = call("gaps.claim", claim_input, ctxpack_digest=digest)
if r1:
    run_id_claim = (r1.get("data") or {}).get("run_id")
    sys.stdout.write(f"ok={r1.get('ok')} run_id={run_id_claim}\n")
    sys.stdout.flush()
    if run_id_claim:
        claim_result = poll(run_id_claim, "claim")
        if claim_result:
            sys.stdout.write(f"CLAIM RESULT: {json.dumps(claim_result, indent=2)}\n")
        sys.stdout.flush()

# Step 2: workspace.provision immediately
sys.stdout.write("\n=== workspace.provision ===\n"); sys.stdout.flush()
r2 = call("workspace.provision", {"repo": REPO, "gap_id": GAP_ID})
if r2:
    run_id_prov = (r2.get("data") or {}).get("run_id")
    sys.stdout.write(f"ok={r2.get('ok')} run_id={run_id_prov}\n")
    sys.stdout.flush()
    if run_id_prov:
        poll(run_id_prov, "provision")

sys.stdout.write("\nDone.\n"); sys.stdout.flush()
