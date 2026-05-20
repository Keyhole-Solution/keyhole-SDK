"""Actor envelope DTOs — SDK-CLIENT-29.

Lightweight client-side data transfer objects for parsing the
``actor_envelope`` returned by ``GET /mcp/v1/whoami`` and stamped on
governed-run responses by SDK-SERVER-29.

These models are **DTOs only**.  They contain no authorization logic,
no decoding of JWTs, and no inference of identity.  The MCP server is
the sole authority for actor truth; the client merely parses what the
server returns.

Unknown fields are preserved (``model_config["extra"] = "allow"``) so
that future server fields surface as raw dict access without breaking
old SDK builds.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class HumanPrincipal(BaseModel):
    """Human (kh-prod) principal resolved by the MCP boundary."""

    model_config = ConfigDict(extra="allow")

    realm: Optional[str] = None
    subject_id: Optional[str] = None
    tenant_id: Optional[str] = None
    org_id: Optional[str] = None
    display_name: Optional[str] = None


class ActingPrincipal(BaseModel):
    """Acting (keyhole-mcp) principal — the CLI/agent/worker invoking the call."""

    model_config = ConfigDict(extra="allow")

    realm: Optional[str] = None
    client_id: Optional[str] = None
    kind: Optional[str] = None
    subject_id: Optional[str] = None


class Delegation(BaseModel):
    """Delegation posture between acting and human principals."""

    model_config = ConfigDict(extra="allow")

    kind: Optional[str] = None
    assurance: Optional[str] = None


class Authorization(BaseModel):
    """Effective authorization resolved by the MCP boundary."""

    model_config = ConfigDict(extra="allow")

    effective_scopes: List[str] = Field(default_factory=list)
    tool_grants: List[str] = Field(default_factory=list)


class ActorEnvelope(BaseModel):
    """Sanitized actor envelope returned by MCP /whoami and run responses.

    The client never constructs an ActorEnvelope from local state. It is
    populated only from server responses. All fields are optional so that
    pre-SDK-SERVER-29 servers (which return no envelope) and future server
    revisions both deserialize without error.
    """

    model_config = ConfigDict(extra="allow")

    human_principal: Optional[HumanPrincipal] = None
    acting_principal: Optional[ActingPrincipal] = None
    delegation: Optional[Delegation] = None
    authorization: Optional[Authorization] = None

    @classmethod
    def from_payload(cls, payload: Any) -> Optional["ActorEnvelope"]:
        """Parse an actor envelope from a server response payload.

        Returns ``None`` when the payload is missing or not a dict, so
        that callers can clearly distinguish "no envelope returned" from
        "empty envelope returned".
        """
        if not isinstance(payload, dict):
            return None
        return cls.model_validate(payload)

    def safe_summary(self) -> Dict[str, Any]:
        """Return a redaction-safe summary suitable for proof artifacts."""
        return {
            "human_principal": self.human_principal.model_dump() if self.human_principal else None,
            "acting_principal": self.acting_principal.model_dump() if self.acting_principal else None,
            "delegation": self.delegation.model_dump() if self.delegation else None,
            "authorization": self.authorization.model_dump() if self.authorization else None,
        }
