"""
Human Behavior Simulation — realistic mouse, scroll, and timing patterns.

Generates Bezier-curve mouse movements, variable-speed scrolling, idle jitter,
and log-normal request delays. Used by browser-based connectors to defeat
behavioral analysis (DataDome, PerimeterX/HUMAN).

Key principles:
- No straight-line mouse paths (use cubic Bezier curves)
- No uniform random delays (use log-normal distribution)
- Add idle micro-movements between actions
- Scroll with variable velocity (accelerate/decelerate)
- Click requires moving to target first
"""

from __future__ import annotations

import asyncio
import math
import random
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Point:
    x: float
    y: float


def _bezier_curve(start: Point, end: Point, num_points: int = 20) -> list[Point]:
    """Generate a cubic Bezier curve between two points with random control points.

    Real mouse movements follow curved paths with variable speed.
    """
    # Control points offset randomly from the straight line
    dx = end.x - start.x
    dy = end.y - start.y

    # Random perpendicular offsets for control points
    perp_x = -dy
    perp_y = dx
    magnitude = math.sqrt(perp_x ** 2 + perp_y ** 2) or 1.0
    perp_x /= magnitude
    perp_y /= magnitude

    offset1 = random.uniform(-0.3, 0.3)
    offset2 = random.uniform(-0.3, 0.3)

    cp1 = Point(
        start.x + dx * 0.25 + perp_x * offset1 * abs(dx + dy),
        start.y + dy * 0.25 + perp_y * offset1 * abs(dx + dy),
    )
    cp2 = Point(
        start.x + dx * 0.75 + perp_x * offset2 * abs(dx + dy),
        start.y + dy * 0.75 + perp_y * offset2 * abs(dx + dy),
    )

    points = []
    for i in range(num_points + 1):
        t = i / num_points
        inv_t = 1 - t
        # Cubic Bezier: B(t) = (1-t)^3*P0 + 3*(1-t)^2*t*P1 + 3*(1-t)*t^2*P2 + t^3*P3
        x = (inv_t ** 3 * start.x +
             3 * inv_t ** 2 * t * cp1.x +
             3 * inv_t * t ** 2 * cp2.x +
             t ** 3 * end.x)
        y = (inv_t ** 3 * start.y +
             3 * inv_t ** 2 * t * cp1.y +
             3 * inv_t * t ** 2 * cp2.y +
             t ** 3 * end.y)
        points.append(Point(x, y))

    return points


def log_normal_delay(median: float = 2.0, sigma: float = 0.5) -> float:
    """Generate a log-normal delay matching real human browsing patterns.

    Log-normal distribution produces mostly short delays with occasional
    longer pauses — matching real user behavior better than uniform random.

    Args:
        median: Median delay in seconds (most common value).
        sigma: Shape parameter (higher = more spread/variance).

    Returns:
        Delay in seconds (always positive, typically 0.5–8s).
    """
    mu = math.log(median)
    delay = random.lognormvariate(mu, sigma)
    # Clamp to reasonable range
    return max(0.3, min(delay, 15.0))


async def human_delay(median: float = 2.0, sigma: float = 0.5) -> None:
    """Sleep for a human-realistic log-normal duration."""
    await asyncio.sleep(log_normal_delay(median, sigma))


async def move_mouse_to(page: Any, target_x: float, target_y: float, current_pos: Optional[Point] = None) -> Point:
    """Move mouse to target via a Bezier curve with variable speed.

    Args:
        page: Playwright page object.
        target_x: Target X coordinate.
        target_y: Target Y coordinate.
        current_pos: Current mouse position (random if None).

    Returns:
        Final mouse position.
    """
    if current_pos is None:
        current_pos = Point(
            random.uniform(100, 800),
            random.uniform(100, 500),
        )

    target = Point(target_x, target_y)
    distance = math.sqrt((target.x - current_pos.x) ** 2 + (target.y - current_pos.y) ** 2)

    # More points for longer distances
    num_points = max(10, min(int(distance / 10), 50))
    path = _bezier_curve(current_pos, target, num_points)

    for point in path:
        await page.mouse.move(point.x, point.y)
        # Variable speed: faster in middle, slower at start/end
        await asyncio.sleep(random.uniform(0.001, 0.008))

    return target


async def human_click(page: Any, selector: str, current_pos: Optional[Point] = None) -> Point:
    """Click an element with realistic mouse movement to it first.

    Moves along a Bezier curve to the element center, pauses briefly,
    then clicks. Returns the new mouse position.
    """
    try:
        element = await page.query_selector(selector)
        if not element:
            return current_pos or Point(400, 400)

        box = await element.bounding_box()
        if not box:
            await element.click()
            return current_pos or Point(400, 400)

        # Target: random point within the element (not dead center)
        target_x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
        target_y = box["y"] + box["height"] * random.uniform(0.3, 0.7)

        # Move to target
        pos = await move_mouse_to(page, target_x, target_y, current_pos)

        # Brief pause before clicking (humans don't click instantly on arrival)
        await asyncio.sleep(random.uniform(0.05, 0.2))

        await page.mouse.click(pos.x, pos.y)
        return pos
    except Exception:
        # Fallback to direct click
        try:
            await page.click(selector)
        except Exception:
            pass
        return current_pos or Point(400, 400)


async def human_scroll(page: Any, distance: int = 800, direction: str = "down") -> None:
    """Scroll with variable velocity — accelerate at start, decelerate at end.

    Mimics real scroll behavior: fast middle section with gentle start/stop.
    """
    if direction == "up":
        distance = -abs(distance)

    total = abs(distance)
    scrolled = 0
    steps = random.randint(5, 12)

    for i in range(steps):
        # Sinusoidal speed profile: slow-fast-slow
        progress = i / steps
        speed_factor = math.sin(progress * math.pi)  # 0 → 1 → 0
        step_size = max(20, int((total / steps) * (0.3 + 1.4 * speed_factor)))

        remaining = total - scrolled
        step_size = min(step_size, remaining)
        if step_size <= 0:
            break

        delta = step_size if distance > 0 else -step_size
        await page.mouse.wheel(0, delta)
        scrolled += step_size

        # Variable pause between scroll steps
        await asyncio.sleep(random.uniform(0.02, 0.1))

    # Occasional micro-pause after scrolling (reading behavior)
    if random.random() < 0.3:
        await asyncio.sleep(random.uniform(0.5, 2.0))


async def idle_jitter(page: Any, duration: float = 1.0) -> None:
    """Simulate idle mouse micro-movements.

    Real users constantly fidget their mouse even when "idle" — the cursor
    is never perfectly still. This defeats idle-detection heuristics.
    """
    start = asyncio.get_event_loop().time()
    pos = Point(random.uniform(200, 800), random.uniform(200, 500))

    while (asyncio.get_event_loop().time() - start) < duration:
        # Tiny random movements (1-5 pixels)
        dx = random.uniform(-5, 5)
        dy = random.uniform(-5, 5)
        pos = Point(
            max(0, min(1920, pos.x + dx)),
            max(0, min(1080, pos.y + dy)),
        )
        await page.mouse.move(pos.x, pos.y)
        await asyncio.sleep(random.uniform(0.1, 0.4))


async def warm_up_navigation(page: Any, target_url: str) -> None:
    """Visit the homepage and optionally a category page before the target.

    Establishes session credibility by mimicking a real user's navigation
    path. Direct deep-link access with no referrer is suspicious.
    """
    from urllib.parse import urlparse

    parsed = urlparse(target_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    try:
        # Step 1: Visit homepage
        await page.goto(base_url, wait_until="domcontentloaded", timeout=15000)
        await human_delay(median=1.5, sigma=0.4)

        # Optional: small scroll on homepage
        await human_scroll(page, distance=random.randint(200, 600))
        await idle_jitter(page, duration=random.uniform(0.5, 1.5))

        # Step 2: 40% chance to visit an intermediate page
        if random.random() < 0.4 and parsed.path and parsed.path != "/":
            # Navigate to a plausible intermediate path
            path_parts = [p for p in parsed.path.strip("/").split("/") if p]
            if len(path_parts) > 1:
                intermediate = f"{base_url}/{path_parts[0]}/"
                try:
                    await page.goto(intermediate, wait_until="domcontentloaded", timeout=10000)
                    await human_delay(median=1.0, sigma=0.3)
                    await human_scroll(page, distance=random.randint(100, 400))
                except Exception:
                    pass  # Intermediate page might 404 — that's fine

    except Exception as e:
        # Warm-up failure is non-fatal — proceed to target
        import logging
        logging.getLogger(__name__).debug("Warm-up navigation failed: %s", e)
