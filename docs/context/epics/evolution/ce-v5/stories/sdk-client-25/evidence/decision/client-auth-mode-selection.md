# Client Auth Mode Selection

**Story:** SDK-CLIENT-25 §5.1, §7.1

The client selects an interactive auth flow exclusively from the
boundary-advertised `auth.supported_flows`, biased by
`auth.preferred_interactive_flow`.

## Decision rule

1. Fetch `GET /mcp/v1/capabilities`.
2. Read `auth.supported_flows` and `auth.preferred_interactive_flow`.
3. Apply `keyhole_sdk.sdk_client_25.select_auth_flow(capabilities)`:
   * If the server prefers `device_authorization` and it is advertised →
     select **device authorization**.
   * Else if `device_authorization` is advertised → select it.
   * Else if `authorization_code_pkce` is advertised → fall back to PKCE.
   * Else → raise `UnsupportedAuthFlowError`.
4. The client must never select a flow not advertised in
   `supported_flows`, and must never select any of the forbidden flows
   (`custom_magic_link_queue`, `magic_link_queue`, `mcp_magic_link`,
   `password`, `ropc`).

## Decision record format

Each decision record committed under `decision/` should capture:

```yaml
decision:
  flow: device_authorization
  reason: server_preferred_device_authorization
  considered:
    - authorization_code_pkce
    - device_authorization
  preferred_by_server: device_authorization
  capabilities_etag: "<from response header>"
  captured_at: "<ISO-8601 UTC>"
```

The decision is logged locally; it is not a substitute for boundary
authority.
