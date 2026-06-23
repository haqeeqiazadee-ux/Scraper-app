from __future__ import annotations

from packages.core.actor_runtime.models import ProviderStep
from packages.core.secrets import SecretsManager, secrets


class ProviderChain:
    def __init__(self, steps: list[ProviderStep] | tuple[ProviderStep, ...]) -> None:
        self._steps = tuple(sorted(steps, key=lambda step: step.priority))

    @property
    def steps(self) -> tuple[ProviderStep, ...]:
        return self._steps

    def missing_env_names(self, secrets_manager: SecretsManager | None = None) -> tuple[str, ...]:
        manager = secrets_manager or secrets
        missing: list[str] = []
        for step in self._steps:
            for name in step.required_env_names:
                if manager.get(name) is None and name not in missing:
                    missing.append(name)
        return tuple(missing)

    def first_available(self, secrets_manager: SecretsManager | None = None) -> ProviderStep | None:
        manager = secrets_manager or secrets
        for step in self._steps:
            if all(manager.get(name) is not None for name in step.required_env_names):
                return step
        return None
