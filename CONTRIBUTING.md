# Contributing

Thanks for helping keep the Keyhole SDK clean and forkable.

Before opening a pull request, run:

```powershell
keyhole doctor
keyhole validate
keyhole validate .\my-first-app
pytest
```

Contribution rules:

- Keep the SDK as a client boundary.
- Do not add server-side governance authority to the SDK.
- Do not commit credentials, local `.env` files, generated receipts, proof bundles, or machine-specific paths.
- Use placeholders for examples: `https://your-keyhole-server.example.com` and `replace_me`.
- Keep live integration tests optional and skipped unless `KEYHOLE_MCP_URL` and `KEYHOLE_MCP_TOKEN` are explicitly configured.
