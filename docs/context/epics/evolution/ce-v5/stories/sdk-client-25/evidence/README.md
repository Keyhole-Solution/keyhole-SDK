# SDK-CLIENT-25 — Evidence Index

VS Code MCP Passwordless Auth Client: Device Flow, Logout Recovery,
and Auth State Hygiene.

This evidence directory mirrors the §10 acceptance evidence requirements
of the story.

## Subdirectories

| Directory          | Purpose                                                  |
|--------------------|----------------------------------------------------------|
| `decision/`        | Client-side flow-selection decision records.             |
| `capabilities/`    | Captured `GET /mcp/v1/capabilities` snapshots used.      |
| `device-flow/`     | RFC 8628 device-authorization request/response samples.  |
| `credentials/`     | Credential-store before/after diffs (redacted).          |
| `mcp/`             | MCP boundary call logs (whoami, redacted).               |
| `logout-reauth/`   | Logout + re-auth transcripts.                            |
| `identity/`        | Identity-match / identity-mismatch evidence.             |
| `tests/`           | Unit + integration test result captures.                 |
| `promotion/`       | Promotion / contract-promotion evidence.                 |

## Truthfulness

All artefacts under this tree must be:

  * generated against the live MCP boundary (or explicitly labelled as
    local-only fixture for development);
  * redaction-checked — no access tokens, refresh tokens, device codes,
    or other secrets in committed artefacts;
  * traceable back to a specific run-id when capturing governed runs.

See `../../sdk-client-25.md` for the full story spec.
