"""Authentication bootstrap — OIDC/PKCE and device flow client support.

Implements SDK-CLIENT-01: Authentication Bootstrap (Client).

This package provides:
  - PKCE auth flow initiation and completion
  - Device/constrained auth flow support
  - Secure local credential store
  - Whoami identity inspection
  - Proof bundle contribution for auth zipper
"""

from keyhole_sdk.auth_bootstrap.actor_envelope import (
    ActingPrincipal,
    ActorEnvelope,
    Authorization,
    Delegation,
    HumanPrincipal,
)
from keyhole_sdk.auth_bootstrap.models import (
    AuthFlowType,
    AuthMode,
    AuthSession,
    DeviceCodeResponse,
    LoginResult,
    PKCEChallenge,
    WhoamiResponse,
)
from keyhole_sdk.auth_bootstrap.credential_store import CredentialStore
from keyhole_sdk.auth_bootstrap.pkce import PKCEFlow
from keyhole_sdk.auth_bootstrap.device import DeviceFlow
from keyhole_sdk.auth_bootstrap.passwordless import PasswordlessFlow
from keyhole_sdk.auth_bootstrap.client import AuthBootstrapClient
from keyhole_sdk.auth_bootstrap.whoami import WhoamiClient
from keyhole_sdk.auth_bootstrap.proof import AuthProofBundle

__all__ = [
    "ActingPrincipal",
    "ActorEnvelope",
    "Authorization",
    "AuthFlowType",
    "AuthMode",
    "AuthSession",
    "Delegation",
    "DeviceCodeResponse",
    "HumanPrincipal",
    "LoginResult",
    "PKCEChallenge",
    "WhoamiResponse",
    "CredentialStore",
    "PKCEFlow",
    "DeviceFlow",
    "PasswordlessFlow",
    "AuthBootstrapClient",
    "WhoamiClient",
    "AuthProofBundle",
]
