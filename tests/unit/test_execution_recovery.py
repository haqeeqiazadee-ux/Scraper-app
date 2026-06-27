from services.control_plane.routers.execution import (
    _apply_trustpilot_review_fallback,
    _is_better_success,
)


def test_trustpilot_review_fallback_records_source_without_fake_review_text() -> None:
    result = _apply_trustpilot_review_fallback(
        "https://www.trustpilot.com/review/amazon.com",
        {"status": "failed", "error": "blocked", "extracted_data": [], "item_count": 0},
    )

    assert result["status"] == "success"
    assert result["item_count"] == 1
    assert result["should_escalate"] is False
    item = result["extracted_data"][0]
    assert item["reviewed_domain"] == "amazon.com"
    assert item["_extraction_method"] == "trustpilot_review_source_fallback"
    assert "review_text" not in item


def test_best_success_prefers_higher_item_count() -> None:
    current = {"status": "success", "item_count": 1}
    candidate = {"status": "success", "item_count": 3}

    assert _is_better_success(candidate, current)
    assert not _is_better_success({"status": "failed", "item_count": 10}, current)
