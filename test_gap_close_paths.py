"""Explore convergence.gap.resolve and proof paths for CLAIMED gap."""
import json, urllib.request, urllib.error, time
from pathlib import Path

creds = json.loads(Path.home().joinpath('.keyhole', 'credentials.json').read_text())
token = creds['access_token']

headers_base = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
}

GAP_ID = 'gap_7cde6c0a3a116eb3'
DIGEST = '6bbb6f5727a7f76ea26d875ce8780439abfd71d4f45838ca3f2a2e57f77b25bc'


def dispatch(run_type, input_data=None, rid=None, extra=None):
    if rid is None:
        rid = run_type.replace('.', '-')
    body_dict = {
        'run_type': run_type,
        'repo_name': 'my-first-app',
        'ctxpack_digest': DIGEST,
    }
    if input_data:
        body_dict['input'] = input_data
    if extra:
        body_dict.update(extra)
    body = json.dumps(body_dict).encode()
    req = urllib.request.Request(
        'https://mcp.keyholesolution.com/mcp/v1/runs/start',
        data=body,
        headers={**headers_base, 'X-Request-Id': rid, 'X-Idempotency-Key': rid},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read())
            return r.status, resp
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


# 1. convergence.gap.resolve
print("=== convergence.gap.resolve ===")
status, resp = dispatch('convergence.gap.resolve', {'gap_id': GAP_ID, 'resolution': 'resolved'}, 'cgr-01')
print(f'HTTP {status} ok={resp.get("ok")}')
print(json.dumps(resp.get('data') or resp.get('error'), indent=2)[:600])

# 2. proof.bundle.emit
print("\n=== proof.bundle.emit ===")
status, resp = dispatch('proof.bundle.emit', {
    'gap_id': GAP_ID,
    'capability': 'my-first-app.greet.user.v1',
    'repo': 'my-first-app',
}, 'pbe-01')
print(f'HTTP {status} ok={resp.get("ok")}')
print(json.dumps(resp.get('data') or resp.get('error'), indent=2)[:600])

# 3. proofbundle.build
print("\n=== proofbundle.build ===")
status, resp = dispatch('proofbundle.build', {
    'gap_id': GAP_ID,
    'capability': 'my-first-app.greet.user.v1',
    'repo': 'my-first-app',
}, 'pbb-01')
print(f'HTTP {status} ok={resp.get("ok")}')
print(json.dumps(resp.get('data') or resp.get('error'), indent=2)[:600])

# 4. gaps.evidence.submit
print("\n=== gaps.evidence.submit ===")
status, resp = dispatch('gaps.evidence.submit', {
    'gap_id': GAP_ID,
    'evidence_type': 'test_pass',
    'evidence': {'capability': 'my-first-app.greet.user.v1', 'status': 'verified'},
}, 'ges-01')
print(f'HTTP {status} ok={resp.get("ok")}')
print(json.dumps(resp.get('data') or resp.get('error'), indent=2)[:600])
