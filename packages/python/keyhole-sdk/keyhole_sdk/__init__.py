"""Keyhole SDK — canonical public Python client surface.

CE-V5-S41-05: SDK Surface Contract.

Public entry points per §11:
  KeyholeClient      — synchronous client
  AsyncKeyholeClient — asynchronous client (placeholder, sync wrapper)
  KeyholeConfig      — narrow configuration object
  KeyholeError       — base exception
  AuthProvider       — pluggable auth base
"""

__version__ = "0.4.1"

# ── Core client entry points ────────────────────────────
from keyhole_sdk.client import KeyholeClient, RuntimeBridgeClient  # noqa: E402

# ── Configuration ────────────────────────────────────────
from keyhole_sdk.config import (  # noqa: E402
    KeyholeConfig,
    DEFAULT_BASE_URL,
    DEFAULT_AUTH_SERVER,
    DEFAULT_REALM,
    DEFAULT_CLIENT_ID,
)

# ── Authentication ───────────────────────────────────────
from keyhole_sdk.auth import (  # noqa: E402
    AuthProvider,
    BearerTokenProvider,
    CallbackTokenProvider,
    EnvironmentTokenProvider,
)

# ── Models ───────────────────────────────────────────────
from keyhole_sdk import models  # noqa: E402
from keyhole_sdk.models import (  # noqa: E402
    CompatibilityResult,
    CompatibilityStatus,
    PublicError,
    RealizationReceipt,
    RealizationRequest,
    RuntimeHealth,
    RuntimeIdentity,
    RuntimeState,
)

# ── Discovery ─────────────────────────────────────────────
from keyhole_sdk.discovery import (  # noqa: E402
    CapabilitiesCache,
    CapabilitiesClient,
    CapabilitiesResult,
)

# ── Context Retrieval ─────────────────────────────────────
from keyhole_sdk.context import (  # noqa: E402
    ContextClient,
    ContextSnapshot,
)

# ── Dispatch Safety ───────────────────────────────────────
from keyhole_sdk.dispatch import (  # noqa: E402
    DispatchPreflight,
    RunTypeValidator,
    SchemaHelper,
)

# ── Read-Only Smoke Path ──────────────────────────────────
from keyhole_sdk.smoke import (  # noqa: E402
    ReadOnlySmokeRunner,
    SmokeResult,
)

# ── Proof-Ready Scaffolding (CE-V5-S42-08) ────────────────
from keyhole_sdk.proof import (  # noqa: E402
    ParticipantContractPlaceholder,
    ProofBundlePlaceholder,
    SupportStatus,
    VerificationOutput,
    VerificationRunner,
)

# ── Recursive Demo Readiness (CE-V5-S42-09) ───────────────
from keyhole_sdk.demo import (  # noqa: E402
    DemoFlowRunner,
    DemoResult,
)

# ── Onboarding (SDK-CLIENT-00) ──────────────────────────────────
from keyhole_sdk.onboarding import (  # noqa: E402
    OnboardingClient,
    OnboardingProofBundle,
    OnboardingRealm,
    OnboardingState,
    RegistrationRequest,
    RegistrationResponse,
    VerificationRequest,
    VerificationResponse,
    RegistrationStatusResponse,
    OnboardingResult,
    OnboardingError,
    RegistrationRejectedError,
    VerificationFailedError,
    VerificationExpiredError,
    DuplicateRegistrationError,
    MissingClassificationError,
    OnboardingNetworkError,
)

# ── Governance Proof Protocol (RG-01) ─────────────────────
from keyhole_sdk.governance import (  # noqa: E402
    GovernancePhase,
    GovernanceProofResult,
    GovernanceProofRunner,
    GovernanceTraceBuilder,
)

# ── Exceptions ───────────────────────────────────────────
from keyhole_sdk.exceptions import (  # noqa: E402
    AuthenticationError,
    CompatibilityError,
    ContractIncompatibleError,
    DirectMemoryAccessNotAllowed,
    KeyholeSDKError,
    PublicEndpointError,
    RuntimeUnavailableError,
    SchemaError,
    TransportError,
    ValidationError as SDKValidationError,
)

# ── Transport Discipline (SDK-CLIENT-15) ──────────────────
from keyhole_sdk.transport import (  # noqa: E402
    GovernedTransport,
    TransportResult,
    OperationAttempt,
    OperationClass,
    OperationDescriptor,
    RetryPolicy,
    RetryConfig,
    ClientObservation,
    TransportProofMetadata,
    generate_idempotency_key,
    generate_request_id,
)
from keyhole_sdk.transport.errors import (  # noqa: E402
    DeferredError,
    IdempotencyConflictError,
    IdempotencyError,
    MissingIdempotencyKeyError,
    RateLimitedError,
    RetryExhaustedError,
    TransportUnknownError,
)

# Backward-compat alias
KeyholeError = KeyholeSDKError

# ── Run Dispatch (SDK-CLIENT-09) ──────────────────────────────
from keyhole_sdk.run_dispatch import (  # noqa: E402
    RunPreflight,
    PreflightFailure,
    RunRequest,
    build_run_request,
    RunOutcome,
    OutcomeStatus,
    dispatch_run,
    emit_run_proof,
    map_repair_guidance,
)

# ── Context Lifecycle (SDK-CLIENT-16) ──────────────────────────
from keyhole_sdk.context_lifecycle import (  # noqa: E402
    ContextCompileRequest,
    ContextCompileResult,
    build_compile_request,
    compile_context,
    ContextInspectResult,
    inspect_context,
    ContextPreflight,
    ContextPreflightFailure,
    emit_context_proof,
    emit_context_binding_proof,
    map_context_repair,
    validate_digest,
    LocalContextTracker,
)

# ── Run Lifecycle (SDK-CLIENT-17) ──────────────────────────────
from keyhole_sdk.run_lifecycle import (  # noqa: E402
    RunRecord,
    LocalRunRecordStore,
    RunStatus,
    TerminalState,
    RunStatusResult,
    RunWaitResult,
    RunTailEntry,
    RunTailResult,
    RunResumeResult,
    fetch_run_status,
    wait_for_terminal,
    tail_run,
    resume_run,
    emit_run_lifecycle_proof,
    map_run_lifecycle_repair,
)

# ── Repository Ingestion (SDK-CLIENT-10) ──────────────────────────
from keyhole_sdk.ingest import (  # noqa: E402
    CompatibilityPosture,
    ConfidenceLevel,
    FileClassification,
    InferredCapability,
    IngestionOutcome,
    IngestionPackage,
    IngestionRequest,
    GraphSummary,
    RepoScanResult,
    ScanSignal,
    scan_repo,
    IncludeExcludeFilter,
    DEFAULT_EXCLUDES,
    DEFAULT_INCLUDES,
    build_ingestion_package,
    submit_ingestion,
    emit_ingestion_proof,
    map_ingestion_repair,
)

# ── Repository Registration (SDK-CLIENT-07) ──────────────────────────
from keyhole_sdk.registration import (  # noqa: E402
    IdentityBinding,
    IngestionReference,
    NativeArtifacts,
    RegistrationOutcome,
    RegistrationPayload,
    RegistrationReadiness,
    RegistrationRequest,
    RegistrationSource,
    assess_readiness,
    load_native_artifacts,
    load_ingestion_reference,
    build_artifacts_snapshot,
    build_registration_payload,
    submit_registration,
    emit_registration_proof,
    map_registration_repair,
)

# ── Capability Discovery (SDK-CLIENT-08) ──────────────────────────
from keyhole_sdk.capability import (  # noqa: E402
    CapabilityCandidate,
    CapabilitySearchRequest,
    CapabilitySearchResult,
    MaterializationMode,
    RepoPosture,
    ResolutionOutcome,
    ResolutionRequest,
    ResolvedDependency,
    submit_capability_search,
    submit_resolution,
    materialize_resolution,
    emit_search_proof,
    emit_resolution_proof,
    map_capability_repair,
)

# ── Capability Namespace Enforcement (SDK-CLIENT-03) ─────────────────────────
from keyhole_sdk.capability import (  # noqa: E402
    CapabilityNameError,
    CapabilityNameParts,
    CapabilityValidationResult,
    NamespaceRejectReason,
    create_capability_name,
    emit_namespace_batch_proof,
    emit_namespace_proof,
    normalize_capability_parts,
    validate_capability_name,
)

# ── Memory Boundary Enforcement (SDK-CLIENT-18) ──────────────────────────
from keyhole_sdk.memory_boundary import (  # noqa: E402
    MEMORY_BOUNDARY_LAWFUL_ALTERNATIVES,
    MEMORY_BOUNDARY_REJECTION_MESSAGE,
    emit_memory_boundary_proof,
    get_memory_boundary_repair,
    reject_direct_memory_access,
)

# ── Alignment Guidance (SDK-CLIENT-11) ───────────────────────────────────
from keyhole_sdk.alignment import (  # noqa: E402
    AlignmentGuidanceRequest,
    AlignmentGuidanceResult,
    AlignmentReadiness,
    GuidanceClass,
    GuidanceItem,
    GuidanceSeverity,
    GuidanceState,
    render_guidance,
    submit_alignment,
    emit_alignment_proof,
    map_alignment_repair,
)

# ── Budget, Limit, and Overload Visibility (SDK-CLIENT-19) ──────────────
from keyhole_sdk.budget import (  # noqa: E402
    LimitOutcomeClass,
    BudgetSnapshot,
    LimitResult,
    BudgetPressureRequest,
    parse_limit_outcome,
    render_budget_summary,
    emit_budget_proof,
    map_budget_repair,
    is_pressure_outcome,
    classify_retry_posture,
)

# ── Governance Explainability (SDK-CLIENT-20) ────────────────────────────
from keyhole_sdk.explain import (  # noqa: E402
    ExplainOutcomeClass,
    RunExplanation,
    RequestInspectionResult,
    SupportBundle,
    assemble_run_explanation,
    assemble_request_inspection,
    assemble_support_bundle,
    render_explanation,
    render_inspection,
    emit_explain_proof,
    emit_bundle_proof,
    map_explain_repair,
)

# ── Surface Negotiation (SDK-CLIENT-21) ─────────────────────────────────
from keyhole_sdk.negotiation import (  # noqa: E402
    CompatibilitySummary,
    CommandCompatibilityResult,
    CommandStatus,
    NegotiatedFeatures,
    NegotiationResult,
    NegotiationStatus,
    SurfaceClass,
    SurfaceEntry,
    SURFACE_TAXONOMY,
    COMMAND_REQUIREMENTS,
    classify_surfaces,
    evaluate_command,
    evaluate_all_commands,
    negotiate,
    negotiate_from_raw,
    write_negotiation_artifacts,
    map_negotiation_repair,
)

# ── Account Deregistration (SDK-CLIENT-22) ──────────────────────────────
from keyhole_sdk.deregister import (  # noqa: E402
    DeregistrationClient,
    DeregistrationProofBundle,
    DeregistrationOutcome,
    DeregistrationRequest,
    DeregistrationStatus,
    DeregistrationAlreadyDeletedError,
    DeregistrationError,
    DeregistrationNetworkError,
    DeregistrationNotAuthenticatedError,
    DeregistrationOwnershipMismatchError,
    DeregistrationPolicyBlockedError,
    DeregistrationSurfaceUnavailableError,
)

# ── Doctor Discovery (SDK-CLIENT-01-C) ───────────────────────────────────
from keyhole_sdk.doctor import (  # noqa: E402
    DoctorHostEntry,
    DoctorHostRecord,
    DoctorProofBundle,
    DoctorReport,
    DoctorSummaryStatus,
    HostDiagnosis,
    HostType,
    RecommendedAction,
    RepairGuidance,
    StalenessState,
    HostDetector,
    SDKCredentialDetector,
    VSCodeHostDetector,
    detect_hosts,
    build_doctor_report,
    build_repair_guidance,
    classify_host_diagnosis,
    check_connection_surfaces_available,
    reconcile,
    CONNECTION_INSPECT_RUN_TYPE,
    CONNECTION_LINEAGE_RUN_TYPE,
    CONNECTION_STATUS_RUN_TYPE,
)

# ── Connection Identity (SDK-CLIENT-01-C) ────────────────────────────────
from keyhole_sdk.connection_identity import (  # noqa: E402
    ConnectionAuthority,
    ConnectionIdentityClient,
    ConnectionIdentityError,
    ConnectionInfo,
    ConnectionNetworkError,
    ConnectionNotAuthenticatedError,
    ConnectionNotFoundError,
    ConnectionStaleness,
    ConnectionSurfaceUnavailableError,
    InvalidateOutcome,
    InvalidateRequest,
    InvalidateStatus,
    RebindOutcome,
    RebindRejectedError,
    RebindRequest,
    RebindStatus,
    VerificationFailedError as ConnectionVerificationFailedError,
    repair_commands_for_diagnosis,
    repair_steps_for_diagnosis,
    render_connection_info,
    render_connection_list,
    render_invalidate_outcome,
    render_lineage,
    render_rebind_outcome,
)

# ── Governance Contract Validation (SDK-CLIENT-04) ───────────────────────
from keyhole_sdk.validation import (  # noqa: E402
    ContractRepoPosture,
    NormalizedDependency,
    NormalizationPreview,
    ReadinessLevel,
    ValidationIssue,
    ValidationResult,
    ValidationStatus,
    detect_foreign_manifests,
    detect_repo_posture,
    emit_validation_proof,
    map_validation_repair,
    run_validation,
    validate_capability_passport,
    validate_compatibility,
    validate_dependencies,
    validate_governance_contract,
    validate_keyhole_yaml,
)

# ── Capability Passport Generation (SDK-CLIENT-05) ───────────────────────
from keyhole_sdk.passport import (  # noqa: E402
    CapabilityEntry,
    CapabilityPassportArtifact,
    PassportGenerationResult,
    PassportIssue,
    PassportReadiness,
    PassportStatus,
    compute_passport_digest,
    emit_passport_proof,
    generate_passport,
    map_passport_repair,
    serialize_passport_for_storage,
)

__all__ = [
    # Core clients
    "KeyholeClient",
    "RuntimeBridgeClient",
    # Configuration
    "KeyholeConfig",
    # Auth
    "AuthProvider",
    "BearerTokenProvider",
    "CallbackTokenProvider",
    "EnvironmentTokenProvider",
    # Models
    "models",
    "RuntimeIdentity",
    "RuntimeHealth",
    "RuntimeState",
    "RealizationRequest",
    "RealizationReceipt",
    "CompatibilityResult",
    "CompatibilityStatus",
    "PublicError",
    # Discovery
    "CapabilitiesClient",
    "CapabilitiesResult",
    "CapabilitiesCache",
    # Context Retrieval
    "ContextClient",
    "ContextSnapshot",
    # Dispatch Safety
    "DispatchPreflight",
    "RunTypeValidator",
    "SchemaHelper",
    # Read-Only Smoke Path
    "ReadOnlySmokeRunner",
    "SmokeResult",
    # Proof-Ready Scaffolding (CE-V5-S42-08)
    "ParticipantContractPlaceholder",
    "ProofBundlePlaceholder",
    "SupportStatus",
    "VerificationOutput",
    "VerificationRunner",
    # Recursive Demo Readiness (CE-V5-S42-09)
    "DemoFlowRunner",
    "DemoResult",
    # Onboarding (SDK-CLIENT-00)
    "OnboardingClient",
    "OnboardingProofBundle",
    "OnboardingRealm",
    "OnboardingState",
    "RegistrationRequest",
    "RegistrationResponse",
    "VerificationRequest",
    "VerificationResponse",
    "RegistrationStatusResponse",
    "OnboardingResult",
    "OnboardingError",
    "RegistrationRejectedError",
    "VerificationFailedError",
    "VerificationExpiredError",
    "DuplicateRegistrationError",
    "MissingClassificationError",
    "OnboardingNetworkError",
    # Governance Proof Protocol (RG-01)
    "GovernancePhase",
    "GovernanceProofResult",
    "GovernanceProofRunner",
    "GovernanceTraceBuilder",
    # Exceptions
    "KeyholeSDKError",
    "KeyholeError",
    "TransportError",
    "RuntimeUnavailableError",
    "SchemaError",
    "CompatibilityError",
    "PublicEndpointError",
    "AuthenticationError",
    "ContractIncompatibleError",
    "SDKValidationError",
    # Transport Discipline (SDK-CLIENT-15)
    "GovernedTransport",
    "TransportResult",
    "OperationAttempt",
    "OperationClass",
    "OperationDescriptor",
    "RetryPolicy",
    "RetryConfig",
    "ClientObservation",
    "TransportProofMetadata",
    "generate_idempotency_key",
    "generate_request_id",
    "IdempotencyError",
    "MissingIdempotencyKeyError",
    "IdempotencyConflictError",
    "RetryExhaustedError",
    "DeferredError",
    "TransportUnknownError",
    "RateLimitedError",
    # Run Dispatch (SDK-CLIENT-09)
    "RunPreflight",
    "PreflightFailure",
    "RunRequest",
    "build_run_request",
    "RunOutcome",
    "OutcomeStatus",
    "dispatch_run",
    "emit_run_proof",
    "map_repair_guidance",
    # Context Lifecycle (SDK-CLIENT-16)
    "ContextCompileRequest",
    "ContextCompileResult",
    "build_compile_request",
    "compile_context",
    "ContextInspectResult",
    "inspect_context",
    "ContextPreflight",
    "ContextPreflightFailure",
    "emit_context_proof",
    "emit_context_binding_proof",
    "map_context_repair",
    "validate_digest",
    "LocalContextTracker",
    # Run Lifecycle (SDK-CLIENT-17)
    "RunRecord",
    "LocalRunRecordStore",
    "RunStatus",
    "TerminalState",
    "RunStatusResult",
    "RunWaitResult",
    "RunTailEntry",
    "RunTailResult",
    "RunResumeResult",
    "fetch_run_status",
    "wait_for_terminal",
    "tail_run",
    "resume_run",
    "emit_run_lifecycle_proof",
    "map_run_lifecycle_repair",
    # Repository Ingestion (SDK-CLIENT-10)
    "CompatibilityPosture",
    "ConfidenceLevel",
    "FileClassification",
    "InferredCapability",
    "IngestionOutcome",
    "IngestionPackage",
    "IngestionRequest",
    "GraphSummary",
    "RepoScanResult",
    "ScanSignal",
    "scan_repo",
    "IncludeExcludeFilter",
    "DEFAULT_EXCLUDES",
    "DEFAULT_INCLUDES",
    "build_ingestion_package",
    "submit_ingestion",
    "emit_ingestion_proof",
    "map_ingestion_repair",
    # Repository Registration (SDK-CLIENT-07)
    "IdentityBinding",
    "IngestionReference",
    "NativeArtifacts",
    "RegistrationOutcome",
    "RegistrationPayload",
    "RegistrationReadiness",
    "RegistrationRequest",
    "RegistrationSource",
    "assess_readiness",
    "load_native_artifacts",
    "load_ingestion_reference",
    "build_artifacts_snapshot",
    "build_registration_payload",
    "submit_registration",
    "emit_registration_proof",
    "map_registration_repair",
    # Capability Discovery (SDK-CLIENT-08)
    "CapabilityCandidate",
    "CapabilitySearchRequest",
    "CapabilitySearchResult",
    "MaterializationMode",
    "RepoPosture",
    "ResolutionOutcome",
    "ResolutionRequest",
    "ResolvedDependency",
    "submit_capability_search",
    "submit_resolution",
    "materialize_resolution",
    "emit_search_proof",
    "emit_resolution_proof",
    "map_capability_repair",
    # Capability Namespace Enforcement (SDK-CLIENT-03)
    "CapabilityNameError",
    "CapabilityNameParts",
    "CapabilityValidationResult",
    "NamespaceRejectReason",
    "create_capability_name",
    "emit_namespace_batch_proof",
    "emit_namespace_proof",
    "normalize_capability_parts",
    "validate_capability_name",
    # Memory Boundary Enforcement (SDK-CLIENT-18)
    "DirectMemoryAccessNotAllowed",
    "MEMORY_BOUNDARY_LAWFUL_ALTERNATIVES",
    "MEMORY_BOUNDARY_REJECTION_MESSAGE",
    "emit_memory_boundary_proof",
    "get_memory_boundary_repair",
    "reject_direct_memory_access",
    # Alignment Guidance (SDK-CLIENT-11)
    "AlignmentGuidanceRequest",
    "AlignmentGuidanceResult",
    "AlignmentReadiness",
    "GuidanceClass",
    "GuidanceItem",
    "GuidanceSeverity",
    "GuidanceState",
    "render_guidance",
    "submit_alignment",
    "emit_alignment_proof",
    "map_alignment_repair",
    # Budget, Limit, and Overload Visibility (SDK-CLIENT-19)
    "LimitOutcomeClass",
    "BudgetSnapshot",
    "LimitResult",
    "BudgetPressureRequest",
    "parse_limit_outcome",
    "render_budget_summary",
    "emit_budget_proof",
    "map_budget_repair",
    "is_pressure_outcome",
    "classify_retry_posture",
    # Governance Explainability (SDK-CLIENT-20)
    "ExplainOutcomeClass",
    "RunExplanation",
    "RequestInspectionResult",
    "SupportBundle",
    "assemble_run_explanation",
    "assemble_request_inspection",
    "assemble_support_bundle",
    "render_explanation",
    "render_inspection",
    "emit_explain_proof",
    "emit_bundle_proof",
    "map_explain_repair",
    # Surface Negotiation (SDK-CLIENT-21)
    "CompatibilitySummary",
    "CommandCompatibilityResult",
    "CommandStatus",
    "NegotiatedFeatures",
    "NegotiationResult",
    "NegotiationStatus",
    "SurfaceClass",
    "SurfaceEntry",
    "SURFACE_TAXONOMY",
    "COMMAND_REQUIREMENTS",
    "classify_surfaces",
    "evaluate_command",
    "evaluate_all_commands",
    "negotiate",
    "negotiate_from_raw",
    "write_negotiation_artifacts",
    "map_negotiation_repair",
    # Account Deregistration (SDK-CLIENT-22)
    "DeregistrationClient",
    "DeregistrationProofBundle",
    "DeregistrationOutcome",
    "DeregistrationRequest",
    "DeregistrationStatus",
    "DeregistrationAlreadyDeletedError",
    "DeregistrationError",
    "DeregistrationNetworkError",
    "DeregistrationNotAuthenticatedError",
    "DeregistrationOwnershipMismatchError",
    "DeregistrationPolicyBlockedError",
    "DeregistrationSurfaceUnavailableError",
    # Doctor Discovery (SDK-CLIENT-01-C)
    "DoctorHostEntry",
    "DoctorHostRecord",
    "DoctorProofBundle",
    "DoctorReport",
    "DoctorSummaryStatus",
    "HostDiagnosis",
    "HostType",
    "RecommendedAction",
    "RepairGuidance",
    "StalenessState",
    "HostDetector",
    "SDKCredentialDetector",
    "VSCodeHostDetector",
    "detect_hosts",
    "build_doctor_report",
    "build_repair_guidance",
    "classify_host_diagnosis",
    "check_connection_surfaces_available",
    "reconcile",
    "CONNECTION_INSPECT_RUN_TYPE",
    "CONNECTION_LINEAGE_RUN_TYPE",
    "CONNECTION_STATUS_RUN_TYPE",
    # Connection Identity (SDK-CLIENT-01-C)
    "ConnectionAuthority",
    "ConnectionIdentityClient",
    "ConnectionIdentityError",
    "ConnectionInfo",
    "ConnectionNetworkError",
    "ConnectionNotAuthenticatedError",
    "ConnectionNotFoundError",
    "ConnectionStaleness",
    "ConnectionSurfaceUnavailableError",
    "InvalidateOutcome",
    "InvalidateRequest",
    "InvalidateStatus",
    "RebindOutcome",
    "RebindRejectedError",
    "RebindRequest",
    "RebindStatus",
    "ConnectionVerificationFailedError",
    "repair_commands_for_diagnosis",
    "repair_steps_for_diagnosis",
    "render_connection_info",
    "render_connection_list",
    "render_invalidate_outcome",
    "render_lineage",
    "render_rebind_outcome",
    # Governance Contract Validation (SDK-CLIENT-04)
    "ValidationStatus",
    "ContractRepoPosture",
    "ReadinessLevel",
    "ValidationIssue",
    "NormalizedDependency",
    "NormalizationPreview",
    "ValidationResult",
    "detect_repo_posture",
    "detect_foreign_manifests",
    "validate_keyhole_yaml",
    "validate_governance_contract",
    "validate_capability_passport",
    "validate_dependencies",
    "validate_compatibility",
    "run_validation",
    "map_validation_repair",
    "emit_validation_proof",
    # Capability Passport Generation (SDK-CLIENT-05)
    "PassportStatus",
    "PassportReadiness",
    "CapabilityEntry",
    "CapabilityPassportArtifact",
    "PassportIssue",
    "PassportGenerationResult",
    "compute_passport_digest",
    "serialize_passport_for_storage",
    "generate_passport",
    "map_passport_repair",
    "emit_passport_proof",
]
