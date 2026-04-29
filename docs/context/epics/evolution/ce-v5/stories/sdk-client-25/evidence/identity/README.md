# Identity Match / Mismatch Evidence

Captures of `detect_identity_mismatch` outcomes when the CLI and
VS Code authenticate independently against the same boundary.

Required artefacts per scenario:

  * `vscode-whoami.json` (redacted — keep `user_id`, `tenant_id`,
    `org_id`; drop email and any token-derived fields);
  * `cli-whoami.json` (same shape, same redaction);
  * `match-result.json` — `IdentityMatchResult` payload;
  * if mismatch: the rendered §9 warning text shown to the user.

The acceptance scenario requires that mismatch is surfaced clearly
and **never** silently ignored.
