import requests
resp = requests.get('https://mcp.keyholesolution.com/mcp/v1/capabilities')
caps = resp.json()
ops = caps.get('data', {}).get('operations', [])
gap_ops = [op['run_type'] for op in ops if 'gap' in op.get('run_type', '').lower()]
print('Available gap operations:')
for op in sorted(gap_ops):
    print(f'  {op}')
