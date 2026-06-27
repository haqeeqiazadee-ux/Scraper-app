from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from packages.core.actor_runtime.knowledge import SENSITIVE_PAYLOAD_KEYS
from packages.core.actor_runtime.models import (
    ActorCostEstimate,
    ActorQualityEval,
    ActorRuntimeTrace,
    ActorSecurityAssessment,
    ActorSpec,
    KnowledgeDecision,
    KnowledgeRuntimeDecisionResult,
)
from packages.core.cost_tracker import COST_TABLE


INJECTION_MARKERS = (
    "ignore previous",
    "system prompt",
    "developer message",
    "reveal secrets",
)

BASE_FAMILY_COST_API = {
    "marketplace_product_catalog": "keepa_asin",
    "local_maps_serp": "serper_places",
    "commerce_storefront_generic": "shopify_api",
}


def assess_actor_payload_security(payload: Mapping[str, Any]) -> ActorSecurityAssessment:
    redacted_keys = tuple(sorted(str(key) for key in payload if str(key).lower() in SENSITIVE_PAYLOAD_KEYS))
    text = " ".join(
        str(value).lower()
        for key, value in payload.items()
        if str(key).lower() not in SENSITIVE_PAYLOAD_KEYS and isinstance(value, str)
    )
    risk_flags: list[str] = []
    if redacted_keys:
        risk_flags.append("sensitive_payload_keys_present")
    if any(marker in text for marker in INJECTION_MARKERS):
        risk_flags.append("prompt_injection_marker_present")
    return ActorSecurityAssessment(
        allowed=True,
        redacted_payload_keys=redacted_keys,
        risk_flags=tuple(risk_flags),
    )


def estimate_actor_cost(
    spec: ActorSpec,
    decision: KnowledgeRuntimeDecisionResult,
    output: Mapping[str, Any],
) -> ActorCostEstimate:
    api = BASE_FAMILY_COST_API.get(spec.base_family, "curl_cffi_page")
    unit_cost = COST_TABLE.get(api, 0.0)
    item_count = int(output.get("item_count") or 0)
    fresh_cost = max(unit_cost, unit_cost * max(item_count, 1))
    if decision.decision in {KnowledgeDecision.SERVE_CACHED, KnowledgeDecision.SERVE_CACHED_AND_REFRESH}:
        return ActorCostEstimate(
            estimated_usd=0.0,
            estimated_credits=0,
            saved_by_knowledge_usd=round(fresh_cost, 6),
            pricing_basis=f"knowledge_reuse_avoided:{api}",
        )
    estimated_usd = round(fresh_cost, 6)
    return ActorCostEstimate(
        estimated_usd=estimated_usd,
        estimated_credits=0 if estimated_usd == 0 else max(int(estimated_usd * 100000), 1),
        saved_by_knowledge_usd=0.0,
        pricing_basis=api,
    )


def evaluate_actor_output(output: Mapping[str, Any], requested_fields: tuple[str, ...] = ()) -> ActorQualityEval:
    items = output.get("extracted_data", output.get("items", []))
    item_dicts = [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []
    item_count = int(output.get("item_count") or len(item_dicts))
    confidence = min(max(float(output.get("confidence") or 0.0), 0.0), 1.0)
    missing_required_fields = tuple(
        field for field in requested_fields if not any(field in item and item.get(field) is not None for item in item_dicts)
    )
    field_score = 1.0 if not missing_required_fields else max(0.0, 1.0 - (len(missing_required_fields) / max(len(requested_fields), 1)))
    volume_score = 1.0 if item_count > 0 else 0.0
    score = round((confidence * 0.5) + (field_score * 0.3) + (volume_score * 0.2), 4)
    return ActorQualityEval(
        passed=score >= 0.6 and not missing_required_fields,
        score=score,
        item_count=item_count,
        confidence=confidence,
        missing_required_fields=missing_required_fields,
    )


def build_actor_trace(
    spec: ActorSpec,
    decision: KnowledgeRuntimeDecisionResult,
    *,
    provider: str | None = None,
) -> ActorRuntimeTrace:
    trace_basis = f"{spec.actor_id}:{spec.base_family}:{decision.decision.value}:{decision.reason}:{provider or ''}"
    trace_id = hashlib.sha256(trace_basis.encode("utf-8")).hexdigest()[:24]
    events = ("knowledge_decision", "security_assessment", "cost_estimate", "quality_eval")
    return ActorRuntimeTrace(
        trace_id=trace_id,
        actor_id=spec.actor_id,
        base_family=spec.base_family,
        decision=decision.decision.value,
        provider=provider,
        events=events,
    )


def build_actor_governance_metadata(
    *,
    spec: ActorSpec,
    payload: Mapping[str, Any],
    output: Mapping[str, Any],
    decision: KnowledgeRuntimeDecisionResult,
    provider: str | None = None,
    requested_fields: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "trace": build_actor_trace(spec, decision, provider=provider).model_dump(mode="json"),
        "security": assess_actor_payload_security(payload).model_dump(mode="json"),
        "cost": estimate_actor_cost(spec, decision, output).model_dump(mode="json"),
        "eval": evaluate_actor_output(output, requested_fields=requested_fields).model_dump(mode="json"),
    }
