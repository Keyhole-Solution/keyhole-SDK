"""Test different body shapes for gaps.get."""
import json, urllib.request, urllib.error
from pathlib import Path

creds = json.loads(Path.home().joinpath('.keyhole', 'credentials.json').read_text())
token = creds['access_token']

shapes = [
    # both top-level and params
    {
        'run_type': 'gaps.get',
        'ctxpack_digest': '6bbb6f5727a7f76ea26d875ce8780439abfd71d4f45838ca3f2a2e57f77b25bc',
        'gap_id': 'gap_7cde6c0a3a116eb3',
        'params': {'gap_id': 'gap_7cde6c0a3a116eb3'}
    },
    # top-level + repo_name
    {
        'run_type': 'gaps.get',
        'ctxpack_digest': '6bbb6f5727a7f76ea26d875ce8780439abfd71d4f45838ca3f2a2e57f77b25bc',
        'gap_id': 'gap_7cde6c0a3a116eb3',
        'repo_name': 'my-first-app'
    },
    # under input key
    {
        'run_type': 'gaps.get',
        'ctxpack_digest': '6bbb6f5727a7f76ea26d875ce8780439abfd71d4f45838ca3f2a2e57f77b25bc',
        'input': {'gap_id': 'gap_7cde6c0a3a116eb3'}
    },
    # under data key
    {
        'run_type': 'gaps.get',
        'ctxpack_digest': '6bbb6f5727a7f76ea26d875ce8780439abfd71d4f45838ca3f2a2e57f77b25bc',
        'data': {'gap_id': 'gap_7cde6c0a3a116eb3'}
    },
]

for i, body_dict in enumerate(shapes):
    body = json.dumps(body_dict).encode()
    req = urllib.request.Request(
        'https://mcp.keyholesolution.com/mcp/v1/runs/start',
        data=body,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Request-Id': f'gaps-get-shape-{i:02d}',
            'X-Idempotency-Key': f'gaps-get-shape-{i:02d}',
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read())
            err = resp.get('error')
            data = resp.get('data')
            print(f'shape {i}: HTTP {r.status} ok={resp.get("ok")} error={err} data_snippet={str(data)[:120]}')
    except urllib.error.HTTPError as e:
        body_err = json.loads(e.read())
        print(f'shape {i}: HTTP {e.code} error={body_err.get("error")}')
