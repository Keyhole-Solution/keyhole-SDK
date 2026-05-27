"""Try gaps.claim with different action values."""
import json, urllib.request, urllib.error, uuid
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

for action in ['status', 'inspect', 'token', 'refresh', 'extend']:
    rid = str(uuid.uuid4())
    body = json.dumps({
        'run_type': 'gaps.claim',
        'ctxpack_digest': DIGEST,
        'input': {'action': action, 'gap_id': GAP_ID}
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
            err = resp.get('error')
            snippet = json.dumps(data)[:200] if data else None
            print(f'action={action}: ok={resp.get("ok")} data_snippet={snippet} err={err}')
    except urllib.error.HTTPError as e:
        print(f'action={action}: HTTP {e.code}', json.loads(e.read()).get('error', {}).get('code'))
