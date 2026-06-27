from __future__ import annotations


def _spec():
    from packages.core.actor_runtime import ActorSpec, ProviderStep

    return ActorSpec(
        actor_id="actor-fixture-1",
        slug="fixture-demo",
        title="Fixture Demo",
        base_family="generic_web_page_extraction",
        provider_chain=[ProviderStep(name="http_worker", priority=1)],
    )


def test_low_confidence_trace_becomes_redacted_fixture_candidate() -> None:
    from packages.core.actor_runtime import ActorRuntimeResult, ActorRunState, TraceToFixturePromoter

    result = ActorRuntimeResult(
        actor_id="actor-fixture-1",
        state=ActorRunState.SUCCEEDED,
        provider="http_worker",
        metadata={
            "trace": {"trace_id": "trace-low-score"},
            "eval": {"score": 0.42, "missing_required_fields": ("price",)},
            "security": {"risk_flags": ()},
        },
    )

    candidate = TraceToFixturePromoter().candidate_from_result(
        spec=_spec(),
        payload={"target": "https://example.com/products", "cookies": "secret-cookie"},
        result=result,
        tenant_id="tenant-a",
    )

    assert candidate is not None
    assert candidate.source_trace_id == "trace-low-score"
    assert candidate.trigger_reasons == ("low_confidence", "missing_required_fields")
    assert candidate.sanitized_input["cookies"] == "[redacted]"
    assert candidate.redacted_payload_keys == ("cookies",)
    assert "required_fields_should_be_present" in candidate.expected_assertions
    assert "secret-cookie" not in candidate.model_dump_json()


def test_successful_high_confidence_trace_does_not_create_fixture_candidate() -> None:
    from packages.core.actor_runtime import ActorRuntimeResult, ActorRunState, build_regression_fixture_candidate

    result = ActorRuntimeResult(
        actor_id="actor-fixture-1",
        state=ActorRunState.SUCCEEDED,
        provider="http_worker",
        metadata={
            "trace": {"trace_id": "trace-good"},
            "eval": {"score": 0.95, "missing_required_fields": ()},
            "security": {"risk_flags": ()},
        },
    )

    candidate = build_regression_fixture_candidate(
        spec=_spec(),
        payload={"target": "https://example.com/products"},
        result=result,
        tenant_id="tenant-a",
    )

    assert candidate is None


def test_failed_trace_fixture_id_is_deterministic() -> None:
    from packages.core.actor_runtime import ActorRuntimeResult, ActorRunState, TraceToFixturePromoter

    result = ActorRuntimeResult(
        actor_id="actor-fixture-1",
        state=ActorRunState.FAILED,
        provider="http_worker",
        error="TimeoutError: deadline exceeded",
        metadata={
            "trace": {"trace_id": "trace-timeout"},
            "eval": {"score": 0.0},
        },
    )
    promoter = TraceToFixturePromoter()
    first = promoter.candidate_from_result(
        spec=_spec(),
        payload={"target": "https://example.com/products"},
        result=result,
        tenant_id="tenant-a",
    )
    second = promoter.candidate_from_result(
        spec=_spec(),
        payload={"target": "https://example.com/products"},
        result=result,
        tenant_id="tenant-a",
    )

    assert first is not None
    assert second is not None
    assert first.fixture_id == second.fixture_id
    assert first.trigger_reasons == ("run_failed", "low_confidence")
    assert "run_should_not_fail_after_fix" in first.expected_assertions
