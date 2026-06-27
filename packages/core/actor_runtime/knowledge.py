from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Protocol

from packages.core.actor_runtime.models import (
    ActorRuntimeResult,
    ActorSpec,
    FreshnessPolicy,
    KnowledgeDecision,
    KnowledgeFreshnessState,
    KnowledgeRuntimeContext,
    KnowledgeRuntimeDecisionResult,
    KnowledgeSnapshot,
)


SENSITIVE_PAYLOAD_KEYS = {
    "api_key",
    "authorization",
    "cookies",
    "password",
    "secret",
    "token",
}


class KnowledgeMemoryStore(Protocol):
    def lookup(
        self,
        *,
        spec: ActorSpec,
        payload: Mapping[str, Any],
        context: KnowledgeRuntimeContext,
    ) -> KnowledgeSnapshot | None:
        ...

    def record(
        self,
        *,
        spec: ActorSpec,
        payload: Mapping[str, Any],
        context: KnowledgeRuntimeContext,
        result: ActorRuntimeResult,
    ) -> None:
        ...


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def build_query_fingerprint(actor_id: str, payload: Mapping[str, Any]) -> str:
    redacted_payload = {
        str(key): value
        for key, value in payload.items()
        if str(key).lower() not in SENSITIVE_PAYLOAD_KEYS and str(key) != "knowledge_context"
    }
    encoded = json.dumps({"actor_id": actor_id, "payload": redacted_payload}, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_knowledge_context(
    spec: ActorSpec,
    payload: Mapping[str, Any],
    *,
    tenant_id: str | None = None,
) -> KnowledgeRuntimeContext:
    raw_context = payload.get("knowledge_context")
    context_payload = raw_context if isinstance(raw_context, Mapping) else {}
    resolved_tenant_id = str(
        context_payload.get("tenant_id")
        or payload.get("tenant_id")
        or tenant_id
        or "default"
    )
    query_fingerprint = str(
        context_payload.get("query_fingerprint")
        or payload.get("query_fingerprint")
        or build_query_fingerprint(spec.actor_id, payload)
    )
    requested_fields = context_payload.get("requested_fields") or payload.get("requested_fields") or ()
    if isinstance(requested_fields, str):
        requested_fields = (requested_fields,)
    return KnowledgeRuntimeContext(
        actor_id=spec.actor_id,
        tenant_id=resolved_tenant_id,
        query_fingerprint=query_fingerprint,
        requested_fields=tuple(requested_fields),
        force_fresh=bool(context_payload.get("force_fresh") or payload.get("force_fresh")),
    )


class KnowledgeFreshnessEvaluator:
    def __init__(self, policy: FreshnessPolicy | None = None) -> None:
        self.policy = policy or FreshnessPolicy()

    def evaluate(
        self,
        *,
        spec: ActorSpec,
        context: KnowledgeRuntimeContext,
        snapshot: KnowledgeSnapshot | None,
    ) -> KnowledgeRuntimeDecisionResult:
        if context.force_fresh:
            return KnowledgeRuntimeDecisionResult(
                decision=KnowledgeDecision.RUN_FRESH,
                freshness_state=KnowledgeFreshnessState.BLOCKED,
                reason="force_fresh_requested",
            )
        if snapshot is None:
            return KnowledgeRuntimeDecisionResult(
                decision=KnowledgeDecision.RUN_FRESH,
                freshness_state=KnowledgeFreshnessState.MISSING,
                reason="knowledge_snapshot_missing",
            )
        if snapshot.actor_id != spec.actor_id or snapshot.query_fingerprint != context.query_fingerprint:
            return KnowledgeRuntimeDecisionResult(
                decision=KnowledgeDecision.RUN_FRESH,
                freshness_state=KnowledgeFreshnessState.BLOCKED,
                reason="knowledge_identity_mismatch",
                source=snapshot.source,
            )
        if self.policy.tenant_isolation_required and snapshot.tenant_id != context.tenant_id:
            return KnowledgeRuntimeDecisionResult(
                decision=KnowledgeDecision.RUN_FRESH,
                freshness_state=KnowledgeFreshnessState.BLOCKED,
                reason="tenant_isolation_mismatch",
                source=snapshot.source,
            )
        if not snapshot.provenance:
            return KnowledgeRuntimeDecisionResult(
                decision=KnowledgeDecision.RUN_FRESH,
                freshness_state=KnowledgeFreshnessState.BLOCKED,
                reason="missing_provenance",
                source=snapshot.source,
            )
        if snapshot.confidence < self.policy.min_confidence:
            return KnowledgeRuntimeDecisionResult(
                decision=KnowledgeDecision.RUN_FRESH,
                freshness_state=KnowledgeFreshnessState.BLOCKED,
                reason="confidence_below_policy_floor",
                source=snapshot.source,
                evidence=snapshot.provenance,
            )

        now = _aware_utc(context.now)
        observed_at = _aware_utc(snapshot.observed_at)
        age_seconds = max(int((now - observed_at).total_seconds()), 0)
        if snapshot.expires_at is not None and _aware_utc(snapshot.expires_at) <= now:
            return KnowledgeRuntimeDecisionResult(
                decision=KnowledgeDecision.RUN_FRESH,
                freshness_state=KnowledgeFreshnessState.EXPIRED,
                reason="knowledge_snapshot_expired",
                source=snapshot.source,
                age_seconds=age_seconds,
                evidence=snapshot.provenance,
            )

        missing_fields = tuple(
            field for field in context.requested_fields if not snapshot.field_coverage.get(field, False)
        )
        ttl_seconds = self.policy.ttl_for_family(spec.base_family)
        if missing_fields and self.policy.allow_partial_field_refresh and age_seconds <= self.policy.stale_ttl_seconds:
            return KnowledgeRuntimeDecisionResult(
                decision=KnowledgeDecision.PARTIAL_REFRESH,
                freshness_state=KnowledgeFreshnessState.PARTIAL,
                reason="knowledge_snapshot_missing_requested_fields",
                source=snapshot.source,
                age_seconds=age_seconds,
                reusable_output=snapshot.output,
                refresh_fields=missing_fields,
                evidence=snapshot.provenance,
            )
        if age_seconds <= ttl_seconds:
            return KnowledgeRuntimeDecisionResult(
                decision=KnowledgeDecision.SERVE_CACHED,
                freshness_state=KnowledgeFreshnessState.FRESH,
                reason="knowledge_snapshot_fresh",
                source=snapshot.source,
                age_seconds=age_seconds,
                reusable_output=snapshot.output,
                evidence=snapshot.provenance,
            )
        if age_seconds <= self.policy.stale_ttl_seconds and self.policy.allow_stale_while_revalidate:
            return KnowledgeRuntimeDecisionResult(
                decision=KnowledgeDecision.SERVE_CACHED_AND_REFRESH,
                freshness_state=KnowledgeFreshnessState.STALE,
                reason="knowledge_snapshot_stale_revalidate",
                source=snapshot.source,
                age_seconds=age_seconds,
                reusable_output=snapshot.output,
                evidence=snapshot.provenance,
            )
        return KnowledgeRuntimeDecisionResult(
            decision=KnowledgeDecision.RUN_FRESH,
            freshness_state=KnowledgeFreshnessState.EXPIRED,
            reason="knowledge_snapshot_too_old",
            source=snapshot.source,
            age_seconds=age_seconds,
            evidence=snapshot.provenance,
        )


async def maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value
