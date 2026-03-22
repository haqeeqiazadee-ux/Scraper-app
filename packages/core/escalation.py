"""
Lane Escalation Manager — handles automatic escalation between execution lanes.

When a lane fails or produces low-confidence results, escalation kicks in:
HTTP → Browser → Hard-Target

Integrates with ExecutionRouter to track outcomes and improve future routing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from packages.core.router import ExecutionRouter, Lane, RouteDecision

logger = logging.getLogger(__name__)

MAX_ESCALATION_DEPTH = 3


@dataclass
class EscalationContext:
    """Tracks escalation state for a single task."""

    task_id: str
    original_lane: Lane
    current_lane: Lane
    attempts: list[dict] = field(default_factory=list)
    depth: int = 0

    @property
    def can_escalate(self) -> bool:
        return self.depth < MAX_ESCALATION_DEPTH

    @property
    def is_exhausted(self) -> bool:
        return self.depth >= MAX_ESCALATION_DEPTH


class EscalationManager:
    """Manages lane escalation for failed or low-confidence extractions."""

    def __init__(self, router: ExecutionRouter, confidence_threshold: float = 0.3) -> None:
        self._router = router
        self._confidence_threshold = confidence_threshold
        self._active_contexts: dict[str, EscalationContext] = {}

    def should_escalate(self, result: dict) -> bool:
        """Determine if a result warrants escalation to a higher lane."""
        # Explicit escalation flag from worker
        if result.get("should_escalate", False):
            return True

        # Failed status always escalates
        if result.get("status") == "failed":
            return True

        # Low confidence with no items
        if result.get("item_count", 0) == 0:
            return True

        # Low confidence below threshold
        confidence = result.get("confidence", 0.0)
        if confidence < self._confidence_threshold and result.get("item_count", 0) > 0:
            return True

        return False

    def get_escalation(self, task_id: str, current_result: dict, route_decision: RouteDecision) -> Optional[Lane]:
        """Get the next lane to escalate to, or None if exhausted."""
        # Get or create context
        if task_id not in self._active_contexts:
            self._active_contexts[task_id] = EscalationContext(
                task_id=task_id,
                original_lane=route_decision.lane,
                current_lane=route_decision.lane,
            )

        ctx = self._active_contexts[task_id]

        # Record attempt
        ctx.attempts.append({
            "lane": ctx.current_lane.value,
            "status": current_result.get("status"),
            "confidence": current_result.get("confidence", 0.0),
            "item_count": current_result.get("item_count", 0),
        })

        if not ctx.can_escalate:
            logger.warning("Escalation exhausted", extra={"task_id": task_id, "depth": ctx.depth})
            return None

        # Get next lane from route decision fallbacks
        next_lane = self._router.get_next_lane(
            RouteDecision(
                lane=ctx.current_lane,
                reason="escalation",
                fallback_lanes=[l for l in route_decision.fallback_lanes if l != ctx.current_lane],
            )
        )

        if next_lane is None:
            logger.info("No more fallback lanes", extra={"task_id": task_id})
            return None

        ctx.current_lane = next_lane
        ctx.depth += 1

        # Record outcome in router for future decisions
        domain = self._extract_domain(current_result.get("url", ""))
        if domain:
            self._router.record_outcome(domain, Lane(current_result.get("lane", "http")), success=False)

        logger.info(
            "Escalating task",
            extra={"task_id": task_id, "from": ctx.attempts[-1]["lane"], "to": next_lane.value, "depth": ctx.depth},
        )

        return next_lane

    def complete(self, task_id: str, final_result: dict) -> None:
        """Mark escalation as complete and record final outcome."""
        ctx = self._active_contexts.pop(task_id, None)
        if ctx:
            domain = self._extract_domain(final_result.get("url", ""))
            success = final_result.get("status") == "success" and final_result.get("item_count", 0) > 0
            if domain:
                self._router.record_outcome(domain, ctx.current_lane, success=success)

    def get_context(self, task_id: str) -> Optional[EscalationContext]:
        """Get the current escalation context for a task."""
        return self._active_contexts.get(task_id)

    def _extract_domain(self, url: str) -> str:
        if not url:
            return ""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
