"""Live capability operation normalization and alias resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


class AmbiguousOperationAliasError(ValueError):
    """Raised when a live capability alias resolves to multiple operations."""


@dataclass
class OperationDefinition:
    """Normalized operation definition from the live capability contract."""

    operation_name: str
    canonical_run_type: str
    aliases: List[str] = field(default_factory=list)
    status: str = ""
    method: str = ""
    path: str = ""
    canonical_endpoint: Dict[str, Any] = field(default_factory=dict)
    governed: bool = False
    event_spine_evidence: bool = False
    required_authorization: Dict[str, Any] = field(default_factory=dict)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    capability_metadata: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    def identifiers(self) -> List[str]:
        seen: set[str] = set()
        values: List[str] = []
        for value in [self.operation_name, self.canonical_run_type, *self.aliases]:
            if value and value not in seen:
                seen.add(value)
                values.append(value)
        return values

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation_name": self.operation_name,
            "canonical_run_type": self.canonical_run_type,
            "aliases": list(self.aliases),
            "status": self.status,
            "method": self.method,
            "path": self.path,
            "canonical_endpoint": dict(self.canonical_endpoint),
            "governed": self.governed,
            "event_spine_evidence": self.event_spine_evidence,
            "required_authorization": dict(self.required_authorization),
            "input_schema": dict(self.input_schema),
            "output_schema": dict(self.output_schema),
            "capability_metadata": dict(self.capability_metadata),
            "raw": dict(self.raw),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OperationDefinition":
        return cls(
            operation_name=str(data.get("operation_name") or ""),
            canonical_run_type=str(data.get("canonical_run_type") or ""),
            aliases=[str(item) for item in data.get("aliases", []) if isinstance(item, str)],
            status=str(data.get("status") or ""),
            method=str(data.get("method") or ""),
            path=str(data.get("path") or ""),
            canonical_endpoint=_safe_dict(data.get("canonical_endpoint")),
            governed=bool(data.get("governed")),
            event_spine_evidence=bool(data.get("event_spine_evidence")),
            required_authorization=_safe_dict(data.get("required_authorization")),
            input_schema=_safe_dict(data.get("input_schema")),
            output_schema=_safe_dict(data.get("output_schema")),
            capability_metadata=_safe_dict(data.get("capability_metadata")),
            raw=_safe_dict(data.get("raw")),
        )


class DiscoveredOperationRegistry:
    """Indexes live operations by operation name, canonical run type, and aliases."""

    def __init__(self, operations: Iterable[OperationDefinition] = ()) -> None:
        self._operations: List[OperationDefinition] = list(operations)
        self._by_identifier: Dict[str, OperationDefinition] = {}
        self._build_indexes()

    @classmethod
    def from_capabilities(cls, capabilities_result: object) -> "DiscoveredOperationRegistry":
        raw_operations = getattr(capabilities_result, "operations", []) or []
        operations: List[OperationDefinition] = []
        for item in raw_operations:
            if isinstance(item, OperationDefinition):
                if item.canonical_run_type:
                    operations.append(item)
            elif isinstance(item, dict):
                operation = OperationDefinition.from_dict(item)
                if operation.canonical_run_type:
                    operations.append(operation)
        return cls(operations)

    def _build_indexes(self) -> None:
        for operation in self._operations:
            for identifier in operation.identifiers():
                existing = self._by_identifier.get(identifier)
                if existing is not None and existing is not operation:
                    raise AmbiguousOperationAliasError(
                        f"Identifier {identifier!r} is advertised by both "
                        f"{existing.operation_name!r} and {operation.operation_name!r}."
                    )
                self._by_identifier[identifier] = operation

    def resolve(self, identifier: str) -> Optional[OperationDefinition]:
        return self._by_identifier.get((identifier or "").strip())

    def all_operations(self) -> List[OperationDefinition]:
        return list(self._operations)

    def all_identifiers(self) -> List[str]:
        return sorted(self._by_identifier)


def normalize_operations_from_capabilities(raw: Dict[str, Any]) -> List[OperationDefinition]:
    """Normalize live capability operations without inventing missing fields."""
    body = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    operations = body.get("operations", []) if isinstance(body, dict) else []
    normalized: List[OperationDefinition] = []

    if isinstance(operations, dict):
        for name, spec in operations.items():
            if isinstance(spec, dict):
                normalized.append(_normalize_operation_dict(str(name), spec))
            elif spec:
                normalized.append(OperationDefinition(operation_name=str(name), canonical_run_type=str(name)))
    elif isinstance(operations, list):
        for item in operations:
            if isinstance(item, str):
                normalized.append(OperationDefinition(operation_name=item, canonical_run_type=item))
            elif isinstance(item, dict):
                normalized.append(_normalize_operation_dict("", item))

    return normalized


def _normalize_operation_dict(name_hint: str, item: Dict[str, Any]) -> OperationDefinition:
    operation_name = str(
        item.get("operation_name")
        or item.get("operation_id")
        or item.get("name")
        or item.get("operation")
        or name_hint
        or ""
    )
    canonical_run_type = str(
        item.get("canonical_run_type")
        or item.get("run_type")
        or item.get("canonical")
        or ""
    )
    aliases = [
        str(alias)
        for alias in item.get("aliases", [])
        if isinstance(alias, str) and alias
    ]
    canonical_endpoint = _safe_dict(item.get("canonical_endpoint"))
    method = str(item.get("method") or canonical_endpoint.get("method") or "")
    path = str(item.get("path") or canonical_endpoint.get("path") or "")
    return OperationDefinition(
        operation_name=operation_name,
        canonical_run_type=canonical_run_type,
        aliases=aliases,
        status=str(item.get("status") or ""),
        method=method.upper() if method else "",
        path=path,
        canonical_endpoint=canonical_endpoint,
        governed=bool(item.get("governed")),
        event_spine_evidence=bool(item.get("event_spine_evidence")),
        required_authorization=(
            _safe_dict(item.get("required_authorization"))
            or _safe_dict(item.get("authorization"))
            or _safe_dict(item.get("auth"))
        ),
        input_schema=_safe_dict(item.get("input_schema")),
        output_schema=_safe_dict(item.get("output_schema")),
        capability_metadata=(
            _safe_dict(item.get("capability"))
            or _safe_dict(item.get("metadata"))
        ),
        raw=dict(item),
    )


def _safe_dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}
