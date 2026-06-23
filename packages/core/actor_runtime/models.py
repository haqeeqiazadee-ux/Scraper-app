from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


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


class ProviderStep(BaseModel):
    name: str
    required_env_names: tuple[str, ...] = Field(default_factory=tuple)
    optional_env_names: tuple[str, ...] = Field(default_factory=tuple)
    priority: int = 100

    @field_validator("required_env_names", "optional_env_names", mode="before")
    @classmethod
    def _normalize_env_names(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        return _dedupe_env_names(tuple(value))


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
