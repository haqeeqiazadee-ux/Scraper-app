from __future__ import annotations

from typing import Any

from packages.core.actor_runtime.models import (
    ActorRuntimeResult,
    ActorRunState,
    ActorSpec,
    RequirementCheck,
)
from packages.core.actor_runtime.provider_chain import ProviderChain
from packages.core.secrets import SecretsManager, secrets


class BaseActorRunner:
    def __init__(self, spec: ActorSpec, secrets_manager: SecretsManager | None = None) -> None:
        self.spec = spec
        self.secrets = secrets_manager or secrets

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
            return ActorRuntimeResult(
                actor_id=self.spec.actor_id,
                state=requirements.state,
                missing_env_names=requirements.missing_env_names,
                metadata={"base_family": self.spec.base_family},
            )

        try:
            output = await self.execute(payload)
        except Exception as exc:
            return ActorRuntimeResult(
                actor_id=self.spec.actor_id,
                state=ActorRunState.FAILED,
                error=f"{type(exc).__name__}: {exc}",
                provider=requirements.provider,
                metadata={"base_family": self.spec.base_family},
            )

        return ActorRuntimeResult(
            actor_id=self.spec.actor_id,
            state=ActorRunState.SUCCEEDED,
            output=output,
            provider=requirements.provider,
            metadata={"base_family": self.spec.base_family},
        )

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Actor runners must implement execute()")
