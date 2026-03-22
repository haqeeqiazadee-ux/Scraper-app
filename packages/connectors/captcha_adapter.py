"""
CAPTCHA Adapter — multi-service CAPTCHA solving with cost tracking.

Ported and refactored from scraper_pro/engine_v2.py CaptchaSolver.
Supports 2Captcha, Anti-Captcha, CapMonster with automatic fallback.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


class CaptchaType(StrEnum):
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    IMAGE = "image"


@dataclass
class CaptchaSolution:
    """Result of a CAPTCHA solve attempt."""

    success: bool
    solution: str = ""
    solver_name: str = ""
    cost_usd: float = 0.0
    elapsed_ms: int = 0
    error: Optional[str] = None


@runtime_checkable
class CaptchaSolver(Protocol):
    """Interface for CAPTCHA solving services."""

    async def solve(
        self,
        captcha_type: CaptchaType,
        site_key: str,
        page_url: str,
    ) -> CaptchaSolution: ...

    def get_name(self) -> str: ...


class CaptchaAdapter:
    """CAPTCHA adapter with multi-service fallback and cost tracking."""

    def __init__(self) -> None:
        self._solvers: list[CaptchaSolver] = []
        self._total_cost_usd: float = 0.0
        self._total_solves: int = 0
        self._total_failures: int = 0

    def add_solver(self, solver: CaptchaSolver) -> None:
        """Add a CAPTCHA solver to the fallback chain."""
        self._solvers.append(solver)

    async def solve(
        self,
        captcha_type: CaptchaType,
        site_key: str,
        page_url: str,
        max_attempts: int = 3,
    ) -> CaptchaSolution:
        """Attempt to solve a CAPTCHA using available solvers with fallback."""
        for solver in self._solvers:
            for attempt in range(max_attempts):
                try:
                    solution = await solver.solve(captcha_type, site_key, page_url)
                    if solution.success:
                        self._total_cost_usd += solution.cost_usd
                        self._total_solves += 1
                        logger.info(
                            "CAPTCHA solved",
                            extra={
                                "solver": solver.get_name(),
                                "type": captcha_type,
                                "cost": solution.cost_usd,
                                "attempt": attempt + 1,
                            },
                        )
                        return solution
                except Exception as e:
                    logger.warning(
                        "CAPTCHA solve failed",
                        extra={"solver": solver.get_name(), "attempt": attempt + 1, "error": str(e)},
                    )

        self._total_failures += 1
        return CaptchaSolution(
            success=False,
            error="All CAPTCHA solvers exhausted",
        )

    @property
    def total_cost_usd(self) -> float:
        return self._total_cost_usd

    @property
    def stats(self) -> dict:
        return {
            "total_solves": self._total_solves,
            "total_failures": self._total_failures,
            "total_cost_usd": self._total_cost_usd,
        }
