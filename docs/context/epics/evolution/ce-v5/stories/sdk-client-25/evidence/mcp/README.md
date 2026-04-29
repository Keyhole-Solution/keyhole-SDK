# MCP Boundary Call Evidence

Redacted transcripts of MCP calls made during SDK-CLIENT-25 flows:

  * `GET /mcp/v1/capabilities` (unauthenticated discovery);
  * `GET /mcp/v1/whoami` (post-login identity check);
  * any governed run dispatch performed as part of acceptance scenarios.

`Authorization: Bearer` headers must be redacted.  The diagnostic
recorder under `keyhole_sdk.sdk_client_25.diagnostics` produces
suitable safe transcripts.
