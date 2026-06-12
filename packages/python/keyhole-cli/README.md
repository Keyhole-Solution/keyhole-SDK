# keyhole-cli

Public CLI for Keyhole SDK projects.

Primary commands:

- `keyhole doctor`
- `keyhole validate`
- `keyhole repo register`
- `keyhole context compile`
- `keyhole run`
- `keyhole governed run`
- `keyhole governed status`
- `keyhole governed resume`
- `keyhole governed receipt`

Local validation works without server credentials. Live governed commands require:

```powershell
$env:KEYHOLE_MCP_URL = "https://your-keyhole-server.example.com"
$env:KEYHOLE_MCP_TOKEN = "replace_me"
```
