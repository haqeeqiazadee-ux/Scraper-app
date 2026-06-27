from __future__ import annotations

from typing import Any

from packages.core.actor_runtime.models import (
    ActorRuntimeResult,
    ActorRunState,
    ActorSpec,
    FreshnessPolicy,
    KnowledgeDecision,
    KnowledgeFreshnessState,
    KnowledgeRuntimeDecisionResult,
    RequirementCheck,
)
from packages.core.actor_runtime.governance import build_actor_governance_metadata
from packages.core.actor_runtime.knowledge import (
    KnowledgeFreshnessEvaluator,
    KnowledgeMemoryStore,
    build_knowledge_context,
    maybe_await,
)
from packages.core.actor_runtime.profiles import (
    StrategyProfile,
    StrategyProfileEngine,
    StrategyProfileStore,
    build_default_strategy_profile,
)
from packages.core.actor_runtime.provider_chain import ProviderChain
from packages.core.secrets import SecretsManager, secrets


class BaseActorRunner:
    def __init__(
        self,
        spec: ActorSpec,
        secrets_manager: SecretsManager | None = None,
        *,
        knowledge_store: KnowledgeMemoryStore | None = None,
        freshness_policy: FreshnessPolicy | None = None,
        strategy_profile: StrategyProfile | None = None,
        strategy_profile_store: StrategyProfileStore | None = None,
        strategy_profile_engine: StrategyProfileEngine | None = None,
    ) -> None:
        self.spec = spec
        self.secrets = secrets_manager or secrets
        self.knowledge_store = knowledge_store
        self.knowledge_evaluator = KnowledgeFreshnessEvaluator(freshness_policy)
        self.strategy_profile = strategy_profile or build_default_strategy_profile(spec)
        self.strategy_profile_store = strategy_profile_store
        self.strategy_profile_engine = strategy_profile_engine or StrategyProfileEngine()

    def check_requirements(self) -> RequirementCheck:
        missing: list[str] = []
        available: list[str] = []
        provider: str | None = None

        for name in self.spec.required_env_names:
            if self.secrets.get(name) is None:
                missing.append(name)
            else:
                available.append(name)

        if self.spec.provider_chain and not missing:
            chain = ProviderChain(self.spec.provider_chain)
            selected_provider = chain.first_available(self.secrets)
            if selected_provider is not None:
                provider = selected_provider.name
                for name in selected_provider.required_env_names:
                    if name not in available:
                        available.append(name)
            else:
                for name in chain.missing_env_names(self.secrets):
                    if name not in missing:
                        missing.append(name)

        if missing:
            return RequirementCheck(
                state=ActorRunState.SKIPPED_MISSING_KEY,
                missing_env_names=tuple(missing),
                available_env_names=tuple(available),
            )

        return RequirementCheck(
            state=ActorRunState.READY,
            available_env_names=tuple(available),
            provider=provider,
        )

    async def run(self, payload: dict[str, Any]) -> ActorRuntimeResult:
        requirements = self.check_requirements()
        if not requirements.is_ready:
            result = ActorRuntimeResult(
                actor_id=self.spec.actor_id,
                state=requirements.state,
                missing_env_names=requirements.missing_env_names,
                metadata={
                    "base_family": self.spec.base_family,
                    "strategy_profile": self._strategy_profile_metadata(),
                },
            )
            await self.record_learning_event(payload, result)
            return result

        knowledge_decision = self.decide_knowledge(payload)
        if knowledge_decision.decision in {
            KnowledgeDecision.SERVE_CACHED,
            KnowledgeDecision.SERVE_CACHED_AND_REFRESH,
        }:
            result = ActorRuntimeResult(
                actor_id=self.spec.actor_id,
                state=ActorRunState.SUCCEEDED,
                output=knowledge_decision.reusable_output,
                provider=requirements.provider,
                metadata={
                    "base_family": self.spec.base_family,
                    "strategy_profile": self._strategy_profile_metadata(),
                    "knowledge": self._knowledge_metadata(knowledge_decision),
                    **self._governance_metadata(
                        payload,
                        knowledge_decision.reusable_output,
                        knowledge_decision,
                        requirements.provider,
                    ),
                },
            )
            await self.record_learning_event(payload, result)
            return result

        try:
            output = await self.execute(payload)
        except Exception as exc:
            result = ActorRuntimeResult(
                actor_id=self.spec.actor_id,
                state=ActorRunState.FAILED,
                error=f"{type(exc).__name__}: {exc}",
                provider=requirements.provider,
                metadata={
                    "base_family": self.spec.base_family,
                    "strategy_profile": self._strategy_profile_metadata(),
                },
            )
            await self.record_learning_event(payload, result)
            return result

        result = ActorRuntimeResult(
            actor_id=self.spec.actor_id,
            state=ActorRunState.SUCCEEDED,
            output=output,
            provider=requirements.provider,
            metadata={
                "base_family": self.spec.base_family,
                "strategy_profile": self._strategy_profile_metadata(),
                "knowledge": self._knowledge_metadata(knowledge_decision),
                **self._governance_metadata(payload, output, knowledge_decision, requirements.provider),
            },
        )
        await self.record_knowledge(payload, result)
        await self.record_learning_event(payload, result)
        return result

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Actor runners must implement execute()")

    def decide_knowledge(self, payload: dict[str, Any]) -> KnowledgeRuntimeDecisionResult:
        context = build_knowledge_context(
            self.spec,
            payload,
            tenant_id=getattr(self, "tenant_id", None),
        )
        if self.knowledge_store is None:
            return self.knowledge_evaluator.evaluate(spec=self.spec, context=context, snapshot=None)
        try:
            snapshot = self.knowledge_store.lookup(spec=self.spec, payload=payload, context=context)
        except Exception as exc:
            return KnowledgeRuntimeDecisionResult(
                decision=KnowledgeDecision.RUN_FRESH,
                freshness_state=KnowledgeFreshnessState.BLOCKED,
                reason=f"knowledge_lookup_failed:{type(exc).__name__}",
            )
        return self.knowledge_evaluator.evaluate(spec=self.spec, context=context, snapshot=snapshot)

    async def record_knowledge(self, payload: dict[str, Any], result: ActorRuntimeResult) -> None:
        if self.knowledge_store is None or result.state != ActorRunState.SUCCEEDED:
            return
        context = build_knowledge_context(
            self.spec,
            payload,
            tenant_id=getattr(self, "tenant_id", None),
        )
        try:
            await maybe_await(
                self.knowledge_store.record(
                    spec=self.spec,
                    payload=payload,
                    context=context,
                    result=result,
                )
            )
        except Exception as exc:
            result.metadata.setdefault("knowledge", {})["record_error"] = type(exc).__name__

    async def record_learning_event(self, payload: dict[str, Any], result: ActorRuntimeResult) -> None:
        if self.strategy_profile_store is None:
            return
        try:
            event = self.strategy_profile_engine.build_learning_event(
                spec=self.spec,
                payload=payload,
                result=result,
                profile=self.strategy_profile,
                tenant_id=str(getattr(self, "tenant_id", None) or "system"),
            )
            await maybe_await(self.strategy_profile_store.record_learning_event(event))
            result.metadata.setdefault("strategy_profile", self._strategy_profile_metadata())["learning_event"] = {
                "event_type": event.event_type.value,
                "profile_version": event.profile_version,
                "payload_fingerprint": event.payload_fingerprint,
                "redacted_payload_keys": list(event.redacted_payload_keys),
            }
        except Exception as exc:
            result.metadata.setdefault("strategy_profile", self._strategy_profile_metadata())[
                "learning_record_error"
            ] = type(exc).__name__

    def _knowledge_metadata(self, decision: KnowledgeRuntimeDecisionResult) -> dict[str, Any]:
        return decision.model_dump(mode="json", exclude={"reusable_output"})

    def _strategy_profile_metadata(self) -> dict[str, Any]:
        return {
            "actor_id": self.strategy_profile.actor_id,
            "base_family": self.strategy_profile.base_family,
            "version": self.strategy_profile.version,
            "policy_version": self.strategy_profile.policy_version,
            "promoted_by": self.strategy_profile.promoted_by,
            "provider_order": list(self.strategy_profile.provider_order),
            "replay_fixture_ids": list(self.strategy_profile.replay_fixture_ids),
        }

    def _governance_metadata(
        self,
        payload: dict[str, Any],
        output: dict[str, Any],
        decision: KnowledgeRuntimeDecisionResult,
        provider: str | None,
    ) -> dict[str, Any]:
        context = build_knowledge_context(
            self.spec,
            payload,
            tenant_id=getattr(self, "tenant_id", None),
        )
        return build_actor_governance_metadata(
            spec=self.spec,
            payload=payload,
            output=output,
            decision=decision,
            provider=provider,
            requested_fields=context.requested_fields,
        )
