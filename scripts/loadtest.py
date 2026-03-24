"""
Locust load-testing script for the AI Scraping Platform control-plane.

Usage:
    pip install locust
    locust -f scripts/loadtest.py --host http://localhost:8000

Environment variables:
    LOCUST_TENANT_ID    — tenant header value (default: "load-test-tenant")
    LOCUST_JWT_SECRET   — JWT secret for token generation (default: "change-me-in-production")
"""

from __future__ import annotations

import json
import os
import uuid

from locust import HttpUser, between, task


TENANT_ID = os.environ.get("LOCUST_TENANT_ID", "load-test-tenant")


class ScraperUser(HttpUser):
    """Simulates a typical platform user interacting with the control-plane API."""

    wait_time = between(0.5, 2)

    def on_start(self) -> None:
        """Set up auth headers and create seed data."""
        self.headers = {
            "X-Tenant-ID": TENANT_ID,
            "Content-Type": "application/json",
        }
        self._task_ids: list[str] = []
        self._policy_ids: list[str] = []

    # ------------------------------------------------------------------
    # Health endpoints (lightweight, high frequency)
    # ------------------------------------------------------------------

    @task(10)
    def health_check(self) -> None:
        self.client.get("/health", name="/health")

    @task(5)
    def readiness_check(self) -> None:
        self.client.get("/ready", name="/ready")

    @task(3)
    def metrics(self) -> None:
        self.client.get("/metrics", name="/metrics")

    # ------------------------------------------------------------------
    # Task CRUD
    # ------------------------------------------------------------------

    @task(8)
    def create_task(self) -> None:
        payload = {
            "url": f"https://example.com/products/{uuid.uuid4().hex[:8]}",
            "task_type": "scrape",
            "priority": 5,
            "config": {"selectors": {"title": "h1", "price": ".price"}},
        }
        with self.client.post(
            "/api/v1/tasks",
            json=payload,
            headers=self.headers,
            name="/api/v1/tasks [POST]",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                data = resp.json()
                task_id = data.get("id") or data.get("task_id")
                if task_id:
                    self._task_ids.append(task_id)
                    # Cap stored IDs to avoid memory growth
                    if len(self._task_ids) > 200:
                        self._task_ids = self._task_ids[-100:]
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")

    @task(15)
    def list_tasks(self) -> None:
        self.client.get(
            "/api/v1/tasks",
            headers=self.headers,
            name="/api/v1/tasks [GET]",
        )

    @task(6)
    def get_task(self) -> None:
        if not self._task_ids:
            return
        task_id = self._task_ids[-1]
        self.client.get(
            f"/api/v1/tasks/{task_id}",
            headers=self.headers,
            name="/api/v1/tasks/:id [GET]",
        )

    @task(2)
    def delete_task(self) -> None:
        if not self._task_ids:
            return
        task_id = self._task_ids.pop(0)
        self.client.delete(
            f"/api/v1/tasks/{task_id}",
            headers=self.headers,
            name="/api/v1/tasks/:id [DELETE]",
        )

    # ------------------------------------------------------------------
    # Policy CRUD
    # ------------------------------------------------------------------

    @task(4)
    def create_policy(self) -> None:
        payload = {
            "name": f"loadtest-policy-{uuid.uuid4().hex[:6]}",
            "domain_pattern": "*.example.com",
            "rate_limit": 10,
            "config": {"lane": "http", "retry_count": 2},
        }
        with self.client.post(
            "/api/v1/policies",
            json=payload,
            headers=self.headers,
            name="/api/v1/policies [POST]",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                data = resp.json()
                policy_id = data.get("id") or data.get("policy_id")
                if policy_id:
                    self._policy_ids.append(policy_id)
                    if len(self._policy_ids) > 100:
                        self._policy_ids = self._policy_ids[-50:]
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")

    @task(8)
    def list_policies(self) -> None:
        self.client.get(
            "/api/v1/policies",
            headers=self.headers,
            name="/api/v1/policies [GET]",
        )

    # ------------------------------------------------------------------
    # Results & Export
    # ------------------------------------------------------------------

    @task(6)
    def list_results(self) -> None:
        self.client.get(
            "/api/v1/results",
            headers=self.headers,
            name="/api/v1/results [GET]",
        )

    @task(2)
    def get_task_results(self) -> None:
        if not self._task_ids:
            return
        task_id = self._task_ids[-1]
        self.client.get(
            f"/api/v1/tasks/{task_id}/results",
            headers=self.headers,
            name="/api/v1/tasks/:id/results [GET]",
        )

    # ------------------------------------------------------------------
    # Execution (route dry-run)
    # ------------------------------------------------------------------

    @task(3)
    def route_dryrun(self) -> None:
        payload = {
            "url": "https://example.com/products",
            "task_type": "scrape",
        }
        self.client.post(
            "/api/v1/route",
            json=payload,
            headers=self.headers,
            name="/api/v1/route [POST]",
        )

    # ------------------------------------------------------------------
    # Schedules
    # ------------------------------------------------------------------

    @task(4)
    def list_schedules(self) -> None:
        self.client.get(
            "/api/v1/schedules",
            headers=self.headers,
            name="/api/v1/schedules [GET]",
        )

    # ------------------------------------------------------------------
    # Connection check (deep probe)
    # ------------------------------------------------------------------

    @task(1)
    def check_connection(self) -> None:
        self.client.get(
            "/check-connection",
            name="/check-connection",
        )


class HighThroughputUser(HttpUser):
    """Simulates high-frequency read-heavy traffic (dashboards, polling)."""

    wait_time = between(0.1, 0.5)

    def on_start(self) -> None:
        self.headers = {
            "X-Tenant-ID": TENANT_ID,
            "Content-Type": "application/json",
        }

    @task(20)
    def poll_tasks(self) -> None:
        self.client.get(
            "/api/v1/tasks",
            headers=self.headers,
            name="/api/v1/tasks [GET]",
        )

    @task(10)
    def poll_metrics(self) -> None:
        self.client.get("/metrics", name="/metrics")

    @task(5)
    def poll_health(self) -> None:
        self.client.get("/health", name="/health")

    @task(3)
    def poll_results(self) -> None:
        self.client.get(
            "/api/v1/results",
            headers=self.headers,
            name="/api/v1/results [GET]",
        )
