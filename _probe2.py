"""Probe: gaps.claim -> extract claim_token -> workspace.provision -> poll."""
import json, sys, time, urllib.error, urllib.request, uuid
from pathlib import Path

BASE = "https://mcp.keyholesolution.com"
GAP_ID = "gap_810669d1c41e2041"
REPO = "my-first-app"


def _headers():
    """Reload token from disk on every call to pick up fresh token."""
    creds = json.loads(Path.home().joinpath(".keyhole", "credentials.json").read_text())
    return {
        "Authorization": "Bearer " + creds["access_token"],
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def dispatch(payload):
    """Send an exact payload to /mcp/v1/runs/start and return the response.
    Logs the exact JSON sent so the wire format is always visible.
    """
    rid = str(uuid.uuid4())
    body = json.dumps(payload).encode()
    sys.stdout.write(f"  SEND: {json.dumps(payload)}\n"); sys.stdout.flush()
    req = urllib.request.Request(
        BASE + "/mcp/v1/runs/start", data=body,
        headers={**_headers(), "X-Request-Id": rid, "X-Idempotency-Key": rid},
    )
    try:
        raw = json.loads(urllib.request.urlopen(req, timeout=15).read())
        sys.stdout.write(f"  RECV: {json.dumps(raw)[:600]}\n"); sys.stdout.flush()
        return raw
    except urllib.error.HTTPError as e:
        body_str = e.read().decode()
        sys.stdout.write(f"  HTTP {e.code}: {body_str[:400]}\n"); sys.stdout.flush()
        return None


def poll(run_id, label=""):
    url = BASE + "/mcp/v1/runs/" + run_id
    for ms in [50, 100, 200, 500, 1000, 2000, 3000, 5000, 8000]:
        time.sleep(ms / 1000)
        r = urllib.request.urlopen(urllib.request.Request(url, headers=_headers()), timeout=10)
        d = json.loads(r.read())
        ok, payload, err = d.get("ok"), d.get("data"), d.get("error", {})
        ec = (err or {}).get("code", "")
        sys.stdout.write(f"  {label} {ms}ms ok={ok} ec={ec}\n"); sys.stdout.flush()
        if ok and payload is not None:
            sys.stdout.write(f"  RESULT: {json.dumps(payload, indent=2)[:1200]}\n")
            return payload
        if ec and ec != "not_found":
            sys.stdout.write(f"  ERROR: {json.dumps(err, indent=2)[:600]}\n")
            return None
    sys.stdout.write(f"  {label} result never appeared\n")
    return None


def extract_claim_token(poll_result):
    """Pull claim_token out of the run result envelope."""
    if poll_result is None:
        return None
    # The GET /runs/<id> response wraps the executor output in 'output' (JSON string)
    for key in ("output", "result"):
        val = poll_result.get(key)
        if isinstance(val, str):
            try:
                parsed = json.loads(val)
                tok = parsed.get("claim_token")
                if tok:
                    return tok
            except Exception:
                pass
        elif isinstance(val, dict):
            tok = val.get("claim_token")
            if tok:
                return tok
    # Also look inside the nested 'run' wrapper if present
    run_wrapper = poll_result.get("run") or {}
    for key in ("output", "result"):
        val = run_wrapper.get(key)
        if isinstance(val, str):
            try:
                parsed = json.loads(val)
                tok = parsed.get("claim_token")
                if tok:
                    return tok
            except Exception:
                pass
    return None


# ── Step 0: gaps.get — check current gap state ─────────────────────────────
sys.stdout.write("=== gaps.get ===\n"); sys.stdout.flush()
r0 = dispatch({"run_type": "gaps.get", "repo": REPO, "input": {"gap_id": GAP_ID}})
gap_status = None
if r0 and r0.get("ok") and r0.get("data"):
    d = r0["data"]
    gap_status = d.get("status")
    sys.stdout.write(json.dumps(
        {k: d.get(k) for k in ["status", "claimed_by", "claim_expires_ts", "workspace_id"]},
        indent=2) + "\n")
sys.stdout.flush()

# ── Step 0b: if already CLAIMED by us, release so we can get a fresh token ─
if gap_status == "CLAIMED":
    sys.stdout.write("\n=== gaps.claim (release) ===\n"); sys.stdout.flush()
    rr = dispatch({"run_type": "gaps.claim", "repo": REPO,
                   "input": {"action": "release", "gap_id": GAP_ID}})
    if rr and (rr.get("data") or {}).get("run_id"):
        poll((rr["data"]["run_id"]), "release")
    sys.stdout.write("  released — waiting 1s for state to settle\n"); sys.stdout.flush()
    time.sleep(1)

# ── Step 1: get canonical digest then claim the gap ────────────────────────
sys.stdout.write("\n=== gaps.status (canonical digest) ===\n"); sys.stdout.flush()
rs = dispatch({"run_type": "gaps.status", "repo": REPO, "input": {}})
digest = None
if rs and rs.get("ok"):
    canonical = (rs.get("data") or {}).get("canonical", {})
    raw_d = canonical.get("current_canonical_digest") or ""
    digest = raw_d.replace("sha256:", "") if raw_d else None
sys.stdout.write(f"  canonical_digest={digest}\n"); sys.stdout.flush()

sys.stdout.write("\n=== gaps.claim ===\n"); sys.stdout.flush()
r1 = dispatch({
    "run_type": "gaps.claim",
    "repo": REPO,
    "ctxpack_digest": digest,
    "input": {"gap_id": GAP_ID},
})
claim_result = None
claim_token = None
if r1 and (r1.get("data") or {}).get("run_id"):
    run_id_claim = r1["data"]["run_id"]
    sys.stdout.write(f"  run_id={run_id_claim}\n"); sys.stdout.flush()
    claim_result = poll(run_id_claim, "claim")
    claim_token = extract_claim_token(claim_result)
    sys.stdout.write(f"  claim_token={claim_token}\n"); sys.stdout.flush()

if not claim_token:
    sys.stdout.write("  ABORT: no claim_token — cannot proceed to workspace.provision\n")
    sys.exit(1)

# ── Step 2: workspace.provision ────────────────────────────────────────────
# Use the exact shape from next_best_actions (NO top-level 'repo').
# If the server still returns input_value={} this is a confirmed server bug.
sys.stdout.write("\n=== workspace.provision (shape A: no top-level repo) ===\n"); sys.stdout.flush()
r2a = dispatch({
    "run_type": "workspace.provision",
    "input": {"gap_id": GAP_ID, "claim_token": claim_token},
})
run_id_prov = None
if r2a and (r2a.get("data") or {}).get("run_id"):
    run_id_prov = r2a["data"]["run_id"]
    sys.stdout.write(f"  run_id={run_id_prov}\n"); sys.stdout.flush()
    prov_result = poll(run_id_prov, "provision-A")
    if prov_result and (prov_result.get("status") or "") not in ("failed",):
        sys.stdout.write("  Shape A SUCCEEDED\n"); sys.stdout.flush()
        run_id_prov = None  # mark done so Shape B is skipped

# ── Step 2b: if shape A still gets input_value={}, try with top-level repo ─
if run_id_prov is not None:  # shape A returned a run_id but it failed
    prov_err = (prov_result.get("error") if prov_result else None) or ""
    if "input_value={}" in json.dumps(prov_err):
        sys.stdout.write("\n=== workspace.provision (shape B: with top-level repo) ===\n"); sys.stdout.flush()
        r2b = dispatch({
            "run_type": "workspace.provision",
            "repo": REPO,
            "input": {"gap_id": GAP_ID, "claim_token": claim_token},
        })
        if r2b and (r2b.get("data") or {}).get("run_id"):
            run_id_prov2 = r2b["data"]["run_id"]
            sys.stdout.write(f"  run_id={run_id_prov2}\n"); sys.stdout.flush()
            poll(run_id_prov2, "provision-B")

sys.stdout.write("\nDone.\n"); sys.stdout.flush()
