"""
Wait for claim to expire, then immediately re-claim and poll tightly for claim_token.
"""
import json, urllib.request, urllib.error, uuid, time
from pathlib import Path

creds = json.loads(Path.home().joinpath('.keyhole', 'credentials.json').read_text())
token = creds['access_token']
GAP_ID = 'gap_7cde6c0a3a116eb3'
DIGEST = '6bbb6f5727a7f76ea26d875ce8780439abfd71d4f45838ca3f2a2e57f77b25bc'
headers_base = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
}


def gaps_get():
    rid = str(uuid.uuid4())
    body = json.dumps({
        'run_type': 'gaps.get',
        'ctxpack_digest': DIGEST,
        'input': {'gap_id': GAP_ID}
    }).encode()
    req = urllib.request.Request(
        'https://mcp.keyholesolution.com/mcp/v1/runs/start',
        data=body,
        headers={**headers_base, 'X-Request-Id': rid, 'X-Idempotency-Key': rid},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        resp = json.loads(r.read())
        data = resp.get('data') or {}
        server_time = resp.get('keyhole', {}).get('server_time', '')
        status = data.get('status', 'unknown')
        claim = (data.get('meta') or {}).get('keyhole_claim', {}) or {}
        expires = claim.get('claim_expires_ts', '')
        return status, expires, server_time


def gaps_claim():
    rid = str(uuid.uuid4())
    body = json.dumps({
        'run_type': 'gaps.claim',
        'ctxpack_digest': DIGEST,
        'params': {'gap_id': GAP_ID, 'repo_name': 'my-first-app'}
    }).encode()
    req = urllib.request.Request(
        'https://mcp.keyholesolution.com/mcp/v1/runs/start',
        data=body,
        headers={**headers_base, 'X-Request-Id': rid, 'X-Idempotency-Key': rid},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.loads(r.read())
            data = resp.get('data') or {}
            return resp.get('ok'), data.get('run_id'), resp.get('error')
    except urllib.error.HTTPError as e:
        return False, None, json.loads(e.read()).get('error')


def poll_run(run_id):
    req = urllib.request.Request(
        f'https://mcp.keyholesolution.com/mcp/v1/runs/{run_id}',
        headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            resp = json.loads(r.read())
            return resp
    except urllib.error.HTTPError:
        return {}


print("Polling gap state until claim expires...")
for i in range(120):
    status, expires, server_time = gaps_get()
    print(f"  [{server_time}] status={status} expires={expires}")
    if status != 'CLAIMED':
        print("  Gap is no longer CLAIMED!")
        break
    time.sleep(5)
else:
    print("Timed out waiting for claim to expire")
    exit(1)

print("\nClaim expired. Re-claiming immediately...")
ok, run_id, err = gaps_claim()
print(f"gaps.claim: ok={ok} run_id={run_id} err={err}")

if run_id:
    print(f"Polling {run_id} at tight intervals...")
    t0 = time.monotonic()
    for delay_ms in [5, 10, 20, 30, 50, 75, 100, 150, 200, 300, 500]:
        time.sleep(delay_ms / 1000.0)
        elapsed_ms = (time.monotonic() - t0) * 1000
        resp = poll_run(run_id)
        data = resp.get('data') or {}
        error = resp.get('error') or {}
        if error.get('code') == 'not_found':
            print(f"  {elapsed_ms:.0f}ms: not_found")
        else:
            print(f"  {elapsed_ms:.0f}ms: ok={resp.get('ok')} data={json.dumps(data)[:300]}")
            if data:
                print("FULL DATA:")
                print(json.dumps(data, indent=2))
                break

print("\nChecking gap state after re-claim...")
status, expires, server_time = gaps_get()
print(f"status={status} expires={expires} server_time={server_time}")
