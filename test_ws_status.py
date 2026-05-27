"""Check workspace and gaps status."""
import json, urllib.request, urllib.error
from pathlib import Path

creds = json.loads(Path.home().joinpath('.keyhole', 'credentials.json').read_text())
token = creds['access_token']

for run_type in ['workspace.status', 'gaps.status']:
    rid = 'check-' + run_type.replace('.', '-')
    body = json.dumps({
        'run_type': run_type,
        'repo_name': 'my-first-app',
        'input': {'repo': 'my-first-app'}
    }).encode()
    req = urllib.request.Request(
        'https://mcp.keyholesolution.com/mcp/v1/runs/start',
        data=body,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Request-Id': rid,
            'X-Idempotency-Key': rid,
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read())
            print(f'{run_type}: ok={resp.get("ok")}')
            print(json.dumps(resp.get('data'), indent=2))
    except urllib.error.HTTPError as e:
        print(f'{run_type}: HTTP {e.code}', json.loads(e.read()).get('error', {}).get('code'))
