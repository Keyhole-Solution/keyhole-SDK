# Fallback Path — Authorization Code + PKCE

**Story:** SDK-CLIENT-25 §5.1 (preserved fallback)

When the boundary does not advertise `device_authorization`, the
client falls back to `authorization_code_pkce`.  This preserves
SDK-CLIENT-01 behaviour without modification.

## Capture requirements

  * `capabilities-snapshot.json` — proves device flow is **not**
    advertised at the time of fallback.
  * `pkce-flow-trace.json` — sanitised PKCE transcript (no
    `code_verifier`, no `authorization_code`).
  * `decision-record.yaml` — `flow: authorization_code_pkce`,
    `reason: pkce_fallback_advertised`.

## Non-regression

The fallback path must not change auth-state hygiene rules.  Logout,
re-auth, identity mismatch detection, and redaction all apply
identically regardless of selected flow.
