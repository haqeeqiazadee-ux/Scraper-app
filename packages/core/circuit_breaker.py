"""
Circuit Breaker — stop wasting resources on consistently-failing domains.

Implements the circuit breaker pattern per domain:
- CLOSED: Normal operation, requests pass through
- OPEN: Domain is failing, requests are rejected immediately (saves resources)
- HALF_OPEN: After cooldown, allow one probe request to test recovery

This prevents the scraper from burning proxies, browser sessions, and CAPTCHA
credits on domains that are consistently blocking or timing out.

Usage:
    breaker = CircuitBreaker()
    if breaker.can_request("amazon.com"):
        result = await fetch(url)
        if result.ok:
            breaker.record_success("amazon.com")
        else:
            breaker.record_failure("amazon.com")
    else:
        # Domain is circuit-broken, skip or queue for later
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional

logger = logging.getLogger(__name__)


class CircuitState(StrEnum):
    CLOSED = "closed"        # Normal — requests pass through
    OPEN = "open"            # Broken — reject immediately
    HALF_OPEN = "half_open"  # Probing — allow one test request


@dataclass
class DomainCircuit:
    """Circuit state for a single domain."""

    domain: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    consecutive_failures: int = 0
    last_failure_time: float = 0.0
    last_success_time: float = 0.0
    opened_at: float = 0.0
    half_open_attempts: int = 0


class CircuitBreaker:
    """Per-domain circuit breaker to stop wasting resources on failing domains.

    Configuration:
        failure_threshold: Number of consecutive failures to trip the circuit (default: 5)
        recovery_timeout: Seconds to wait before probing (OPEN → HALF_OPEN) (default: 300 = 5 min)
        success_threshold: Successes in HALF_OPEN needed to close circuit (default: 2)
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 300.0,
        success_threshold: int = 2,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._success_threshold = success_threshold
        self._circuits: dict[str, DomainCircuit] = {}

    def _get_circuit(self, domain: str) -> DomainCircuit:
        """Get or create a circuit for a domain."""
        domain = self._normalize_domain(domain)
        if domain not in self._circuits:
            self._circuits[domain] = DomainCircuit(domain=domain)
        return self._circuits[domain]

    def _normalize_domain(self, domain: str) -> str:
        """Normalize domain string."""
        domain = domain.lower().strip()
        if domain.startswith("www."):
            domain = domain[4:]
        # Handle full URLs
        if "://" in domain:
            from urllib.parse import urlparse
            domain = urlparse(domain).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
        return domain

    def can_request(self, domain: str) -> bool:
        """Check if a request to this domain should proceed.

        Returns True if the circuit is CLOSED or transitioning to HALF_OPEN.
        Returns False if the circuit is OPEN (domain is failing).
        """
        circuit = self._get_circuit(domain)

        if circuit.state == CircuitState.CLOSED:
            return True

        if circuit.state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            elapsed = time.time() - circuit.opened_at
            if elapsed >= self._recovery_timeout:
                circuit.state = CircuitState.HALF_OPEN
                circuit.half_open_attempts = 0
                logger.info(
                    "Circuit breaker HALF_OPEN for %s (probing after %.0fs cooldown)",
                    domain, elapsed,
                )
                return True
            return False

        if circuit.state == CircuitState.HALF_OPEN:
            # Allow limited probe requests
            return circuit.half_open_attempts < self._success_threshold
        return True

    def record_success(self, domain: str) -> None:
        """Record a successful request to a domain."""
        circuit = self._get_circuit(domain)
        circuit.success_count += 1
        circuit.consecutive_failures = 0
        circuit.last_success_time = time.time()

        if circuit.state == CircuitState.HALF_OPEN:
            circuit.half_open_attempts += 1
            if circuit.half_open_attempts >= self._success_threshold:
                circuit.state = CircuitState.CLOSED
                logger.info(
                    "Circuit breaker CLOSED for %s (recovered after %d successes)",
                    domain, circuit.half_open_attempts,
                )

    def record_failure(self, domain: str) -> None:
        """Record a failed request to a domain."""
        circuit = self._get_circuit(domain)
        circuit.failure_count += 1
        circuit.consecutive_failures += 1
        circuit.last_failure_time = time.time()

        if circuit.state == CircuitState.HALF_OPEN:
            # Probe failed — reopen the circuit
            circuit.state = CircuitState.OPEN
            circuit.opened_at = time.time()
            logger.warning(
                "Circuit breaker re-OPENED for %s (probe failed)",
                domain,
            )
            return

        if circuit.state == CircuitState.CLOSED:
            if circuit.consecutive_failures >= self._failure_threshold:
                circuit.state = CircuitState.OPEN
                circuit.opened_at = time.time()
                logger.warning(
                    "Circuit breaker OPENED for %s (%d consecutive failures)",
                    domain, circuit.consecutive_failures,
                )

    def get_state(self, domain: str) -> CircuitState:
        """Get the current circuit state for a domain."""
        return self._get_circuit(domain).state

    def get_stats(self, domain: str) -> dict:
        """Get circuit stats for a domain."""
        c = self._get_circuit(domain)
        return {
            "domain": c.domain,
            "state": c.state,
            "failure_count": c.failure_count,
            "success_count": c.success_count,
            "consecutive_failures": c.consecutive_failures,
        }

    def reset(self, domain: str) -> None:
        """Manually reset a domain's circuit."""
        domain = self._normalize_domain(domain)
        if domain in self._circuits:
            del self._circuits[domain]

    def get_open_circuits(self) -> list[str]:
        """Get list of domains with open circuits."""
        return [d for d, c in self._circuits.items() if c.state == CircuitState.OPEN]
