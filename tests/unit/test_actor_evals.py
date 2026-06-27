from __future__ import annotations


def test_actor_quality_eval_passes_complete_output() -> None:
    from packages.core.actor_runtime import evaluate_actor_output

    result = evaluate_actor_output(
        {
            "extracted_data": [{"name": "Item A", "price": "$10"}],
            "item_count": 1,
            "confidence": 0.9,
        },
        requested_fields=("name", "price"),
    )

    assert result.passed is True
    assert result.score >= 0.9
    assert result.missing_required_fields == ()


def test_actor_quality_eval_fails_missing_required_fields() -> None:
    from packages.core.actor_runtime import evaluate_actor_output

    result = evaluate_actor_output(
        {
            "extracted_data": [{"name": "Item A"}],
            "item_count": 1,
            "confidence": 0.9,
        },
        requested_fields=("name", "price"),
    )

    assert result.passed is False
    assert result.missing_required_fields == ("price",)
