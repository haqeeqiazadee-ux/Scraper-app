"""Tests for human behavioral simulation.

Covers:
- Bezier curve generation (curved paths, not straight lines)
- Log-normal delay distribution (matches real browsing patterns)
- Mouse movement (visits intermediate points)
- Human scroll (variable velocity)
- Idle jitter (micro-movements)
"""

import math
from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.core.human_behavior import (
    Point,
    _bezier_curve,
    human_click,
    human_delay,
    human_scroll,
    idle_jitter,
    log_normal_delay,
    move_mouse_to,
)


# ---------------------------------------------------------------------------
# Bezier curve
# ---------------------------------------------------------------------------


class TestBezierCurve:

    def test_curve_starts_at_start(self) -> None:
        """Bezier curve starts at the start point."""
        start = Point(0, 0)
        end = Point(100, 100)
        points = _bezier_curve(start, end, num_points=20)
        assert abs(points[0].x - start.x) < 1
        assert abs(points[0].y - start.y) < 1

    def test_curve_ends_at_end(self) -> None:
        """Bezier curve ends at the end point."""
        start = Point(0, 0)
        end = Point(100, 100)
        points = _bezier_curve(start, end, num_points=20)
        assert abs(points[-1].x - end.x) < 1
        assert abs(points[-1].y - end.y) < 1

    def test_curve_has_correct_point_count(self) -> None:
        """Bezier curve has num_points + 1 points."""
        points = _bezier_curve(Point(0, 0), Point(100, 100), num_points=15)
        assert len(points) == 16  # num_points + 1

    def test_curve_is_not_straight_line(self) -> None:
        """Bezier curve deviates from a straight line (has curvature)."""
        start = Point(0, 0)
        end = Point(200, 0)
        # Generate many curves and check at least some deviate from y=0
        deviations = []
        for _ in range(20):
            points = _bezier_curve(start, end, num_points=20)
            max_y_deviation = max(abs(p.y) for p in points[1:-1])
            deviations.append(max_y_deviation)
        # At least some curves should deviate from straight line
        assert max(deviations) > 1.0, "All curves were straight — Bezier control points should add curvature"

    def test_curve_varies_between_calls(self) -> None:
        """Multiple Bezier curves between same endpoints are different (random control points)."""
        start = Point(0, 0)
        end = Point(100, 100)
        midpoints = []
        for _ in range(10):
            points = _bezier_curve(start, end, num_points=10)
            midpoints.append((points[5].x, points[5].y))
        unique_midpoints = set(midpoints)
        assert len(unique_midpoints) > 1, "Curves should vary between calls"


# ---------------------------------------------------------------------------
# Log-normal delay
# ---------------------------------------------------------------------------


class TestLogNormalDelay:

    def test_delay_is_positive(self) -> None:
        """Delay is always positive."""
        for _ in range(100):
            d = log_normal_delay(median=2.0, sigma=0.5)
            assert d > 0

    def test_delay_is_bounded(self) -> None:
        """Delay is clamped to [0.3, 15.0] range."""
        for _ in range(200):
            d = log_normal_delay(median=2.0, sigma=0.5)
            assert 0.3 <= d <= 15.0

    def test_delay_median_is_reasonable(self) -> None:
        """Median of many samples is close to the requested median."""
        samples = sorted([log_normal_delay(median=2.0, sigma=0.3) for _ in range(1000)])
        actual_median = samples[500]
        assert 1.0 < actual_median < 4.0, f"Median {actual_median} too far from 2.0"

    def test_delay_is_not_uniform(self) -> None:
        """Distribution is NOT uniform — most values cluster near median."""
        samples = [log_normal_delay(median=2.0, sigma=0.5) for _ in range(500)]
        near_median = sum(1 for s in samples if 1.0 < s < 3.5)
        # Majority should be near median
        assert near_median > 250, f"Only {near_median}/500 near median — distribution may be wrong"


# ---------------------------------------------------------------------------
# Mouse movement
# ---------------------------------------------------------------------------


class TestMouseMovement:

    @pytest.mark.asyncio
    async def test_move_mouse_calls_page_mouse_move(self) -> None:
        """move_mouse_to calls page.mouse.move multiple times along a path."""
        page = AsyncMock()
        page.mouse = AsyncMock()
        page.mouse.move = AsyncMock()

        result = await move_mouse_to(page, 500, 300, current_pos=Point(100, 100))

        assert page.mouse.move.call_count >= 10, "Should move through multiple intermediate points"
        assert abs(result.x - 500) < 1
        assert abs(result.y - 300) < 1

    @pytest.mark.asyncio
    async def test_move_mouse_from_random_start(self) -> None:
        """If no current_pos, starts from a random position."""
        page = AsyncMock()
        page.mouse = AsyncMock()
        page.mouse.move = AsyncMock()

        result = await move_mouse_to(page, 500, 300)
        assert page.mouse.move.call_count >= 10


# ---------------------------------------------------------------------------
# Human click
# ---------------------------------------------------------------------------


class TestHumanClick:

    @pytest.mark.asyncio
    async def test_click_moves_then_clicks(self) -> None:
        """human_click moves to element then clicks."""
        page = AsyncMock()
        page.mouse = AsyncMock()
        page.mouse.move = AsyncMock()
        page.mouse.click = AsyncMock()

        element = AsyncMock()
        element.bounding_box = AsyncMock(return_value={"x": 100, "y": 200, "width": 80, "height": 30})
        page.query_selector = AsyncMock(return_value=element)

        result = await human_click(page, "button.submit")

        assert page.mouse.move.call_count >= 5, "Should move mouse to target"
        assert page.mouse.click.call_count == 1, "Should click once"

    @pytest.mark.asyncio
    async def test_click_fallback_on_missing_element(self) -> None:
        """Falls back to direct click if element not found."""
        page = AsyncMock()
        page.mouse = AsyncMock()
        page.query_selector = AsyncMock(return_value=None)

        result = await human_click(page, "button.missing")
        assert isinstance(result, Point)


# ---------------------------------------------------------------------------
# Scroll simulation
# ---------------------------------------------------------------------------


class TestHumanScroll:

    @pytest.mark.asyncio
    async def test_scroll_calls_mouse_wheel(self) -> None:
        """human_scroll calls page.mouse.wheel multiple times."""
        page = AsyncMock()
        page.mouse = AsyncMock()
        page.mouse.wheel = AsyncMock()

        await human_scroll(page, distance=800)

        assert page.mouse.wheel.call_count >= 5, "Should scroll in multiple steps"

    @pytest.mark.asyncio
    async def test_scroll_up(self) -> None:
        """Scroll up passes negative delta."""
        page = AsyncMock()
        page.mouse = AsyncMock()
        page.mouse.wheel = AsyncMock()

        await human_scroll(page, distance=400, direction="up")

        # Check at least one wheel call had negative delta
        for call in page.mouse.wheel.call_args_list:
            _, delta = call[0]
            if delta < 0:
                break
        else:
            pytest.fail("No negative scroll delta found for upward scroll")


# ---------------------------------------------------------------------------
# Idle jitter
# ---------------------------------------------------------------------------


class TestIdleJitter:

    @pytest.mark.asyncio
    async def test_jitter_moves_mouse(self) -> None:
        """idle_jitter makes small mouse movements."""
        page = AsyncMock()
        page.mouse = AsyncMock()
        page.mouse.move = AsyncMock()

        # Very short duration to keep test fast
        await idle_jitter(page, duration=0.3)

        assert page.mouse.move.call_count >= 1, "Should make at least one micro-movement"
