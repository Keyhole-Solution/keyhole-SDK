# VS Code Device Flow Support

**Story:** SDK-CLIENT-25 §7.2–7.4

Captures evidence that the client correctly drives the OAuth 2.0
Device Authorization Grant (RFC 8628) when selected.

## Required artefacts

For each captured run:

  * `device-authorization-request.json` — POST body and redacted headers.
  * `device-authorization-response.json` — server response with
    `device_code` and `user_code` redacted.  Keep `verification_uri`,
    `expires_in`, and `interval`.
  * `polling-trace.json` — chronological list of poll outcomes:
    `authorization_pending`, `slow_down`, `success`, etc.  Include
    interval changes (e.g. 5 → 10 after `slow_down`).
  * `token-success.json` — final token response with `access_token`,
    `refresh_token`, and `id_token` redacted.

## Behavioural invariants

  * `slow_down` increases the polling interval by 5 seconds, capped at
    60 seconds.
  * `expired_token` / `expired_device_code` immediately abort polling
    with `DeviceAuthorizationExpired`.
  * `access_denied` immediately aborts polling with
    `DeviceAuthorizationDenied`.
  * Network failures retry with bounded budget
    (≤ 3 consecutive failures) before raising
    `DeviceAuthorizationNetworkError`.
  * Pending attempts are checked for supersession on every poll.
  * Polling never blocks past `expires_in`.
