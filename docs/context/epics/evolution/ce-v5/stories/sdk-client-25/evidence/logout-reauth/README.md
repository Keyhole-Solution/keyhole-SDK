# Logout / Re-Auth Hygiene Evidence

Transcripts demonstrating SDK-CLIENT-25 §8 acceptance criteria:

  1. `keyhole logout` revokes refresh + access tokens (best-effort)
     against the auth server's revocation endpoint.
  2. The credential store file is removed.
  3. Pending interactive auth attempts are marked superseded and
     cancel themselves on the next poll.
  4. Companion state files (`mcp_account.json`, PKCE state, device
     state, identity-context cache) are removed.
  5. A subsequent `keyhole login` begins a brand-new transaction —
     no leakage from the prior session.

Each evidence run should include:

  * `before-credentials.json` (safe summary);
  * `logout-result.json` (the `LogoutResult.to_safe_dict()` payload);
  * `after-listing.txt` (directory listing of `$KEYHOLE_HOME` showing
    that auth artefacts are gone);
  * `reauth-decision.yaml` (proof that the next login made a fresh
    flow-selection decision).
