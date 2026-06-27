from __future__ import annotations


def _future_workflow_spec():
    from packages.core.actor_runtime import (
        ProviderLadder,
        ProviderStep,
        ProviderTier,
        WorkflowAPISurface,
        WorkflowProfile,
        WorkflowQAGate,
        WorkflowSpec,
        WorkflowUIContract,
    )

    return WorkflowSpec(
        workflow_id="wearable-device-health-metrics",
        category="health_devices",
        platform_type="wearable_device_api",
        supported_intents=("sync_metrics", "monitor_activity"),
        input_schema={"type": "object", "properties": {"account_id": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"steps": {"type": "integer"}}},
        examples=({"account_id": "acct_demo"},),
        pricing_hints={"unit": "run", "base_credits": 1},
        compliance_notes=("No raw health secrets in logs or result packets.",),
        provider_ladder=ProviderLadder(
            steps=(
                ProviderStep(
                    name="wearable_public_api",
                    tier=ProviderTier.OFFICIAL_PUBLIC_API,
                    connector="packages.connectors.wearable_connector.WearableConnector",
                    priority=1,
                    rationale="Prefer the platform public API before any export scrape.",
                ),
                ProviderStep(
                    name="wearable_export_http",
                    tier=ProviderTier.HTTP_EXTRACTION,
                    connector="services.worker_http.worker.HttpWorker",
                    priority=2,
                    rationale="Fallback only for user-authorized export pages.",
                ),
            )
        ),
        result_contract={"required_fields": ["steps"]},
        profile=WorkflowProfile(
            strategy_id="wearable-api-first-v1",
            replay_fixture_ids=("fixtures/workflows/wearable_device_happy_path.json",),
        ),
        ui_contract=WorkflowUIContract(
            form_schema={"account_id": {"control": "text"}},
            result_columns=("steps",),
            examples=({"account_id": "acct_demo"},),
        ),
        api_surface=WorkflowAPISurface(),
        qa_gate=WorkflowQAGate(
            no_core_rewrite_fixture="tests/fixtures/workflows/wearable_no_core_rewrite.json",
            test_files=("tests/unit/test_workflow_extension_contract.py",),
        ),
    )


def test_future_platform_category_registers_without_core_runtime_router_or_storage_rewrite() -> None:
    from packages.core.actor_runtime import WorkflowRegistry

    registry = WorkflowRegistry()
    spec = registry.register(_future_workflow_spec())

    assert spec.requires_core_runtime_rewrite is False
    assert spec.requires_router_rewrite is False
    assert spec.requires_storage_rewrite is False
    assert registry.get("wearable-device-health-metrics") is spec
    assert registry.list_by_category("health_devices") == (spec,)


def test_future_platform_category_inherits_shared_api_memory_governance_and_qa_contracts() -> None:
    spec = _future_workflow_spec()

    assert spec.provider_ladder.ordered_steps[0].tier == "official_public_api"
    assert spec.api_surface.run_endpoint == "/api/v1/actors/{actor_id}/runs"
    assert spec.freshness_policy.tenant_isolation_required is True
    assert spec.qa_gate.is_complete is True
    assert spec.ui_contract.export_modes == ("json", "csv")
    assert spec.profile.replay_fixture_ids == ("fixtures/workflows/wearable_device_happy_path.json",)


def test_workflow_extension_rejects_core_rewrite_and_incomplete_qa_gate() -> None:
    from packages.core.actor_runtime import WorkflowSpec

    data = _future_workflow_spec().model_dump()
    data["requires_core_runtime_rewrite"] = True
    data["qa_gate"]["required_gates"] = ("unit", "contract")
    spec = WorkflowSpec(**data)

    try:
        spec.assert_extension_safe()
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected extension safety failure")

    assert "requires_core_runtime_rewrite" in message
    assert "missing_qa_gate:security" in message
    assert "missing_qa_gate:api" in message


def test_workflow_registry_rejects_duplicate_workflow_ids() -> None:
    from packages.core.actor_runtime import WorkflowRegistry

    registry = WorkflowRegistry()
    registry.register(_future_workflow_spec())

    try:
        registry.register(_future_workflow_spec())
    except ValueError as exc:
        assert "already registered" in str(exc)
    else:
        raise AssertionError("Expected duplicate registration failure")
