# Credential Store Evidence

Before/after snapshots of `$KEYHOLE_HOME/credentials.json`
demonstrating that:

  * tokens are persisted with mode `0600` on POSIX;
  * logout fully removes the file;
  * a fresh login after logout writes a brand new session (different
    `created_at`, different `token_fingerprint`).

Files committed here must contain only `safe_summary()` output —
**never** raw access tokens or refresh tokens.
