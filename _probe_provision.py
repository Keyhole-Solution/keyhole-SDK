"""Claim + provision probe: claim gap, dispatch workspace.provision, poll result aggressively."""
import json
import time
import urllib.request
import uuid
from pathlib import Path

BASE = "https://mcp.keyholesolution.com"
GAP_ID = "gap_7cde6c0a3a116eb3"
REPO = "my-first-app"

creds = json.loads(Path.home().joinpath(".keyhole", "credentials.json").read_text())
token = creds["access_token"]
H = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def get_run(run_id):
    r = urllib.request.urlopen(
        urllib.request.Request(f"{BASE}/mcp/v1/runs/{run_id}", headers=H), timeout=10
    )
    return json.loads(r.read())


def dispatch(run_type, input_data, repo="keyhole-SDK"):
    rid = str(uuid.uuid4())
    payload = {"run_type": run_type, "repo": repo}
    if input_data:
        payload["input"] = input_data  # wire format uses "input", not "input_data"
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE}/mcp/v1/runs/start",
        data=body,
        headers={**H, "X-Request-Id": rid, "X-Idempotency-Key": rid},
    )
    try:
        r = urllib.request.urlopen(req, timeout=15)
        return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  HTTP {e.code}: {body[:300]}")
        raise


# ── Step 0: check current gap state ──────────────────────────────────────────
print("=== Step 0: gaps.get current state ===")
resp0, _ = dispatch("gaps.get", {"gap_id": GAP_ID})
gap_data = resp0.get("data") or {}
print(f"  ok={resp0.get('ok')}")
if resp0.get("ok"):
    print(json.dumps({k: gap_data.get(k) for k in ["status", "claimed_by", "claim_expires_ts", "workspace_id", "workspace"]}, indent=2))
else:
    print("  error:", resp0.get("error"))

# ── Step 1: re-claim the gap ───────────────────────────────────────────────────
print("\n=== Step 1: gaps.claim ===")
resp, status = dispatch("gaps.claim", {"gap_id": GAP_ID})
claim_run_id = resp.get("run_id")
print(f"  HTTP {status}  run_id={claim_run_id}")
print(json.dumps(resp, indent=2))

print("\n--- polling claim result ---")
claim_payload = None
for ms in [50, 100, 200, 500, 1000, 2000, 3000]:
    time.sleep(ms / 1000)
    d = get_run(claim_run_id)
    payload = d.get("data")
    ok = d.get("ok")
    err = d.get("error")
    snippet = json.dumps(payload)[:120] if payload else None
    print(f"  {ms}ms: ok={ok}  data={snippet}  err={err}")
    if ok and payload is not None:
        claim_payload = payload
        print("  CLAIM SUCCESS:", json.dumps(payload, indent=2)[:400])
        break
    if err and (err.get("code") or "") not in ("not_found", ""):
        print("  CLAIM ERROR:", json.dumps(err))
        break

# ── Step 2: workspace.provision immediately ────────────────────────────────────
print("\n=== Step 2: workspace.provision ===")
resp2, status2 = dispatch("workspace.provision", {"repo": REPO, "gap_id": GAP_ID})
prov_run_id = resp2.get("run_id")
print(f"  HTTP {status2}  run_id={prov_run_id}")
print(json.dumps(resp2, indent=2))

print("\n--- polling provision result ---")
for ms in [50, 100, 200, 500, 1000, 2000, 3000, 5000, 8000, 12000]:
    time.sleep(ms / 1000)
    d = get_run(prov_run_id)
    ok = d.get("ok")
    payload = d.get("data")
    err = d.get("error")
    snippet = json.dumps(payload)[:120] if payload else None
    print(f"  {ms}ms: ok={ok}  data={snippet}  err={err}")
    if ok and payload is not None:
        print("  PROVISION SUCCESS:", json.dumps(payload, indent=2))
        break
    if err and (err.get("code") or "") not in ("not_found", ""):
        print("  PROVISION ERROR:", json.dumps(err, indent=2))
        break
else:
    print("  All polls exhausted — result still unknown (run result TTL issue)")

print("\nDone.")
