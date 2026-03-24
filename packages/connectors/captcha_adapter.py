"""
CAPTCHA Adapter — multi-service CAPTCHA solving with cost tracking.

Ported and refactored from scraper_pro/engine_v2.py CaptchaSolver.
Supports 2Captcha, Anti-Captcha, CapMonster with automatic fallback.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


class CaptchaType(StrEnum):
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    TURNSTILE = "turnstile"
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


# ---------------------------------------------------------------------------
# Concrete solver implementations
# ---------------------------------------------------------------------------

class TwoCaptchaSolver:
    """2Captcha.com CAPTCHA solving service."""

    API_SUBMIT = "http://2captcha.com/in.php"
    API_RESULT = "http://2captcha.com/res.php"
    COST_PER_SOLVE = 0.003  # ~$2.99 per 1000

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def get_name(self) -> str:
        return "2captcha"

    async def solve(
        self,
        captcha_type: CaptchaType,
        site_key: str,
        page_url: str,
    ) -> CaptchaSolution:
        start = time.time()
        try:
            import httpx
        except ImportError:
            return CaptchaSolution(success=False, solver_name=self.get_name(), error="httpx not installed")

        method_map = {
            CaptchaType.RECAPTCHA_V2: "userrecaptcha",
            CaptchaType.RECAPTCHA_V3: "userrecaptcha",
            CaptchaType.HCAPTCHA: "hcaptcha",
        }
        method = method_map.get(captcha_type)
        if not method:
            return CaptchaSolution(success=False, solver_name=self.get_name(), error=f"Unsupported type: {captcha_type}")

        async with httpx.AsyncClient(timeout=10) as client:
            # Submit
            submit_data = {
                "key": self._api_key,
                "method": method,
                "googlekey" if captcha_type != CaptchaType.HCAPTCHA else "sitekey": site_key,
                "pageurl": page_url,
                "json": "1",
            }
            resp = await client.post(self.API_SUBMIT, data=submit_data)
            result = resp.json()

            if result.get("status") != 1:
                return CaptchaSolution(
                    success=False, solver_name=self.get_name(),
                    error=result.get("request", "submit failed"),
                    elapsed_ms=int((time.time() - start) * 1000),
                )

            captcha_id = result["request"]

            # Poll (max 30 × 5s = 150s)
            for _ in range(30):
                await asyncio.sleep(5)
                resp = await client.get(
                    self.API_RESULT,
                    params={"key": self._api_key, "action": "get", "id": captcha_id, "json": "1"},
                )
                result = resp.json()
                if result.get("status") == 1:
                    return CaptchaSolution(
                        success=True,
                        solution=result["request"],
                        solver_name=self.get_name(),
                        cost_usd=self.COST_PER_SOLVE,
                        elapsed_ms=int((time.time() - start) * 1000),
                    )
                if result.get("request") != "CAPCHA_NOT_READY":
                    return CaptchaSolution(
                        success=False, solver_name=self.get_name(),
                        error=result.get("request", "unknown error"),
                        elapsed_ms=int((time.time() - start) * 1000),
                    )

        return CaptchaSolution(
            success=False, solver_name=self.get_name(), error="timeout",
            elapsed_ms=int((time.time() - start) * 1000),
        )


class AntiCaptchaSolver:
    """Anti-Captcha.com CAPTCHA solving service."""

    API_BASE = "https://api.anti-captcha.com"
    COST_PER_SOLVE = 0.002

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def get_name(self) -> str:
        return "anti-captcha"

    async def solve(
        self,
        captcha_type: CaptchaType,
        site_key: str,
        page_url: str,
    ) -> CaptchaSolution:
        start = time.time()
        try:
            import httpx
        except ImportError:
            return CaptchaSolution(success=False, solver_name=self.get_name(), error="httpx not installed")

        task_type_map = {
            CaptchaType.RECAPTCHA_V2: "RecaptchaV2TaskProxyless",
            CaptchaType.RECAPTCHA_V3: "RecaptchaV3TaskProxyless",
            CaptchaType.HCAPTCHA: "HCaptchaTaskProxyless",
        }
        task_type = task_type_map.get(captcha_type)
        if not task_type:
            return CaptchaSolution(success=False, solver_name=self.get_name(), error=f"Unsupported type: {captcha_type}")

        async with httpx.AsyncClient(timeout=10) as client:
            # Create task
            payload = {
                "clientKey": self._api_key,
                "task": {"type": task_type, "websiteURL": page_url, "websiteKey": site_key},
            }
            resp = await client.post(f"{self.API_BASE}/createTask", json=payload)
            result = resp.json()

            if result.get("errorId", 1) != 0:
                return CaptchaSolution(
                    success=False, solver_name=self.get_name(),
                    error=result.get("errorDescription", "submit failed"),
                    elapsed_ms=int((time.time() - start) * 1000),
                )

            task_id = result["taskId"]

            # Poll
            for _ in range(30):
                await asyncio.sleep(5)
                resp = await client.post(
                    f"{self.API_BASE}/getTaskResult",
                    json={"clientKey": self._api_key, "taskId": task_id},
                )
                result = resp.json()
                if result.get("status") == "ready":
                    solution_key = "gRecaptchaResponse" if "recaptcha" in captcha_type else "token"
                    return CaptchaSolution(
                        success=True,
                        solution=result.get("solution", {}).get(solution_key, ""),
                        solver_name=self.get_name(),
                        cost_usd=result.get("cost", self.COST_PER_SOLVE),
                        elapsed_ms=int((time.time() - start) * 1000),
                    )
                if result.get("errorId", 0) != 0:
                    return CaptchaSolution(
                        success=False, solver_name=self.get_name(),
                        error=result.get("errorDescription", "unknown error"),
                        elapsed_ms=int((time.time() - start) * 1000),
                    )

        return CaptchaSolution(
            success=False, solver_name=self.get_name(), error="timeout",
            elapsed_ms=int((time.time() - start) * 1000),
        )


class CapSolverSolver:
    """CapSolver.com CAPTCHA solving service — fast and cost-effective."""

    API_BASE = "https://api.capsolver.com"
    COST_PER_SOLVE = 0.001  # ~$0.50-$1.50 per 1000

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def get_name(self) -> str:
        return "capsolver"

    async def solve(
        self,
        captcha_type: CaptchaType,
        site_key: str,
        page_url: str,
    ) -> CaptchaSolution:
        start = time.time()
        try:
            import httpx
        except ImportError:
            return CaptchaSolution(success=False, solver_name=self.get_name(), error="httpx not installed")

        task_type_map = {
            CaptchaType.RECAPTCHA_V2: "ReCaptchaV2TaskProxyLess",
            CaptchaType.RECAPTCHA_V3: "ReCaptchaV3TaskProxyLess",
            CaptchaType.HCAPTCHA: "HCaptchaTaskProxyLess",
        }
        task_type = task_type_map.get(captcha_type)
        if not task_type:
            return CaptchaSolution(success=False, solver_name=self.get_name(), error=f"Unsupported type: {captcha_type}")

        async with httpx.AsyncClient(timeout=30) as client:
            # Create task
            payload = {
                "clientKey": self._api_key,
                "task": {
                    "type": task_type,
                    "websiteURL": page_url,
                    "websiteKey": site_key,
                },
            }
            if captcha_type == CaptchaType.RECAPTCHA_V3:
                payload["task"]["pageAction"] = "verify"
                payload["task"]["minScore"] = 0.7

            resp = await client.post(f"{self.API_BASE}/createTask", json=payload)
            result = resp.json()

            if result.get("errorId", 1) != 0:
                return CaptchaSolution(
                    success=False, solver_name=self.get_name(),
                    error=result.get("errorDescription", "submit failed"),
                    elapsed_ms=int((time.time() - start) * 1000),
                )

            task_id = result.get("taskId")

            # Poll for result (max 60 × 3s = 180s)
            for _ in range(60):
                await asyncio.sleep(3)
                resp = await client.post(
                    f"{self.API_BASE}/getTaskResult",
                    json={"clientKey": self._api_key, "taskId": task_id},
                )
                result = resp.json()
                if result.get("status") == "ready":
                    solution_obj = result.get("solution", {})
                    token = (
                        solution_obj.get("gRecaptchaResponse")
                        or solution_obj.get("token")
                        or ""
                    )
                    return CaptchaSolution(
                        success=True,
                        solution=token,
                        solver_name=self.get_name(),
                        cost_usd=self.COST_PER_SOLVE,
                        elapsed_ms=int((time.time() - start) * 1000),
                    )
                if result.get("errorId", 0) != 0:
                    return CaptchaSolution(
                        success=False, solver_name=self.get_name(),
                        error=result.get("errorDescription", "unknown error"),
                        elapsed_ms=int((time.time() - start) * 1000),
                    )

        return CaptchaSolution(
            success=False, solver_name=self.get_name(), error="timeout",
            elapsed_ms=int((time.time() - start) * 1000),
        )


class CapMonsterSolver:
    """CapMonster.cloud CAPTCHA solving service (API-compatible with Anti-Captcha)."""

    API_BASE = "https://api.capmonster.cloud"
    COST_PER_SOLVE = 0.001

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._delegate = AntiCaptchaSolver(api_key)
        # Override API base
        self._delegate.API_BASE = self.API_BASE

    def get_name(self) -> str:
        return "capmonster"

    async def solve(
        self,
        captcha_type: CaptchaType,
        site_key: str,
        page_url: str,
    ) -> CaptchaSolution:
        result = await self._delegate.solve(captcha_type, site_key, page_url)
        result.solver_name = self.get_name()
        if result.success:
            result.cost_usd = self.COST_PER_SOLVE
        return result


class NopeCHASolver:
    """NopeCHA CAPTCHA solving service — supports reCAPTCHA, hCaptcha, and Turnstile.

    API docs: https://developers.nopecha.com/token/
    Pricing: 20 credits for reCAPTCHA, 10 credits for hCaptcha, 1 credit for Turnstile.
    """

    API_BASE = "https://api.nopecha.com/token/"
    COST_PER_SOLVE = 0.002  # approximate USD cost

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def get_name(self) -> str:
        return "nopecha"

    async def solve(
        self,
        captcha_type: CaptchaType,
        site_key: str,
        page_url: str,
    ) -> CaptchaSolution:
        start = time.time()
        try:
            import httpx
        except ImportError:
            return CaptchaSolution(success=False, solver_name=self.get_name(), error="httpx not installed")

        type_map = {
            CaptchaType.RECAPTCHA_V2: "recaptcha2",
            CaptchaType.RECAPTCHA_V3: "recaptcha3",
            CaptchaType.HCAPTCHA: "hcaptcha",
            CaptchaType.TURNSTILE: "turnstile",
        }
        nopecha_type = type_map.get(captcha_type)
        if not nopecha_type:
            return CaptchaSolution(
                success=False, solver_name=self.get_name(),
                error=f"Unsupported type: {captcha_type}",
            )

        async with httpx.AsyncClient(timeout=30) as client:
            # Submit task
            payload: dict = {
                "key": self._api_key,
                "type": nopecha_type,
                "sitekey": site_key,
                "url": page_url,
            }
            resp = await client.post(self.API_BASE, json=payload)
            result = resp.json()

            if "error" in result:
                return CaptchaSolution(
                    success=False, solver_name=self.get_name(),
                    error=result.get("message", f"error code {result['error']}"),
                    elapsed_ms=int((time.time() - start) * 1000),
                )

            job_id = result.get("data")
            if not job_id:
                return CaptchaSolution(
                    success=False, solver_name=self.get_name(),
                    error="No job ID returned",
                    elapsed_ms=int((time.time() - start) * 1000),
                )

            # Poll for result (max 60 × 3s = 180s)
            for _ in range(60):
                await asyncio.sleep(3)
                resp = await client.get(
                    self.API_BASE,
                    params={"key": self._api_key, "id": job_id},
                )
                result = resp.json()

                if "error" in result:
                    if result["error"] == 14:
                        # Incomplete job — keep polling
                        continue
                    return CaptchaSolution(
                        success=False, solver_name=self.get_name(),
                        error=result.get("message", f"error code {result['error']}"),
                        elapsed_ms=int((time.time() - start) * 1000),
                    )

                token = result.get("data", "")
                if token:
                    return CaptchaSolution(
                        success=True,
                        solution=token,
                        solver_name=self.get_name(),
                        cost_usd=self.COST_PER_SOLVE,
                        elapsed_ms=int((time.time() - start) * 1000),
                    )

        return CaptchaSolution(
            success=False, solver_name=self.get_name(), error="timeout",
            elapsed_ms=int((time.time() - start) * 1000),
        )


# ---------------------------------------------------------------------------
# CAPTCHA escalation strategy
# ---------------------------------------------------------------------------

class CaptchaEscalationStrategy:
    """Determines when and how to handle CAPTCHA challenges during scraping."""

    def __init__(
        self,
        max_retries_before_captcha: int = 2,
        captcha_budget_usd: float = 1.0,
    ) -> None:
        self._max_retries = max_retries_before_captcha
        self._budget_usd = captcha_budget_usd
        self._spent_usd: float = 0.0

    def should_solve(self, attempt: int, adapter: CaptchaAdapter) -> bool:
        """Decide whether to attempt CAPTCHA solving."""
        if attempt < self._max_retries:
            return False  # Retry without solving first
        if self._spent_usd >= self._budget_usd:
            logger.warning("CAPTCHA budget exhausted", extra={"spent": self._spent_usd, "budget": self._budget_usd})
            return False
        if not adapter._solvers:
            return False
        return True

    def record_cost(self, cost_usd: float) -> None:
        self._spent_usd += cost_usd

    @property
    def budget_remaining(self) -> float:
        return max(0.0, self._budget_usd - self._spent_usd)


# ---------------------------------------------------------------------------
# Main adapter
# ---------------------------------------------------------------------------

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

    @classmethod
    def from_config(
        cls,
        capsolver_key: Optional[str] = None,
        two_captcha_key: Optional[str] = None,
        anti_captcha_key: Optional[str] = None,
        capmonster_key: Optional[str] = None,
        nopecha_key: Optional[str] = None,
    ) -> CaptchaAdapter:
        """Create adapter with solvers based on available API keys.

        CapSolver is preferred (cheapest + fastest) and tried first.
        NopeCHA is second (supports Turnstile + competitive pricing).
        """
        adapter = cls()
        if capsolver_key:
            adapter.add_solver(CapSolverSolver(capsolver_key))
        if nopecha_key:
            adapter.add_solver(NopeCHASolver(nopecha_key))
        if two_captcha_key:
            adapter.add_solver(TwoCaptchaSolver(two_captcha_key))
        if anti_captcha_key:
            adapter.add_solver(AntiCaptchaSolver(anti_captcha_key))
        if capmonster_key:
            adapter.add_solver(CapMonsterSolver(capmonster_key))
        return adapter

    async def solve(
        self,
        captcha_type: CaptchaType,
        site_key: str,
        page_url: str,
        max_attempts: int = 3,
    ) -> CaptchaSolution:
        """Attempt to solve a CAPTCHA using available solvers with fallback."""
        if not self._solvers:
            return CaptchaSolution(success=False, error="No CAPTCHA solvers configured")

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
    def solver_count(self) -> int:
        return len(self._solvers)

    @property
    def stats(self) -> dict:
        return {
            "total_solves": self._total_solves,
            "total_failures": self._total_failures,
            "total_cost_usd": self._total_cost_usd,
            "solvers": [s.get_name() for s in self._solvers],
        }
