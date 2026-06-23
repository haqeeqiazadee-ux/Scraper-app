from __future__ import annotations

import asyncio

from packages.core.secrets import SecretsManager


class StaticSecretProvider:
    def __init__(self, values: dict[str, str]) -> None:
        self.values = values

    def get_secret(self, key: str) -> str | None:
        return self.values.get(key)

    def set_secret(self, key: str, value: str) -> None:
        self.values[key] = value


def test_actor_spec_deduplicates_required_env_names() -> None:
    from packages.core.actor_runtime import ActorSpec, ProviderStep

    spec = ActorSpec(
        actor_id="actor-1",
        slug="demo-actor",
        title="Demo Actor",
        base_family="generic_web_page_extraction",
        required_env_names=["ACTOR_RUNTIME_TEST_KEY_A", "ACTOR_RUNTIME_TEST_KEY_A", "ACTOR_RUNTIME_TEST_KEY_B"],
        provider_chain=[ProviderStep(name="test-provider", required_env_names=["ACTOR_RUNTIME_TEST_KEY_A"])],
    )

    assert spec.required_env_names == ("ACTOR_RUNTIME_TEST_KEY_A", "ACTOR_RUNTIME_TEST_KEY_B")


def test_provider_chain_reports_missing_env_names() -> None:
    from packages.core.actor_runtime import ProviderChain, ProviderStep

    manager = SecretsManager()
    manager.add_provider(StaticSecretProvider({"ACTOR_RUNTIME_TEST_KEY_A": "present"}))
    chain = ProviderChain(
        [
            ProviderStep(name="provider-a", required_env_names=["ACTOR_RUNTIME_TEST_KEY_A"]),
            ProviderStep(name="provider-b", required_env_names=["ACTOR_RUNTIME_TEST_KEY_B"]),
        ]
    )

    assert chain.missing_env_names(manager) == ("ACTOR_RUNTIME_TEST_KEY_B",)
    assert chain.first_available(manager).name == "provider-a"


def test_base_actor_runner_skips_missing_required_key_without_execute() -> None:
    from packages.core.actor_runtime import ActorRunState, ActorSpec, BaseActorRunner

    class DemoRunner(BaseActorRunner):
        executed = False

        async def execute(self, payload: dict) -> dict:
            self.executed = True
            return {"items": [{"ok": True}]}

    runner = DemoRunner(
        ActorSpec(
            actor_id="actor-1",
            slug="demo-actor",
            title="Demo Actor",
            base_family="generic_web_page_extraction",
            required_env_names=["ACTOR_RUNTIME_TEST_MISSING_KEY"],
        ),
        secrets_manager=SecretsManager(),
    )

    result = asyncio.run(runner.run({"target": "https://example.com"}))

    assert result.state == ActorRunState.SKIPPED_MISSING_KEY
    assert result.missing_env_names == ("ACTOR_RUNTIME_TEST_MISSING_KEY",)
    assert result.output == {}
    assert runner.executed is False


def test_base_actor_runner_succeeds_when_requirements_are_met() -> None:
    from packages.core.actor_runtime import ActorRunState, ActorSpec, BaseActorRunner

    class DemoRunner(BaseActorRunner):
        async def execute(self, payload: dict) -> dict:
            return {"items": [{"target": payload["target"]}]}

    manager = SecretsManager()
    manager.add_provider(StaticSecretProvider({"ACTOR_RUNTIME_TEST_KEY_A": "present"}))
    runner = DemoRunner(
        ActorSpec(
            actor_id="actor-1",
            slug="demo-actor",
            title="Demo Actor",
            base_family="generic_web_page_extraction",
            required_env_names=["ACTOR_RUNTIME_TEST_KEY_A"],
        ),
        secrets_manager=manager,
    )

    result = asyncio.run(runner.run({"target": "https://example.com"}))

    assert result.state == ActorRunState.SUCCEEDED
    assert result.output == {"items": [{"target": "https://example.com"}]}
    assert result.missing_env_names == ()


def test_base_actor_runner_uses_first_available_provider_without_blocking_on_fallback_keys() -> None:
    from packages.core.actor_runtime import ActorRunState, ActorSpec, BaseActorRunner, ProviderStep

    class DemoRunner(BaseActorRunner):
        async def execute(self, payload: dict) -> dict:
            return {"items": [{"target": payload["target"]}]}

    manager = SecretsManager()
    manager.add_provider(StaticSecretProvider({"ACTOR_RUNTIME_TEST_KEY_A": "present"}))
    runner = DemoRunner(
        ActorSpec(
            actor_id="actor-1",
            slug="demo-actor",
            title="Demo Actor",
            base_family="generic_web_page_extraction",
            provider_chain=[
                ProviderStep(name="provider-a", required_env_names=["ACTOR_RUNTIME_TEST_KEY_A"], priority=1),
                ProviderStep(name="provider-b", required_env_names=["ACTOR_RUNTIME_TEST_KEY_B"], priority=2),
            ],
        ),
        secrets_manager=manager,
    )

    result = asyncio.run(runner.run({"target": "https://example.com"}))

    assert result.state == ActorRunState.SUCCEEDED
    assert result.provider == "provider-a"
    assert result.missing_env_names == ()
