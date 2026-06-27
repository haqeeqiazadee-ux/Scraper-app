from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _dedupe_env_names(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        name = str(value).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        deduped.append(name)
    return tuple(deduped)


class ActorRunState(StrEnum):
    READY = "ready"
    SKIPPED_MISSING_KEY = "skipped_missing_key"
    BLOCKED_POLICY = "blocked_policy"
    PROVIDER_DEGRADED = "provider_degraded"
    FAILED = "failed"
    SUCCEEDED = "succeeded"


class KnowledgeDecision(StrEnum):
    RUN_FRESH = "run_fresh"
    SERVE_CACHED = "serve_cached"
    SERVE_CACHED_AND_REFRESH = "serve_cached_and_refresh"
    PARTIAL_REFRESH = "partial_refresh"


class KnowledgeFreshnessState(StrEnum):
    MISSING = "missing"
    FRESH = "fresh"
    STALE = "stale"
    EXPIRED = "expired"
    BLOCKED = "blocked"
    PARTIAL = "partial"


class KnowledgeSource(StrEnum):
    DATABASE = "database"
    GRAPH = "graph"
    OBSIDIAN = "obsidian"
    VECTOR = "vector"
    CACHE = "cache"


class ProviderTier(StrEnum):
    OFFICIAL_PUBLIC_API = "official_public_api"
    PROVIDER_SDK = "provider_sdk"
    INTERNAL_CONNECTOR = "internal_connector"
    HTTP_EXTRACTION = "http_extraction"
    BROWSER_UNBLOCKER = "browser_unblocker"
    AUTHENTICATED_SESSION = "authenticated_session"
    UNSUPPORTED = "unsupported"


class ProviderStep(BaseModel):
    name: str
    tier: ProviderTier = ProviderTier.INTERNAL_CONNECTOR
    required_env_names: tuple[str, ...] = Field(default_factory=tuple)
    optional_env_names: tuple[str, ...] = Field(default_factory=tuple)
    priority: int = 100
    connector: str | None = None
    rationale: str = ""

    @field_validator("required_env_names", "optional_env_names", mode="before")
    @classmethod
    def _normalize_env_names(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        return _dedupe_env_names(tuple(value))

    @field_validator("rationale", mode="before")
    @classmethod
    def _normalize_rationale(cls, value: Any) -> str:
        return "" if value is None else str(value).strip()


class ActorSpec(BaseModel):
    actor_id: str
    slug: str
    title: str
    base_family: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    required_env_names: tuple[str, ...] = Field(default_factory=tuple)
    optional_env_names: tuple[str, ...] = Field(default_factory=tuple)
    provider_chain: tuple[ProviderStep, ...] = Field(default_factory=tuple)
    default_limits: dict[str, Any] = Field(default_factory=dict)
    credit_policy: dict[str, Any] = Field(default_factory=dict)
    skip_policy: str = "skip_missing_key"
    compliance_notes: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("required_env_names", "optional_env_names", mode="before")
    @classmethod
    def _normalize_env_names(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        return _dedupe_env_names(tuple(value))

    @field_validator("provider_chain", mode="before")
    @classmethod
    def _normalize_provider_chain(cls, value: Any) -> tuple[ProviderStep, ...]:
        if value is None:
            return ()
        return tuple(value)

    @field_validator("compliance_notes", mode="before")
    @classmethod
    def _normalize_notes(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        return tuple(str(item) for item in value)


class FreshnessPolicy(BaseModel):
    fresh_ttl_seconds: int = 3600
    stale_ttl_seconds: int = 86400
    high_volatility_ttl_seconds: int = 900
    minimum_ttl_seconds: int = 60
    maximum_ttl_seconds: int = 604800
    allow_stale_while_revalidate: bool = True
    allow_partial_field_refresh: bool = True
    min_confidence: float = 0.7
    tenant_isolation_required: bool = True
    high_volatility_families: tuple[str, ...] = (
        "marketplace_product_catalog",
        "local_maps_serp",
        "review_monitoring_generic",
    )

    @field_validator(
        "fresh_ttl_seconds",
        "stale_ttl_seconds",
        "high_volatility_ttl_seconds",
        "minimum_ttl_seconds",
        "maximum_ttl_seconds",
        mode="before",
    )
    @classmethod
    def _normalize_seconds(cls, value: Any) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = 0
        return max(parsed, 0)

    @field_validator("high_volatility_families", mode="before")
    @classmethod
    def _normalize_family_names(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            return (value.strip(),) if value.strip() else ()
        return tuple(str(item).strip() for item in value if str(item).strip())

    @field_validator("min_confidence", mode="before")
    @classmethod
    def _normalize_confidence(cls, value: Any) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            parsed = 0.0
        return min(max(parsed, 0.0), 1.0)

    @model_validator(mode="after")
    def _normalize_ttl_bounds(self) -> "FreshnessPolicy":
        if self.maximum_ttl_seconds < self.minimum_ttl_seconds:
            self.maximum_ttl_seconds = self.minimum_ttl_seconds
        self.fresh_ttl_seconds = self._clamp_ttl(self.fresh_ttl_seconds)
        self.stale_ttl_seconds = max(self._clamp_ttl(self.stale_ttl_seconds), self.fresh_ttl_seconds)
        self.high_volatility_ttl_seconds = self._clamp_ttl(self.high_volatility_ttl_seconds)
        return self

    def _clamp_ttl(self, seconds: int) -> int:
        return min(max(seconds, self.minimum_ttl_seconds), self.maximum_ttl_seconds)

    def ttl_for_family(self, base_family: str) -> int:
        if base_family in self.high_volatility_families:
            return min(self.fresh_ttl_seconds, self.high_volatility_ttl_seconds)
        return self.fresh_ttl_seconds


class GraphTraversalBudget(BaseModel):
    depth: int
    nodes: int
    edges: int
    truncated: bool
    cycle_strategy: str = "collapse_scc"


class GraphTraversalPolicy(BaseModel):
    max_depth: int = 3
    max_nodes: int = 500
    max_edges: int = 1500
    collapse_strongly_connected_components: bool = True

    @field_validator("max_depth", "max_nodes", "max_edges", mode="before")
    @classmethod
    def _normalize_positive_int(cls, value: Any) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = 1
        return max(parsed, 1)

    def bound_request(
        self,
        *,
        requested_depth: int | None = None,
        requested_nodes: int | None = None,
        requested_edges: int | None = None,
    ) -> GraphTraversalBudget:
        raw_depth = self.max_depth if requested_depth is None else int(requested_depth)
        raw_nodes = self.max_nodes if requested_nodes is None else int(requested_nodes)
        raw_edges = self.max_edges if requested_edges is None else int(requested_edges)
        depth = min(max(raw_depth, 1), self.max_depth)
        nodes = min(max(raw_nodes, 1), self.max_nodes)
        edges = min(max(raw_edges, 1), self.max_edges)
        return GraphTraversalBudget(
            depth=depth,
            nodes=nodes,
            edges=edges,
            truncated=depth != raw_depth or nodes != raw_nodes or edges != raw_edges,
            cycle_strategy="collapse_scc" if self.collapse_strongly_connected_components else "stop_on_cycle",
        )


class KnowledgeRuntimeContext(BaseModel):
    actor_id: str
    tenant_id: str
    query_fingerprint: str
    requested_fields: tuple[str, ...] = Field(default_factory=tuple)
    now: datetime = Field(default_factory=_utc_now)
    force_fresh: bool = False

    @field_validator("requested_fields", mode="before")
    @classmethod
    def _normalize_requested_fields(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            return (value.strip(),) if value.strip() else ()
        return tuple(str(item).strip() for item in value if str(item).strip())


class KnowledgeSnapshot(BaseModel):
    actor_id: str
    tenant_id: str
    query_fingerprint: str
    output: dict[str, Any] = Field(default_factory=dict)
    source: KnowledgeSource = KnowledgeSource.CACHE
    observed_at: datetime = Field(default_factory=_utc_now)
    expires_at: datetime | None = None
    provenance: tuple[str, ...] = Field(default_factory=tuple)
    field_coverage: dict[str, bool] = Field(default_factory=dict)
    confidence: float = 1.0

    @field_validator("provenance", mode="before")
    @classmethod
    def _normalize_provenance(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            return (value.strip(),) if value.strip() else ()
        return tuple(str(item).strip() for item in value if str(item).strip())

    @field_validator("confidence", mode="before")
    @classmethod
    def _normalize_confidence(cls, value: Any) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            parsed = 0.0
        return min(max(parsed, 0.0), 1.0)


class KnowledgeRuntimeDecisionResult(BaseModel):
    decision: KnowledgeDecision
    freshness_state: KnowledgeFreshnessState
    reason: str
    source: KnowledgeSource | None = None
    age_seconds: int | None = None
    reusable_output: dict[str, Any] = Field(default_factory=dict)
    refresh_fields: tuple[str, ...] = Field(default_factory=tuple)
    evidence: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("refresh_fields", "evidence", mode="before")
    @classmethod
    def _normalize_tuple(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            return (value.strip(),) if value.strip() else ()
        return tuple(str(item).strip() for item in value if str(item).strip())


class ActorRuntimeTrace(BaseModel):
    trace_id: str
    actor_id: str
    base_family: str
    decision: str
    provider: str | None = None
    events: tuple[str, ...] = Field(default_factory=tuple)


class ActorSecurityAssessment(BaseModel):
    allowed: bool = True
    redacted_payload_keys: tuple[str, ...] = Field(default_factory=tuple)
    risk_flags: tuple[str, ...] = Field(default_factory=tuple)


class ActorCostEstimate(BaseModel):
    estimated_usd: float = 0.0
    estimated_credits: int = 0
    saved_by_knowledge_usd: float = 0.0
    pricing_basis: str = "actor_runtime_estimate"


class ActorQualityEval(BaseModel):
    passed: bool
    score: float
    item_count: int = 0
    confidence: float = 0.0
    missing_required_fields: tuple[str, ...] = Field(default_factory=tuple)


class RequirementCheck(BaseModel):
    state: ActorRunState
    missing_env_names: tuple[str, ...] = Field(default_factory=tuple)
    available_env_names: tuple[str, ...] = Field(default_factory=tuple)
    provider: str | None = None

    @property
    def is_ready(self) -> bool:
        return self.state == ActorRunState.READY


class ActorRuntimeResult(BaseModel):
    actor_id: str
    state: ActorRunState
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    missing_env_names: tuple[str, ...] = Field(default_factory=tuple)
    provider: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
