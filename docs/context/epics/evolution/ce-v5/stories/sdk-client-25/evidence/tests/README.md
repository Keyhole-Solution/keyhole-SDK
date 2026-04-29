# Test Result Captures

Per-target pytest captures for SDK-CLIENT-25.  Generate with:

```
make sdk.client.test
make sdk.client.auth.verify
make sdk.client.device-auth.verify
make sdk.client.logout-reauth.verify
make sdk.client.identity-mismatch.verify
make sdk.client.redaction.verify
```

Commit the captured stdout (with timestamps and host info redacted)
under this directory as part of the evidence package.
