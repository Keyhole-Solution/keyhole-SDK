"""Try workspace.provision help and check actual provision result."""
import json, urllib.request, urllib.error, time
from pathlib import Path

creds = json.loads(Path.home().joinpath('.keyhole', 'credentials.json').read_text())
token = creds['access_token']

headers_base = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
}

# 1. Run workspace.provision properly and immediately poll
print("=== workspace.provision dispatch ===")
body = json.dumps({
    'run_type': 'workspace.provision',
    'repo_name': 'my-first-app',
    'input': {
        'repo': 'my-first-app',
        'gap_id': 'gap_7cde6c0a3a116eb3',
    }
}).encode()
req = urllib.request.Request(
    'https://mcp.keyholesolution.com/mcp/v1/runs/start',
    data=body,
    headers={**headers_base, 'X-Request-Id': 'ws-prov-final-01', 'X-Idempotency-Key': 'ws-prov-final-01'},
)
run_id = None
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        resp = json.loads(r.read())
        run_id = (resp.get('data') or {}).get('run_id')
        print(f'HTTP {r.status} ok={resp.get("ok")} run_id={run_id}')
except urllib.error.HTTPError as e:
    print(f'HTTP {e.code}', json.loads(e.read()).get('error'))

if run_id:
    print(f"Polling {run_id} in tight loop...")
    for ms in [50, 100, 200, 500, 1000, 2000, 3000]:
        time.sleep(ms / 1000.0)
        req2 = urllib.request.Request(
            f'https://mcp.keyholesolution.com/mcp/v1/runs/{run_id}',
            headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
        )
        try:
            with urllib.request.urlopen(req2, timeout=5) as r:
                resp = json.loads(r.read())
                data = resp.get('data') or {}
                if isinstance(data, dict) and data.get('code') == 'not_found':
                    print(f'  {ms}ms: not_found')
                else:
                    print(f'  {ms}ms: HTTP {r.status}')
                    print(json.dumps(resp.get('data'), indent=2)[:500])
        except urllib.error.HTTPError as e:
            print(f'  {ms}ms: HTTP {e.code}')

# 2. Check gaps.get to see if workspace is now provisioned
print("\n=== gaps.get after provision ===")
body = json.dumps({
    'run_type': 'gaps.get',
    'ctxpack_digest': '6bbb6f5727a7f76ea26d875ce8780439abfd71d4f45838ca3f2a2e57f77b25bc',
    'input': {'gap_id': 'gap_7cde6c0a3a116eb3'}
}).encode()
req = urllib.request.Request(
    'https://mcp.keyholesolution.com/mcp/v1/runs/start',
    data=body,
    headers={**headers_base, 'X-Request-Id': 'gaps-get-post-prov', 'X-Idempotency-Key': 'gaps-get-post-prov'},
)
with urllib.request.urlopen(req, timeout=15) as r:
    resp = json.loads(r.read())
    data = resp.get('data', {})
    print('status:', data.get('status'))
    print('workspace:', json.dumps(data.get('workspace'), indent=2))
    print('blocked:', data.get('blocked'))
    print('blocked_reasons:', json.dumps(data.get('blocked_reasons'), indent=2))
