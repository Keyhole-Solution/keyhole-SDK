# Keyhole Test Runtime

The first public runtime container in the Keyhole developer ecosystem.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/healthz` | Health check |
| GET | `/identity` | Runtime identity and capabilities |
| GET | `/state` | Current local runtime state |
| POST | `/realize` | Realize a candidate digest |

## Local Development

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Docker

```bash
docker build -t keyhole-test-runtime .
docker run -p 8080:8080 keyhole-test-runtime
```

## Image

```text
ghcr.io/keyhole-solution/keyhole-test-runtime:latest
```

See [docs/test-runtime.md](../../docs/test-runtime.md) for full contract documentation.
