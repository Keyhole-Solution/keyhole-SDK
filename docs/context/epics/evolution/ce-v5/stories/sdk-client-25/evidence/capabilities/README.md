# Capabilities Snapshots

Captured `GET /mcp/v1/capabilities` responses used to drive flow
selection decisions.  Snapshots must include the response headers
(`ETag`, contract version) and a UTC timestamp.

Do not commit secrets.  Capabilities is a public read-only endpoint —
captures are safe by construction, but verify before commit.
