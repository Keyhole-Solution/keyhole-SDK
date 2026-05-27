"""Probe workspace.provision with ctxpack_digest and check events."""
import json, urllib.request, urllib.error, time
from pathlib import Path

creds = json.loads(Path.home().joinpath('.keyhole', 'credentials.json').read_text())
token = creds['access_token']

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
}

# 1. Try workspace.provision with claim_token=""
print("=== workspace.provision with empty claim_token ===")
body = json.dumps({
    'run_type': 'workspace.provision',
    'repo_name': 'my-first-app',
    'ctxpack_digest': '6bbb6f5727a7f76ea26d875ce8780439abfd71d4f45838ca3f2a2e57f77b25bc',
    'input': {
        'repo': 'my-first-app',
        'gap_id': 'gap_7cde6c0a3a116eb3',
        'claim_token': ''
    }
}).encode()
req = urllib.request.Request(
    'https://mcp.keyholesolution.com/mcp/v1/runs/start',
    data=body,
    headers={**headers, 'X-Request-Id': 'ws-prov-ct-empty', 'X-Idempotency-Key': 'ws-prov-ct-empty'},
)
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        resp = json.loads(r.read())
        run_id = (resp.get('data') or {}).get('run_id')
        print(f'HTTP {r.status} ok={resp.get("ok")} run_id={run_id}')
        print(json.dumps(resp.get('data'), indent=2))
except urllib.error.HTTPError as e:
    print(f'HTTP {e.code}', json.loads(e.read()).get('error'))

# 2. Query events for workspace events
print("\n=== events.query for workspace events ===")
body = json.dumps({
    'run_type': 'events.replay',
    'input': {
        'subject_filter': 'gap_7cde6c0a3a116eb3',
        'limit': 20
    }
}).encode()
req = urllib.request.Request(
    'https://mcp.keyholesolution.com/mcp/v1/runs/start',
    data=body,
    headers={**headers, 'X-Request-Id': 'events-ws-01', 'X-Idempotency-Key': 'events-ws-01'},
)
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        resp = json.loads(r.read())
        data = resp.get('data') or {}
        events = data.get('events', [])
        print(f'HTTP {r.status} ok={resp.get("ok")} event_count={len(events)}')
        for ev in events[-5:]:
            print(' -', ev.get('event_type', ev.get('type')), ev.get('subject'), ev.get('status'))
except urllib.error.HTTPError as e:
    print(f'HTTP {e.code}', json.loads(e.read()).get('error', {}).get('code'))
