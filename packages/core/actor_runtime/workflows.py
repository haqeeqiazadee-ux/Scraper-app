from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field, field_validator

from packages.core.actor_runtime.models import FreshnessPolicy, ProviderStep


REQUIRED_QA_GATES = (
    "unit",
    "contract",
    "fixture_replay",
    "security",
    "cost",
    "trace",
    "eval",
    "api",
)


class ProviderLadder(BaseModel):
    steps: tuple[ProviderStep, ...]
    no_durable_api_rationale: str = ""

    @field_validator("steps", mode="before")
    @classmethod
    def _normalize_steps(cls, value: Any) -> tuple[ProviderStep, ...]:
        if value is None:
            return ()
        return tuple(value)

    @field_validator("no_durable_api_rationale", mode="before")
    @classmethod
    def _normalize_rationale(cls, value: Any) -> str:
        return "" if value is None else str(value).strip()

    @property
    def ordered_steps(self) -> tuple[ProviderStep, ...]:
        return tuple(sorted(self.steps, key=lambda step: step.priority))

    @property
    def is_mapped(self) -> bool:
        return bool(self.steps)


class WorkflowProfile(BaseModel):
    version: str = "1.0.0"
    strategy_id: str
    promoted_by: str = "codex"
    replay_fixture_ids: tuple[str, ...] = Field(default_factory=tuple)


class WorkflowUIContract(BaseModel):
    form_schema: dict[str, Any] = Field(default_factory=dict)
    result_columns: tuple[str, ...] = Field(default_factory=tuple)
    export_modes: tuple[str, ...] = ("json", "csv")
    examples: tuple[dict[str, Any], ...] = Field(default_factory=tuple)


class WorkflowAPISurface(BaseModel):
    run_endpoint: str = "/api/v1/actors/{actor_id}/runs"
    list_endpoint: str = "/api/v1/actors/{actor_id}/runs"
    detail_endpoint: str = "/api/v1/actors/{actor_id}/runs/{run_id}"
    result_endpoint: str = "/api/v1/results/{result_id}"
    export_endpoint: str = "/api/v1/results/{result_id}/export"
    schedule_endpoint: str = "/api/v1/schedules"
    webhook_endpoint: str = "/api/v1/webhooks"


class WorkflowQAGate(BaseModel):
    required_gates: tuple[str, ...] = REQUIRED_QA_GATES
    test_files: tuple[str, ...] = Field(default_factory=tuple)
    no_core_rewrite_fixture: str

    @field_validator("required_gates", "test_files", mode="before")
    @classmethod
    def _normalize_tuple(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        return tuple(str(item).strip() for item in value if str(item).strip())

    @property
    def missing_required_gates(self) -> tuple[str, ...]:
        present = set(self.required_gates)
        return tuple(gate for gate in REQUIRED_QA_GATES if gate not in present)

    @property
    def is_complete(self) -> bool:
        return not self.missing_required_gates and bool(self.no_core_rewrite_fixture)


class WorkflowSpec(BaseModel):
    workflow_id: str
    category: str
    platform_type: str
    supported_intents: tuple[str, ...] = Field(default_factory=tuple)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    examples: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    default_limits: dict[str, Any] = Field(default_factory=dict)
    pricing_hints: dict[str, Any] = Field(default_factory=dict)
    compliance_notes: tuple[str, ...] = Field(default_factory=tuple)
    freshness_policy: FreshnessPolicy = Field(default_factory=FreshnessPolicy)
    provider_ladder: ProviderLadder
    result_contract: dict[str, Any] = Field(default_factory=dict)
    profile: WorkflowProfile
    ui_contract: WorkflowUIContract = Field(default_factory=WorkflowUIContract)
    api_surface: WorkflowAPISurface = Field(default_factory=WorkflowAPISurface)
    qa_gate: WorkflowQAGate
    requires_core_runtime_rewrite: bool = False
    requires_router_rewrite: bool = False
    requires_storage_rewrite: bool = False

    @field_validator("supported_intents", "compliance_notes", mode="before")
    @classmethod
    def _normalize_tuple(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        return tuple(str(item).strip() for item in value if str(item).strip())

    def assert_extension_safe(self) -> None:
        blockers: list[str] = []
        if self.requires_core_runtime_rewrite:
            blockers.append("requires_core_runtime_rewrite")
        if self.requires_router_rewrite:
            blockers.append("requires_router_rewrite")
        if self.requires_storage_rewrite:
            blockers.append("requires_storage_rewrite")
        if not self.provider_ladder.is_mapped:
            blockers.append("provider_ladder_missing")
        if not self.qa_gate.is_complete:
            blockers.extend(f"missing_qa_gate:{gate}" for gate in self.qa_gate.missing_required_gates)
        if blockers:
            raise ValueError(";".join(blockers))


class WorkflowAdapter(Protocol):
    async def execute(self, payload: dict[str, Any], spec: WorkflowSpec) -> dict[str, Any]:
        ...

    def normalize(self, output: dict[str, Any], spec: WorkflowSpec) -> dict[str, Any]:
        ...


class WorkflowRegistry:
    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowSpec] = {}

    def register(self, spec: WorkflowSpec) -> WorkflowSpec:
        spec.assert_extension_safe()
        if spec.workflow_id in self._workflows:
            raise ValueError(f"Workflow {spec.workflow_id} is already registered")
        self._workflows[spec.workflow_id] = spec
        return spec

    def get(self, workflow_id: str) -> WorkflowSpec | None:
        return self._workflows.get(workflow_id)

    def list_by_category(self, category: str) -> tuple[WorkflowSpec, ...]:
        return tuple(spec for spec in self._workflows.values() if spec.category == category)

    def all(self) -> tuple[WorkflowSpec, ...]:
        return tuple(self._workflows.values())


workflow_registry = WorkflowRegistry()
