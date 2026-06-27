from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Mapping, Protocol

from pydantic import BaseModel, Field, field_validator

from packages.core.actor_runtime.models import ActorRunState, ActorRuntimeResult, ActorSpec


SENSITIVE_PAYLOAD_KEYS = {
    "api_key",
    "authorization",
    "cookie",
    "cookies",
    "password",
    "secret",
    "session",
    "token",
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _normalize_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _next_patch_version(version: str) -> str:
    parts = version.split(".")
    if len(parts) != 3:
        return f"{version}.1"
    try:
        patch = int(parts[2]) + 1
    except ValueError:
        return f"{version}.1"
    return f"{parts[0]}.{parts[1]}.{patch}"


def _redact_payload(payload: Mapping[str, Any]) -> tuple[dict[str, Any], tuple[str, ...]]:
    redacted: dict[str, Any] = {}
    redacted_keys: list[str] = []
    for key, value in payload.items():
        clean_key = str(key)
        if clean_key.lower() in SENSITIVE_PAYLOAD_KEYS:
            redacted[clean_key] = "[redacted]"
            redacted_keys.append(clean_key)
        elif isinstance(value, dict):
            redacted_child, child_keys = _redact_payload(value)
            redacted[clean_key] = redacted_child
            redacted_keys.extend(f"{clean_key}.{child}" for child in child_keys)
        else:
            redacted[clean_key] = value
    return redacted, tuple(redacted_keys)


def _payload_fingerprint(payload: Mapping[str, Any]) -> tuple[str, tuple[str, ...]]:
    safe_payload, redacted_keys = _redact_payload(payload)
    encoded = json.dumps(safe_payload, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:24], redacted_keys


class LearningEventType(StrEnum):
    RUN_SUCCEEDED = "run_succeeded"
    RUN_FAILED = "run_failed"
    LOW_CONFIDENCE = "low_confidence"
    MISSING_FIELDS = "missing_fields"
    SECURITY_RISK = "security_risk"


class StrategyPatchStatus(StrEnum):
    PROPOSED = "proposed"
    REPLAY_PASSED = "replay_passed"
    REPLAY_FAILED = "replay_failed"
    PROMOTED = "promoted"
    REJECTED = "rejected"


class StrategyProfile(BaseModel):
    actor_id: str
    base_family: str
    version: str = "1.0.0"
    policy_version: str = "strategy-profile-v1"
    promoted_by: str = "codex"
    provider_order: tuple[str, ...] = Field(default_factory=tuple)
    schema_aliases: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    freshness_overrides: dict[str, Any] = Field(default_factory=dict)
    replay_fixture_ids: tuple[str, ...] = Field(default_factory=tuple)
    metrics: dict[str, Any] = Field(default_factory=dict)

    @field_validator("provider_order", "replay_fixture_ids", mode="before")
    @classmethod
    def _normalize_string_tuple(cls, value: Any) -> tuple[str, ...]:
        return _normalize_tuple(value)

    @field_validator("schema_aliases", mode="before")
    @classmethod
    def _normalize_aliases(cls, value: Any) -> dict[str, tuple[str, ...]]:
        if value is None:
            return {}
        return {str(key): _normalize_tuple(val) for key, val in dict(value).items()}


class ActorLearningEvent(BaseModel):
    actor_id: str
    tenant_id: str
    base_family: str
    event_type: LearningEventType
    trigger_reason: str
    observed_at: datetime = Field(default_factory=_utc_now)
    profile_version: str
    payload_fingerprint: str
    redacted_payload_keys: tuple[str, ...] = Field(default_factory=tuple)
    metrics: dict[str, Any] = Field(default_factory=dict)
    evidence: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("redacted_payload_keys", "evidence", mode="before")
    @classmethod
    def _normalize_tuple_fields(cls, value: Any) -> tuple[str, ...]:
        return _normalize_tuple(value)


class StrategyPatchProposal(BaseModel):
    proposal_id: str
    actor_id: str
    base_family: str
    current_profile_version: str
    proposed_profile_version: str
    patch: dict[str, Any] = Field(default_factory=dict)
    rationale: str
    required_replay_fixture_ids: tuple[str, ...] = Field(default_factory=tuple)
    status: StrategyPatchStatus = StrategyPatchStatus.PROPOSED
    created_at: datetime = Field(default_factory=_utc_now)

    @field_validator("required_replay_fixture_ids", mode="before")
    @classmethod
    def _normalize_fixture_ids(cls, value: Any) -> tuple[str, ...]:
        return _normalize_tuple(value)


class ReplayValidationResult(BaseModel):
    proposal_id: str
    passed: bool
    fixtures_run: tuple[str, ...] = Field(default_factory=tuple)
    score_before: float = 0.0
    score_after: float = 0.0
    security_blockers: tuple[str, ...] = Field(default_factory=tuple)
    errors: tuple[str, ...] = Field(default_factory=tuple)
    validated_at: datetime = Field(default_factory=_utc_now)

    @field_validator("fixtures_run", "security_blockers", "errors", mode="before")
    @classmethod
    def _normalize_tuple_fields(cls, value: Any) -> tuple[str, ...]:
        return _normalize_tuple(value)


class StrategyProfileStore(Protocol):
    def get_profile(self, actor_id: str, tenant_id: str | None = None) -> StrategyProfile | None:
        ...

    def record_learning_event(self, event: ActorLearningEvent) -> None:
        ...

    def promote_profile(self, profile: StrategyProfile) -> None:
        ...


def build_default_strategy_profile(spec: ActorSpec) -> StrategyProfile:
    return StrategyProfile(
        actor_id=spec.actor_id,
        base_family=spec.base_family,
        provider_order=tuple(step.name for step in spec.provider_chain),
    )


class StrategyProfileEngine:
    def build_learning_event(
        self,
        *,
        spec: ActorSpec,
        payload: Mapping[str, Any],
        result: ActorRuntimeResult,
        profile: StrategyProfile,
        tenant_id: str = "system",
    ) -> ActorLearningEvent:
        fingerprint, redacted_keys = _payload_fingerprint(payload)
        governance_eval = result.metadata.get("eval", {}) if isinstance(result.metadata, dict) else {}
        security = result.metadata.get("security", {}) if isinstance(result.metadata, dict) else {}

        event_type = LearningEventType.RUN_SUCCEEDED
        reason = "run_succeeded"
        if result.state != ActorRunState.SUCCEEDED:
            event_type = LearningEventType.RUN_FAILED
            reason = result.error or result.state.value
        elif security.get("risk_flags"):
            event_type = LearningEventType.SECURITY_RISK
            reason = "security_risk_flags_present"
        elif governance_eval.get("missing_required_fields"):
            event_type = LearningEventType.MISSING_FIELDS
            reason = "missing_required_fields"
        elif float(governance_eval.get("score", 1.0) or 0.0) < 0.75:
            event_type = LearningEventType.LOW_CONFIDENCE
            reason = "quality_score_below_threshold"

        return ActorLearningEvent(
            actor_id=spec.actor_id,
            tenant_id=tenant_id,
            base_family=spec.base_family,
            event_type=event_type,
            trigger_reason=reason,
            profile_version=profile.version,
            payload_fingerprint=fingerprint,
            redacted_payload_keys=redacted_keys,
            metrics={
                "state": result.state.value,
                "provider": result.provider,
                "eval_score": governance_eval.get("score"),
                "missing_required_fields": governance_eval.get("missing_required_fields", ()),
                "security_risk_flags": security.get("risk_flags", ()),
            },
            evidence=(reason,),
        )

    def propose_patch(self, event: ActorLearningEvent, profile: StrategyProfile) -> StrategyPatchProposal:
        patch: dict[str, Any] = {}
        rationale = event.trigger_reason
        missing_fields = _normalize_tuple(event.metrics.get("missing_required_fields"))
        if event.event_type == LearningEventType.MISSING_FIELDS and missing_fields:
            patch["schema_alias_review"] = {field: () for field in missing_fields}
            rationale = "Review schema aliases for missing required fields."
        elif event.event_type == LearningEventType.LOW_CONFIDENCE:
            patch["quality_threshold_review"] = {"previous_score": event.metrics.get("eval_score")}
            rationale = "Review extraction strategy for low-confidence output."
        elif event.event_type == LearningEventType.RUN_FAILED:
            patch["failure_classifier"] = event.trigger_reason
            rationale = "Classify failure and propose a deterministic fixture before strategy promotion."
        elif event.event_type == LearningEventType.SECURITY_RISK:
            patch["security_review_required"] = True
            rationale = "Security risk signals require review before promotion."
        else:
            patch["observation_only"] = True

        basis = f"{event.actor_id}:{event.profile_version}:{event.payload_fingerprint}:{event.event_type.value}"
        proposal_id = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:24]
        return StrategyPatchProposal(
            proposal_id=proposal_id,
            actor_id=event.actor_id,
            base_family=event.base_family,
            current_profile_version=profile.version,
            proposed_profile_version=_next_patch_version(profile.version),
            patch=patch,
            rationale=rationale,
            required_replay_fixture_ids=profile.replay_fixture_ids,
        )

    def validate_replay(
        self,
        proposal: StrategyPatchProposal,
        replay_results: tuple[Mapping[str, Any], ...],
    ) -> ReplayValidationResult:
        fixtures_run = tuple(str(item.get("fixture_id", "")) for item in replay_results if item.get("fixture_id"))
        errors = tuple(str(item.get("error", "")) for item in replay_results if item.get("error"))
        security_blockers = tuple(
            str(item.get("security_blocker", ""))
            for item in replay_results
            if item.get("security_blocker")
        )
        required = set(proposal.required_replay_fixture_ids)
        missing_required = tuple(sorted(required - set(fixtures_run)))
        score_before_values = [float(item.get("score_before", 0.0) or 0.0) for item in replay_results]
        score_after_values = [float(item.get("score_after", 0.0) or 0.0) for item in replay_results]
        score_before = min(score_before_values) if score_before_values else 0.0
        score_after = min(score_after_values) if score_after_values else 0.0
        all_passed = all(bool(item.get("passed")) for item in replay_results) if replay_results else False
        passed = all_passed and not errors and not security_blockers and not missing_required and score_after >= score_before
        return ReplayValidationResult(
            proposal_id=proposal.proposal_id,
            passed=passed,
            fixtures_run=fixtures_run,
            score_before=score_before,
            score_after=score_after,
            security_blockers=security_blockers,
            errors=errors + tuple(f"missing_fixture:{fixture}" for fixture in missing_required),
        )

    def promote_profile(
        self,
        profile: StrategyProfile,
        proposal: StrategyPatchProposal,
        validation: ReplayValidationResult,
        *,
        promoted_by: str = "codex",
    ) -> StrategyProfile:
        if proposal.proposal_id != validation.proposal_id:
            raise ValueError("Replay validation does not match proposal")
        if not validation.passed:
            raise ValueError("Strategy profile cannot be promoted before replay validation passes")

        schema_aliases = dict(profile.schema_aliases)
        for key, value in dict(proposal.patch.get("schema_aliases", {})).items():
            schema_aliases[str(key)] = _normalize_tuple(value)

        provider_order = profile.provider_order
        if proposal.patch.get("provider_order"):
            provider_order = _normalize_tuple(proposal.patch["provider_order"])

        freshness_overrides = dict(profile.freshness_overrides)
        freshness_overrides.update(dict(proposal.patch.get("freshness_overrides", {})))

        replay_fixture_ids = tuple(dict.fromkeys(profile.replay_fixture_ids + validation.fixtures_run))
        metrics = dict(profile.metrics)
        metrics.update(
            {
                "last_proposal_id": proposal.proposal_id,
                "last_replay_score_before": validation.score_before,
                "last_replay_score_after": validation.score_after,
            }
        )

        return profile.model_copy(
            update={
                "version": proposal.proposed_profile_version,
                "promoted_by": promoted_by,
                "provider_order": provider_order,
                "schema_aliases": schema_aliases,
                "freshness_overrides": freshness_overrides,
                "replay_fixture_ids": replay_fixture_ids,
                "metrics": metrics,
            }
        )
