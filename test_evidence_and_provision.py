"""Try gaps.evidence.submit and workspace.provision with complete params."""
import json, urllib.request, urllib.error, time
from pathlib import Path
import uuid

creds = json.loads(Path.home().joinpath('.keyhole', 'credentials.json').read_text())
token = creds['access_token']

headers_base = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
}

GAP_ID = 'gap_7cde6c0a3a116eb3'
DIGEST = '6bbb6f5727a7f76ea26d875ce8780439abfd71d4f45838ca3f2a2e57f77b25bc'


def dispatch_and_poll(run_type, input_data=None, extra=None):
    rid = str(uuid.uuid4())
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
            run_id = (resp.get('data') or {}).get('run_id')
            print(f'  dispatch HTTP {r.status} ok={resp.get("ok")} run_id={run_id}')
            # Immediately poll
            if run_id:
                time.sleep(0.05)
                req2 = urllib.request.Request(
                    f'https://mcp.keyholesolution.com/mcp/v1/runs/{run_id}',
                    headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
                )
                with urllib.request.urlopen(req2, timeout=10) as r2:
                    poll_resp = json.loads(r2.read())
                    poll_data = poll_resp.get('data')
                    poll_error = poll_resp.get('error', {})
                    if poll_error.get('code') == 'not_found':
                        print(f'  poll: not_found (result expired)')
                    else:
                        print(f'  poll: ok={poll_resp.get("ok")} data={json.dumps(poll_data)[:300]}')
            else:
                print(f'  result: {json.dumps(resp.get("data") or resp.get("error"))[:300]}')
            return resp
    except urllib.error.HTTPError as e:
        resp = json.loads(e.read())
        print(f'  HTTP {e.code}: {json.dumps(resp.get("error", {}))[:200]}')
        return resp


# Check claim status first
print("=== Current gap state ===")
body = json.dumps({
    'run_type': 'gaps.get',
    'ctxpack_digest': DIGEST,
    'input': {'gap_id': GAP_ID}
}).encode()
req = urllib.request.Request(
    'https://mcp.keyholesolution.com/mcp/v1/runs/start',
    data=body,
    headers={**headers_base, 'X-Request-Id': str(uuid.uuid4()), 'X-Idempotency-Key': str(uuid.uuid4())},
)
with urllib.request.urlopen(req, timeout=15) as r:
    resp = json.loads(r.read())
    data = resp.get('data', {}) or {}
    print(f'status={data.get("status")} claim_expires={data.get("meta", {}).get("keyhole_claim", {}).get("claim_expires_ts")}')
    server_time = resp.get('keyhole', {}).get('server_time')
    print(f'server_time={server_time}')


# 1. gaps.evidence.submit with proper UUID idempotency key
print("\n=== gaps.evidence.submit ===")
dispatch_and_poll('gaps.evidence.submit', {
    'gap_id': GAP_ID,
    'evidence_type': 'capability_verified',
    'evidence': {
        'capability': 'my-first-app.greet.user.v1',
        'status': 'verified',
        'test_pass': True,
        'repo': 'my-first-app',
    }
})

# 2. workspace.provision with ALL possible params
print("\n=== workspace.provision (all params) ===")
dispatch_and_poll('workspace.provision', {
    'repo': 'my-first-app',
    'gap_id': GAP_ID,
    'capability': 'my-first-app.greet.user.v1',
    'workspace_kind': 'builder',
})
