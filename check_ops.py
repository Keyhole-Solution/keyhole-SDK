import requests
import json

resp = requests.get('https://mcp.keyholesolution.com/mcp/v1/capabilities')
caps = resp.json()
ops = caps.get('data', {}).get('operations', [])

print(f"Total operations: {len(ops)}")
print()

gap_ops = [op for op in ops if 'gap' in op.get('run_type', '').lower()]
print(f"Gap operations: {len(gap_ops)}")
for op in gap_ops:
    print(f"  {op['run_type']}")

print()
print("All operation types (first 20):")
for i, op in enumerate(ops[:20]):
    print(f"  {op.get('run_type')}")
