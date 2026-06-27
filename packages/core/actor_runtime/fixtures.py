from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Mapping

from pydantic import BaseModel, Field, field_validator

from packages.core.actor_runtime.models import ActorRunState, ActorRuntimeResult, ActorSpec
from packages.core.actor_runtime.profiles import SENSITIVE_PAYLOAD_KEYS


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _normalize_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _redact(value: Any, prefix: str = "") -> tuple[Any, tuple[str, ...]]:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        keys: list[str] = []
        for raw_key, child in value.items():
            key = str(raw_key)
            path = f"{prefix}.{key}" if prefix else key
            if key.lower() in SENSITIVE_PAYLOAD_KEYS:
                redacted[key] = "[redacted]"
                keys.append(path)
                continue
            redacted_child, redacted_keys = _redact(child, path)
            redacted[key] = redacted_child
            keys.extend(redacted_keys)
        return redacted, tuple(keys)
    if isinstance(value, list):
        redacted_items = []
        keys: list[str] = []
        for index, child in enumerate(value):
            redacted_child, redacted_keys = _redact(child, f"{prefix}[{index}]")
            redacted_items.append(redacted_child)
            keys.extend(redacted_keys)
        return redacted_items, tuple(keys)
    return value, ()


class RegressionFixtureCandidate(BaseModel):
    fixture_id: str
    actor_id: str
    base_family: str
    tenant_id: str
    trigger_reasons: tuple[str, ...] = Field(default_factory=tuple)
    source_trace_id: str | None = None
    state: str
    provider: str | None = None
    sanitized_input: dict[str, Any] = Field(default_factory=dict)
    redacted_payload_keys: tuple[str, ...] = Field(default_factory=tuple)
    expected_assertions: tuple[str, ...] = Field(default_factory=tuple)
    tags: tuple[str, ...] = Field(default_factory=tuple)
    created_at: datetime = Field(default_factory=_utc_now)

    @field_validator("trigger_reasons", "redacted_payload_keys", "expected_assertions", "tags", mode="before")
    @classmethod
    def _normalize_tuple_fields(cls, value: Any) -> tuple[str, ...]:
        return _normalize_tuple(value)


def _fixture_reasons(result: ActorRuntimeResult, *, score_threshold: float) -> tuple[str, ...]:
    reasons: list[str] = []
    metadata = result.metadata if isinstance(result.metadata, dict) else {}
    eval_metadata = metadata.get("eval", {}) if isinstance(metadata.get("eval"), dict) else {}
    security_metadata = metadata.get("security", {}) if isinstance(metadata.get("security"), dict) else {}

    if result.state != ActorRunState.SUCCEEDED:
        reasons.append("run_failed")
    score = float(eval_metadata.get("score", 1.0) or 0.0)
    if score < score_threshold:
        reasons.append("low_confidence")
    if eval_metadata.get("missing_required_fields"):
        reasons.append("missing_required_fields")
    if security_metadata.get("risk_flags"):
        reasons.append("security_risk")
    return tuple(dict.fromkeys(reasons))


def _expected_assertions(reasons: tuple[str, ...], redacted_keys: tuple[str, ...]) -> tuple[str, ...]:
    assertions = ["fixture_replay_is_deterministic"]
    if "run_failed" in reasons:
        assertions.append("run_should_not_fail_after_fix")
    if "low_confidence" in reasons:
        assertions.append("quality_score_should_improve")
    if "missing_required_fields" in reasons:
        assertions.append("required_fields_should_be_present")
    if "security_risk" in reasons or redacted_keys:
        assertions.append("sensitive_inputs_must_remain_redacted")
    return tuple(assertions)


def build_regression_fixture_candidate(
    *,
    spec: ActorSpec,
    payload: Mapping[str, Any],
    result: ActorRuntimeResult,
    tenant_id: str = "system",
    score_threshold: float = 0.75,
) -> RegressionFixtureCandidate | None:
    reasons = _fixture_reasons(result, score_threshold=score_threshold)
    if not reasons:
        return None

    sanitized, redacted_keys = _redact(dict(payload))
    metadata = result.metadata if isinstance(result.metadata, dict) else {}
    trace = metadata.get("trace", {}) if isinstance(metadata.get("trace"), dict) else {}
    trace_id = trace.get("trace_id")
    fingerprint_basis = {
        "actor_id": spec.actor_id,
        "base_family": spec.base_family,
        "tenant_id": tenant_id,
        "trace_id": trace_id,
        "state": result.state.value,
        "provider": result.provider,
        "payload": sanitized,
        "reasons": reasons,
    }
    fixture_id = hashlib.sha256(
        json.dumps(fingerprint_basis, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:24]
    return RegressionFixtureCandidate(
        fixture_id=f"fixture-{fixture_id}",
        actor_id=spec.actor_id,
        base_family=spec.base_family,
        tenant_id=tenant_id,
        trigger_reasons=reasons,
        source_trace_id=str(trace_id) if trace_id else None,
        state=result.state.value,
        provider=result.provider,
        sanitized_input=dict(sanitized),
        redacted_payload_keys=redacted_keys,
        expected_assertions=_expected_assertions(reasons, redacted_keys),
        tags=("actor-regression", "trace-to-fixture", *reasons),
    )


class TraceToFixturePromoter:
    def __init__(self, *, score_threshold: float = 0.75) -> None:
        self.score_threshold = score_threshold

    def candidate_from_result(
        self,
        *,
        spec: ActorSpec,
        payload: Mapping[str, Any],
        result: ActorRuntimeResult,
        tenant_id: str = "system",
    ) -> RegressionFixtureCandidate | None:
        return build_regression_fixture_candidate(
            spec=spec,
            payload=payload,
            result=result,
            tenant_id=tenant_id,
            score_threshold=self.score_threshold,
        )
