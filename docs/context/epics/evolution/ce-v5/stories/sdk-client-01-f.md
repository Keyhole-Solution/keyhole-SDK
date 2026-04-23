SDK-CLIENT-01-F — Standard Browser OIDC Compatibility, Validation, and Passwordless Support UX

Status: READY FOR IMPLEMENTATION
Owner / Author: Keyhole Solution Foundation
Lane: Dev (design + validation), Prod (promotion only)
Depends on: SDK-CLIENT-01, SDK-CLIENT-01-B, SDK-CLIENT-01-C, SDK-CLIENT-01-D, SDK-CLIENT-01-E, SDK-CLIENT-20, SDK-CLIENT-21, SDK-CLIENT-22, SDK-SERVER-01-F
Paired With: SDK-SERVER-01-F — PKCE-Compatible Passwordless Browser Flow for Standard OIDC Clients
Purpose: Define the client-side validation, diagnostics, guidance, and support-bundle UX for standards-based browser OIDC clients so IDEs and similar tools can use the normal Authorization Code + PKCE flow against Keyhole without proxies, token injection, alternate login paths, or story-map confusion with the already-deployed 01-D and 01-E host capabilities.

1. Goal

Close the client-side gap for browser-based OIDC public clients by making the supported path explicit, verifiable, diagnosable, and safe.

This story makes the following true:

browser/OIDC clients use the normal Authorization Code + PKCE flow,
no client-side proxy or token-injection workaround is part of the supported product surface,
builders can validate that a given OIDC client configuration is compatible with the Keyhole auth boundary,
builders can distinguish standard browser-flow problems from MCP/runtime problems,
builders can gather a deterministic support bundle when a browser-based login fails,
builders can clearly understand that:
the emailed code is a verification factor,
not the OIDC authorization code,
and the magic link is simply a convenience path that completes the same suspended auth session.
2. Story Map Correction / Placement

This story exists because the current auth/host sequence is already occupied as follows:

SDK-CLIENT-01-C — MCP Host Identity Reconciliation, Doctor Discovery, Connection Binding UX
SDK-CLIENT-01-D — Host Credential Installation, Extension Reconciliation, Live Principal Alignment
SDK-CLIENT-01-E — Auto-Detection, MCP Boundary Probing, Governed Mode Auto-Promotion

Therefore this browser-passwordless compatibility story must be placed at:

SDK-CLIENT-01-F
paired with SDK-SERVER-01-F

This story does not replace or mutate the meaning of the already-implemented 01-D or 01-E stories.

3. Problem Statement

The platform already has:

auth bootstrap,
CLI login,
planned credential/profile lifecycle,
host identity discovery and reconciliation,
host credential installation/reconciliation,
auto-detection and boundary probing,
and a complete passwordless email-code login for CLI users.

But none of that by itself gives builders a clean answer to a different class of issue:

an IDE or browser-based OIDC client opens the standard PKCE browser flow,
the realm/browser flow must authenticate the user,
the browser flow fails or times out,
builders need to know whether the problem is:
discovery/configuration,
browser auth UX,
redirect/callback compatibility,
missing passwordless browser continuation support,
or an unsupported workaround path such as a proxy.

Without this story, people and agents are tempted to invent alternate integration paths that look helpful but violate the intended design.

4. Why This Story Exists

The platform needs a client-side story for browser-based OIDC support that is as disciplined as the server-side story.

This story exists to ensure that:

the supported path is explicit,
unsupported detours are rejected,
browser-flow validation is easy,
passwordless browser login is explainable,
failures produce repair guidance,
support artifacts are gathered without contaminating the product with the wrong integration pattern,
and the browser compatibility story is kept distinct from:
01-C doctor/reconciliation,
01-D host install/reconciliation,
01-E host auto-detection/probing.

This is not a second login flow. It is a validation and support story for the standard login flow.

5. Strategic Outcome

After this story, a builder or operator can do the following:

keyhole auth browser-check --client-id vscode-copilot-bridge --realm kh-prod
keyhole auth browser-check --client-id vscode-copilot-bridge --realm kh-prod --redirect-uri http://127.0.0.1:33419/
keyhole auth browser-support-bundle --client-id vscode-copilot-bridge --realm kh-prod
keyhole auth explain-browser --bundle <path>

And receive truthful output such as:

OIDC Browser Compatibility Check
Realm: kh-prod
Client: vscode-copilot-bridge

Authorization Code + PKCE: supported
OIDC discovery: OK
Authorization endpoint: OK
Token endpoint: OK
Loopback redirect pattern: OK
Passwordless browser continuation: supported
offline_access request posture: allowed

Verdict: COMPATIBLE
Recommended path: use direct browser PKCE login
Unsupported paths: mcp-proxy, token injection, CLI credential shadowing

Or, on failure:

OIDC Browser Compatibility Check
Realm: kh-prod
Client: vscode-copilot-bridge

OIDC discovery: OK
Authorization endpoint: OK
Token endpoint: OK
Passwordless browser continuation: NOT SUPPORTED

Verdict: BLOCKED
Repair:
  1. deploy SDK-SERVER-01-F
  2. rerun browser-check
  3. do not use mcp-proxy as an alternate auth path
6. Delivers

This story delivers:

a browser/OIDC compatibility check command,
a browser auth support-bundle command,
browser auth explanation/rendering UX,
clear client-facing guidance for standard PKCE browser login,
explicit rejection of proxy/token-injection login paths,
validation that direct auth and MCP endpoint configuration is correct,
deterministic repair guidance for browser auth failures,
cross-reference-safe naming that preserves the existing meaning of 01-D and 01-E.
7. Constitutional Fit

This story preserves the following:

the standard OIDC Authorization Code + PKCE path remains the only supported browser-client login path,
the CLI does not become an identity-smuggling layer for IDE/browser clients,
the client does not invent alternate token paths,
explainability and support bundles remain first-class,
the product surface stays aligned with the platform’s preference for deterministic, bounded, provable behavior,
the existing 01-C/01-D/01-E host-control stories remain intact and unambiguous.
8. Design Principles
8.1 Standards first

Browser clients must authenticate using normal OIDC Authorization Code + PKCE behavior.

8.2 No alternate client auth path

The CLI must not become a hidden auth bridge for IDE/browser clients.

8.3 No proxy surface

Local proxy/token injection is not part of the supported product design.

8.4 Diagnose before workaround

The right move is to validate the standard path and explain failures, not invent a side path.

8.5 Code and magic link are one auth-session completion model

The client UX and docs must make it clear that both methods complete the same suspended browser auth session.

8.6 Browser issues are not MCP issues

The client must distinguish browser/OIDC compatibility failures from MCP tool/runtime failures.

8.7 Support bundles must be reproducible

When browser auth fails, the captured artifact set must make the failure explainable and repeatable.

8.8 Story-map discipline matters

This story must not overload or rename already-deployed 01-D or 01-E capabilities.

9. Non-Goals

This story does not:

introduce a new CLI login mode for IDE/browser clients,
proxy browser auth through the CLI,
inject bearer tokens into IDE clients,
keep mcp-proxy as a supported product path,
replace the IDE’s own OAuth/OIDC implementation,
change the server-side browser flow itself,
add new MCP executable operations,
replace 01-C, 01-D, or 01-E.
10. Terms
10.1 Browser OIDC client

A public client that authenticates by opening the authorization endpoint in a browser and completing Authorization Code + PKCE.

10.2 Browser compatibility check

A client-side validation that confirms the standard browser login prerequisites and posture.

10.3 Browser auth support bundle

A deterministic artifact set capturing discovery, client metadata, redirect posture, auth attempt context, and observed failure details.

10.4 Passwordless browser continuation

The server-side ability for a passwordless user to finish the same browser auth session with either code entry or magic link.

10.5 Unsupported detour

Any path that bypasses or shadows the standard browser PKCE flow, including proxies and token injection.

11. Required CLI Surfaces
11.1 keyhole auth browser-check

Purpose: validate whether a standards-based browser OIDC client is correctly positioned to authenticate against Keyhole using the intended path.

Example usage
keyhole auth browser-check --client-id vscode-copilot-bridge --realm kh-prod
keyhole auth browser-check --client-id vscode-copilot-bridge --realm kh-prod --redirect-uri http://127.0.0.1:33419/
keyhole auth browser-check --client-id vscode-copilot-bridge --realm kh-prod --json
Responsibilities
inspect OIDC discovery metadata,
inspect authorization endpoint reachability,
inspect token endpoint reachability,
validate redirect URI posture when provided,
validate that the client is using the direct Keyhole auth boundary,
validate that the client is intended for Authorization Code + PKCE,
validate whether passwordless browser continuation support is present,
render a final verdict:
compatible
blocked
misconfigured
unsupported_detour_detected
Output fields
realm
client_id
issuer
authorization_endpoint
token_endpoint
redirect posture
PKCE posture
passwordless browser continuation support
offline_access posture when inferable
verdict
repair guidance
11.2 keyhole auth browser-support-bundle

Purpose: generate a deterministic support bundle for browser auth failures.

Example usage
keyhole auth browser-support-bundle --client-id vscode-copilot-bridge --realm kh-prod
keyhole auth browser-support-bundle --client-id vscode-copilot-bridge --realm kh-prod --redirect-uri http://127.0.0.1:33419/
keyhole auth browser-support-bundle --json
Responsibilities
capture relevant discovery documents,
capture client input parameters,
capture redirect URI posture,
capture observed compatibility check results,
capture browser-auth failure classification if supplied,
emit a deterministic artifact set for explainability/support.
11.3 keyhole auth explain-browser

Purpose: explain a previously captured browser auth bundle in human-readable form.

Example usage
keyhole auth explain-browser --bundle <path>
Responsibilities
summarize the attempted browser flow,
classify the failure or success posture,
distinguish:
auth-boundary failure,
browser-flow incompatibility,
redirect/callback mismatch,
unsupported workaround path,
render concrete repair guidance.
12. Required Client Behaviors
12.1 Standard-path enforcement

The client must document and render the standard supported path as:

OIDC Authorization Code + PKCE
→ browser auth
→ redirect callback
→ token exchange
12.2 Explicit unsupported-path guidance

The client must explicitly mark the following as unsupported product paths:

local proxy auth injection,
token duplication/shadowing,
CLI-mediated browser auth substitution,
alternate callback bypass paths.
12.3 Direct endpoint posture validation

If the user provides or the environment reveals a direct MCP/auth configuration, the client must validate that it points directly to the intended Keyhole boundary rather than a local proxy detour.

12.4 Passwordless semantics clarity

The client must clearly communicate:

the emailed code is a verification code,
not the PKCE/OIDC authorization code,
the magic link is simply a convenience path that completes the same suspended auth session.
12.5 Compatibility posture rendering

The client must render whether the current environment is:

standard-compatible,
blocked on server browser-flow support,
locally misconfigured,
or contaminated by an unsupported detour.
12.6 Cross-story boundary clarity

The client must keep browser compatibility separate from:

01-C doctor/reconciliation,
01-D host install/reconciliation,
01-E auto-detection/probing.
13. Validation Model
13.1 BrowserCompatibilityReport
{
  "realm": "kh-prod",
  "client_id": "vscode-copilot-bridge",
  "issuer": "https://auth.keyholesolution.com/realms/kh-prod",
  "authorization_endpoint": "https://auth.keyholesolution.com/realms/kh-prod/protocol/openid-connect/auth",
  "token_endpoint": "https://auth.keyholesolution.com/realms/kh-prod/protocol/openid-connect/token",
  "redirect_uri": "http://127.0.0.1:33419/",
  "pkce_posture": "supported",
  "passwordless_browser_posture": "supported",
  "direct_mcp_posture": "direct",
  "unsupported_detour_detected": false,
  "verdict": "compatible",
  "repair": []
}
13.2 BrowserSupportBundleIndex
{
  "bundle_id": "brwsup_...",
  "created_at": "2026-04-22T10:22:00Z",
  "realm": "kh-prod",
  "client_id": "vscode-copilot-bridge",
  "redirect_uri": "http://127.0.0.1:33419/",
  "verdict": "blocked",
  "classification": "passwordless_browser_not_supported",
  "artifacts": [
    "oidc_discovery.json",
    "auth_server_metadata.json",
    "browser_check.json",
    "summary.md",
    "repair.json"
  ]
}
14. Detection Responsibilities
14.1 Discovery validation

The client must validate that standard OIDC discovery is reachable and coherent.

14.2 Redirect posture validation

When a redirect URI is provided, the client must validate that it conforms to the expected loopback/public-client posture for a browser-based PKCE client.

14.3 Server capability posture

The client must determine whether the server/browser side actually supports passwordless browser continuation. This may come from:

explicit compatibility disclosure,
realm/browser-flow metadata exposed through supported discovery/config,
or a well-defined server posture signal introduced by SDK-SERVER-01-F.
14.4 Unsupported detour detection

If the environment or config points at a local proxy or token-injection path, the client must classify it as an unsupported detour rather than treating it as a legitimate integration option.

15. Failure and Repair UX

Every failure path must produce deterministic reasons and next-best actions.

15.1 PASSWORDLESS_BROWSER_NOT_SUPPORTED

Repair:

deploy server-side browser passwordless continuation,
rerun browser-check,
do not switch to proxy injection.
15.2 OIDC_DISCOVERY_UNAVAILABLE

Repair:

verify realm URL,
verify auth host reachability,
rerun check.
15.3 REDIRECT_URI_MISMATCH

Repair:

correct the client redirect configuration,
rerun browser-check.
15.4 UNSUPPORTED_DETOUR_DETECTED

Repair:

remove proxy/token-injection config,
restore direct Keyhole endpoint usage,
rerun browser-check.
15.5 BROWSER_AUTH_TIMEOUT

Repair:

capture support bundle,
confirm passwordless browser continuation support,
retry using standard browser flow.
15.6 LOOPBACK_CALLBACK_NOT_COMPLETED

Repair:

verify local callback listener behavior in the client,
verify browser completion actually resumed the original auth session.
16. Required Local Artifacts

All browser-validation and support-bundle artifacts must be tool-owned and repo-neutral.

16.1 Path
<tool-owned-state>/
  auth/
    browser/
      <bundle-or-correlation-id>/
16.2 Minimum files
auth/
  browser/
    <id>/
      oidc_discovery.json
      auth_server_metadata.json
      browser_check.json
      client_input.json
      redirect_posture.json
      detour_detection.json
      summary.md
      repair.json
16.3 Repo neutrality

These artifacts are diagnostic and auth-scoped, not repo-scoped.

17. Proof / Support Bundle Contract
17.1 Required proof content

Every browser-check and support-bundle flow must include:

realm
client_id
redirect_uri when provided
discovery posture
direct vs detour posture
passwordless browser support posture
final verdict
repair guidance
17.2 Summary expectations

summary.md must explain:

whether the client is using the standard path,
whether the server/browser flow is compatible,
whether any unsupported workaround was detected,
what the next step is.
17.3 Explainability fit

These artifacts must be suitable for ingestion into broader explainability/support-bundle workflows already present in the SDK model.

18. Interaction with Existing Stories
18.1 SDK-CLIENT-01

Still owns login/bootstrap. This story does not create a second browser-client login surface.

18.2 SDK-CLIENT-01-B

Still owns credential lifecycle and profile switching. This story validates standard browser-client compatibility.

18.3 SDK-CLIENT-01-C

Still owns doctor, host identity reconciliation, and connection truth/discovery. This story does not replace that host/session diagnosis surface.

18.4 SDK-CLIENT-01-D

Still owns host credential installation, extension reconciliation, and live principal alignment. This story does not replace host install/reconcile behavior.

18.5 SDK-CLIENT-01-E

Still owns auto-detection, MCP boundary probing, and governed mode auto-promotion. This story does not replace detection/probing posture.

18.6 SDK-CLIENT-20

Still owns explainability/support-bundle framing. This story adds a browser-auth-specific artifact set.

18.7 SDK-CLIENT-21

Still owns surface/capability negotiation. This story consumes that posture for browser compatibility and server-support validation.

18.8 SDK-CLIENT-22

Still owns CLI-side passwordless email-code login. This story does not replace it; it explains and validates browser-client compatibility with the same passwordless philosophy.

18.9 SDK-SERVER-01-F

Server story implements the actual email-first browser passwordless continuation. This client story validates, explains, and operationalizes it for standards-based browser clients.

19. Acceptance Criteria
19.1 Standard-path clarity

The client clearly documents and renders the supported browser path as OIDC Authorization Code + PKCE.

19.2 No proxy support

The client does not expose mcp-proxy or similar token-injection behavior as a supported integration path.

19.3 Browser compatibility check

Given a browser OIDC client configuration, keyhole auth browser-check can determine whether the environment is compatible, blocked, misconfigured, or using an unsupported detour.

19.4 Passwordless semantics clarity

The client clearly distinguishes the emailed verification code from the OIDC authorization code.

19.5 Direct endpoint posture

The client can validate that the environment is pointing directly at the intended Keyhole auth/MCP boundary rather than a local proxy.

19.6 Support bundle generation

Given a failed browser login, the client can generate a deterministic support bundle.

19.7 Explainability

Given a support bundle, keyhole auth explain-browser can render a concrete diagnosis and repair plan.

19.8 Repo neutrality

All artifacts are emitted outside the working repo.

19.9 No alternate auth path

This story introduces no second login protocol for browser clients.

19.10 Story-map correctness

This story preserves the already-deployed meanings of 01-D and 01-E and occupies the next free auth/browser slot as 01-F.

20. Tests
Unit
browser-check success posture,
discovery unavailable posture,
redirect mismatch posture,
unsupported detour detection,
passwordless browser posture classification,
summary/repair rendering,
support bundle emission.
Integration
standard-compatible OIDC client validates cleanly,
blocked server browser-flow posture yields blocked,
proxy/detour config yields unsupported_detour_detected,
direct config yields compatible,
explain-browser renders expected diagnosis from captured bundle.
Negative
missing realm,
invalid client id input,
invalid redirect URI,
incomplete discovery metadata,
ambiguous posture from mixed config.
21. Invariants
INV-SDK-CLIENT-01-F-001 — Standard browser path is primary
Browser OIDC clients are guided toward Authorization Code + PKCE, not alternate paths.
INV-SDK-CLIENT-01-F-002 — No proxy confusion
Unsupported proxy/token-injection detours are not presented as supported product behavior.
INV-SDK-CLIENT-01-F-003 — Verification code is named correctly
Client UX must not describe the emailed verification code as the PKCE/OIDC authorization code.
INV-SDK-CLIENT-01-F-004 — Browser validation is explicit
Compatibility with browser passwordless continuation is rendered explicitly, not assumed.
INV-SDK-CLIENT-01-F-005 — Support artifacts are deterministic
Browser auth support bundles are reproducible and repo-neutral.
INV-SDK-CLIENT-01-F-006 — No alternate auth protocol is introduced
The client story validates and explains the standard path; it does not invent a second one.
INV-SDK-CLIENT-01-F-007 — Story map remains stable
Existing 01-C, 01-D, and 01-E identities remain unchanged; browser compatibility occupies 01-F.
22. Suggested Client Modules
keyhole_sdk/auth_browser/__init__.py
keyhole_sdk/auth_browser/check.py
keyhole_sdk/auth_browser/models.py
keyhole_sdk/auth_browser/detours.py
keyhole_sdk/auth_browser/proof.py
keyhole_sdk/auth_browser/explain.py

Suggested CLI commands:

keyhole_cli/commands/auth_browser_check.py
keyhole_cli/commands/auth_browser_support_bundle.py
keyhole_cli/commands/auth_explain_browser.py
23. Dependencies / Unlocks
Depends on
SDK-CLIENT-01
SDK-CLIENT-01-B
SDK-CLIENT-01-C
SDK-CLIENT-01-D
SDK-CLIENT-01-E
SDK-CLIENT-20
SDK-CLIENT-21
SDK-CLIENT-22
SDK-SERVER-01-F
Unlocks
clean standards-based IDE/browser onboarding,
explicit rejection of proxy/token-injection detours,
easier support for browser login failures,
better agent guidance,
alignment between browser auth UX and platform doctrine.
24. Closure Criteria

This story is complete only when:

the client can validate standard browser OIDC compatibility,
unsupported proxy/detour paths are not part of the supported surface,
passwordless browser semantics are clearly explained,
browser auth support bundles are deterministic and repo-neutral,
repair guidance is concrete,
the paired server story provides the actual browser-flow capability underneath,
the current auth story map remains stable and unambiguous.
25. Agent Handoff

Implement this as a validation/support layer, not as a new auth mechanism.

