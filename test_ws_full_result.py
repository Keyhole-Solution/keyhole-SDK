"""Capture full workspace.provision response at 50ms."""
import json, urllib.request, urllib.error, time
from pathlib import Path

creds = json.loads(Path.home().joinpath('.keyhole', 'credentials.json').read_text())
token = creds['access_token']

headers_base = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
}

# 1. Dispatch workspace.provision
body = json.dumps({
    'run_type': 'workspace.provision',
    'repo_name': 'my-first-app',
    'ctxpack_digest': '6bbb6f5727a7f76ea26d875ce8780439abfd71d4f45838ca3f2a2e57f77b25bc',
    'input': {
        'repo': 'my-first-app',
        'gap_id': 'gap_7cde6c0a3a116eb3',
    }
}).encode()
req = urllib.request.Request(
    'https://mcp.keyholesolution.com/mcp/v1/runs/start',
    data=body,
    headers={**headers_base, 'X-Request-Id': 'ws-prov-full-01', 'X-Idempotency-Key': 'ws-prov-full-01'},
)
run_id = None
with urllib.request.urlopen(req, timeout=15) as r:
    resp = json.loads(r.read())
    run_id = (resp.get('data') or {}).get('run_id')
    print(f'Dispatched: HTTP {r.status} run_id={run_id}')

if run_id:
    time.sleep(0.05)  # 50ms
    req2 = urllib.request.Request(
        f'https://mcp.keyholesolution.com/mcp/v1/runs/{run_id}',
        headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    )
    with urllib.request.urlopen(req2, timeout=10) as r:
        full_resp = json.loads(r.read())
        print(f'Poll result HTTP {r.status}:')
        # Print the entire response
        print(json.dumps(full_resp, indent=2))
