# my-first-app

`my-first-app` is a minimal starter app for the Keyhole SDK.

It demonstrates:

- A small application capability in `src/greet.py`.
- Local governance declarations.
- A capability passport.
- A local invariant test.
- Safe no-server behavior for public users.

Run locally:

```powershell
keyhole validate .\my-first-app
pytest .\my-first-app\tests
keyhole governed run --repo-dir .\my-first-app --no-live
```

Live governed commands require `KEYHOLE_MCP_URL` and `KEYHOLE_MCP_TOKEN`.
