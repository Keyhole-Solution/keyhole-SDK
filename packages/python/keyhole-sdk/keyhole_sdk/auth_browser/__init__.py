"""Browser OIDC compatibility — validation, diagnostics, and support-bundle UX.

Implements SDK-CLIENT-01-F: Standard Browser OIDC Compatibility, Validation,
and Passwordless Support UX.

This package provides:
  - Browser OIDC compatibility check (Authorization Code + PKCE)
  - Unsupported detour detection (proxy / token injection paths)
  - Support bundle generation for browser auth failures
  - Explainability rendering from captured bundles
  - Repair guidance for every classified failure
"""

from keyhole_sdk.auth_browser.models import (
    BrowserCompatibilityReport,
    BrowserSupportBundleIndex,
    BrowserCheckVerdict,
    BrowserFailureClass,
    RedirectPosture,
    PkcePosture,
    PasswordlessBrowserPosture,
    DirectMcpPosture,
    RepairItem,
)
from keyhole_sdk.auth_browser.check import run_browser_check
from keyhole_sdk.auth_browser.detours import detect_unsupported_detour
from keyhole_sdk.auth_browser.proof import write_support_bundle, load_support_bundle
from keyhole_sdk.auth_browser.explain import explain_bundle

__all__ = [
    "BrowserCompatibilityReport",
    "BrowserSupportBundleIndex",
    "BrowserCheckVerdict",
    "BrowserFailureClass",
    "RedirectPosture",
    "PkcePosture",
    "PasswordlessBrowserPosture",
    "DirectMcpPosture",
    "RepairItem",
    "run_browser_check",
    "detect_unsupported_detour",
    "write_support_bundle",
    "load_support_bundle",
    "explain_bundle",
]
