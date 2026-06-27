from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ActorProofLevel(StrEnum):
    CATALOG_ONLY = "catalog_only"
    API_MAPPED = "api_mapped"
    RUNTIME_SMOKE_PASSED = "runtime_smoke_passed"
    FIXTURE_REPLAY_PASSED = "fixture_replay_passed"
    UI_ROUTE_PASSED = "ui_route_passed"
    LIVE_E2E_PASSED = "live_e2e_passed"


class ActorProofFailureClass(StrEnum):
    NONE = "none"
    IMPLEMENTATION_BUG = "implementation_bug"
    BAD_GENERATED_INPUT = "bad_generated_input"
    MISSING_CREDENTIALS = "missing_credentials"
    PROVIDER_RATE_LIMIT = "provider_rate_limit"
    PLATFORM_INSTABILITY = "platform_instability"
    ANTI_BOT_BLOCK = "anti_bot_block"
    UNSUPPORTED_FAMILY = "unsupported_family"
    EXTERNAL_OUTAGE = "external_outage"
    NO_RESULT_DATASET = "no_result_dataset"


class ActorProofRecord(BaseModel):
    actor_id: str
    tenant_id: str = "default"
    catalog_version: str = "actor-catalog-v1"
    catalog_total: int = 0
    proof_level: ActorProofLevel = ActorProofLevel.CATALOG_ONLY
    last_verified_at: datetime = Field(default_factory=_utc_now)
    test_input: dict[str, Any] = Field(default_factory=dict)
    run_id: str | None = None
    result_id: str | None = None
    items_count: int = 0
    schema_passed: bool = False
    export_json_passed: bool = False
    export_csv_passed: bool = False
    ui_route_passed: bool = False
    live_e2e_passed: bool = False
    fixture_replay_passed: bool = False
    blocked_reason: str | None = None
    failure_reason: str | None = None
    failure_class: ActorProofFailureClass = ActorProofFailureClass.NONE
    source_timestamp: datetime | None = None
    policy_version: str = "actor-proof-v1"
    tenant_scope: str = "tenant"
    provenance: tuple[str, ...] = Field(default_factory=tuple)
    proof_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("provenance", mode="before")
    @classmethod
    def _normalize_provenance(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            return (value.strip(),) if value.strip() else ()
        return tuple(str(item).strip() for item in value if str(item).strip())

    @field_validator("items_count", "catalog_total", mode="before")
    @classmethod
    def _normalize_non_negative_int(cls, value: Any) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = 0
        return max(parsed, 0)


class ActorProofSummary(BaseModel):
    tenant_id: str
    catalog_actor_count: int
    proof_ledger_count: int
    counts_by_level: dict[str, int] = Field(default_factory=dict)
    live_e2e_passed_count: int = 0
    fixture_replay_passed_count: int = 0
    runtime_smoke_passed_count: int = 0
    ui_route_passed_count: int = 0
    blocked_actor_count: int = 0
    unverified_actor_count: int = 0
    stale_actor_count: int = 0
    generated_at: datetime = Field(default_factory=_utc_now)


def actor_catalog_version(catalog_total: int) -> str:
    return f"actor-catalog-v1:{catalog_total}"


def actor_public_route(actor_id: str) -> str:
    return f"/actors/{actor_id}"


def generate_actor_test_input(entry: Any) -> dict[str, Any]:
    """Generate a safe default input without using Apify URLs as runtime targets."""
    categories = {str(item).upper() for item in getattr(entry, "categories", ())}
    route_strategy = str(getattr(entry, "route_strategy", "native_pipeline") or "native_pipeline")
    name = str(getattr(entry, "name", "actor") or "actor")

    if "JOBS" in categories or route_strategy == "job_board_schema":
        return {"target": "https://example.com", "max_items": 5}
    if "REAL_ESTATE" in categories or route_strategy == "real_estate_schema":
        return {"target": "https://example.com", "max_items": 5}
    if "VIDEOS" in categories or route_strategy == "yt_dlp":
        return {"target": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "max_items": 5}
    if "ECOMMERCE" in categories:
        return {"target": "https://example.com/products", "max_items": 5}
    if "LEAD_GENERATION" in categories or "BUSINESS" in categories:
        return {"target": "https://example.com", "max_items": 5}
    if "NEWS" in categories:
        return {"target": "https://example.com", "max_items": 5}
    if "SOCIAL_MEDIA" in categories:
        return {"target": "https://example.com", "max_items": 5}
    return {"target": "https://example.com", "max_items": 5, "workflow_hint": name}


def classify_actor_proof_failure(
    *,
    run_status: str,
    error: str | None = None,
    missing_env_names: tuple[str, ...] = (),
    item_count: int = 0,
) -> ActorProofFailureClass:
    lowered = (error or "").lower()
    if missing_env_names or ("missing" in lowered and ("key" in lowered or "env" in lowered)):
        return ActorProofFailureClass.MISSING_CREDENTIALS
    if run_status in {"blocked_policy", "blocked"}:
        return ActorProofFailureClass.UNSUPPORTED_FAMILY
    if "rate" in lowered and "limit" in lowered:
        return ActorProofFailureClass.PROVIDER_RATE_LIMIT
    if "captcha" in lowered or "bot" in lowered or "403" in lowered:
        return ActorProofFailureClass.ANTI_BOT_BLOCK
    if "timeout" in lowered or "503" in lowered or "502" in lowered:
        return ActorProofFailureClass.EXTERNAL_OUTAGE
    if run_status == "completed" and item_count <= 0:
        return ActorProofFailureClass.NO_RESULT_DATASET
    if run_status in {"failed", "error"}:
        return ActorProofFailureClass.IMPLEMENTATION_BUG
    return ActorProofFailureClass.NONE


def choose_proof_level(
    *,
    run_status: str,
    has_result: bool,
    item_count: int,
    export_json_passed: bool,
    export_csv_passed: bool,
    ui_route_passed: bool,
    fixture_replay_passed: bool,
) -> ActorProofLevel:
    if (
        run_status == "completed"
        and has_result
        and item_count > 0
        and export_json_passed
        and export_csv_passed
        and ui_route_passed
    ):
        return ActorProofLevel.LIVE_E2E_PASSED
    if fixture_replay_passed:
        return ActorProofLevel.FIXTURE_REPLAY_PASSED
    if run_status == "completed" and has_result and item_count > 0 and export_json_passed and export_csv_passed:
        return ActorProofLevel.RUNTIME_SMOKE_PASSED
    if ui_route_passed and run_status in {"route_checked", "ui_route_passed"}:
        return ActorProofLevel.UI_ROUTE_PASSED
    return ActorProofLevel.API_MAPPED
