"""
Shared data contracts for the AI Scraping Platform.

All components communicate through these Pydantic models.
This is the single source of truth for data schemas.
"""

from packages.contracts.task import Task, TaskCreate, TaskUpdate, TaskStatus
from packages.contracts.policy import (
    Policy,
    PolicyCreate,
    PolicyUpdate,
    RateLimit,
    ProxyPolicy,
    SessionPolicy,
    RetryPolicy,
)
from packages.contracts.session import Session, SessionCreate, SessionStatus, SessionType
from packages.contracts.run import Run, RunCreate, RunStatus
from packages.contracts.result import Result, ResultCreate
from packages.contracts.artifact import Artifact, ArtifactCreate, ArtifactType
from packages.contracts.billing import TenantQuota, UsageCounters, PlanTier
from packages.contracts.template import Template, TemplateCategory, TemplateConfig, FieldDefinition

__all__ = [
    # Task
    "Task", "TaskCreate", "TaskUpdate", "TaskStatus",
    # Policy
    "Policy", "PolicyCreate", "PolicyUpdate",
    "RateLimit", "ProxyPolicy", "SessionPolicy", "RetryPolicy",
    # Session
    "Session", "SessionCreate", "SessionStatus", "SessionType",
    # Run
    "Run", "RunCreate", "RunStatus",
    # Result
    "Result", "ResultCreate",
    # Artifact
    "Artifact", "ArtifactCreate", "ArtifactType",
    # Billing
    "TenantQuota", "UsageCounters", "PlanTier",
    # Template
    "Template", "TemplateCategory", "TemplateConfig", "FieldDefinition",
]
