"""
Repository classes for database CRUD operations.

Each repository handles one entity type and enforces tenant isolation.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.actor_runtime.profiles import (
    ActorLearningEvent,
    ReplayValidationResult,
    StrategyPatchProposal,
    StrategyPatchStatus,
    StrategyProfile,
)
from packages.core.actor_runtime.fixtures import (
    FixtureReviewStatus,
    MaterializedRegressionFixture,
    RegressionFixtureCandidate,
    materialize_regression_fixture,
)
from packages.core.storage.models import (
    ActorLearningEventModel,
    ActorRegressionFixtureCandidateModel,
    ActorStrategyProfileModel,
    ArtifactModel,
    PolicyModel,
    ReplayValidationResultModel,
    ResultModel,
    RunModel,
    StrategyPatchProposalModel,
    TaskModel,
)

logger = logging.getLogger(__name__)


class TaskRepository:
    """CRUD operations for tasks with tenant isolation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, tenant_id: str, **kwargs) -> TaskModel:
        task = TaskModel(tenant_id=tenant_id, **kwargs)
        self._session.add(task)
        await self._session.flush()
        return task

    async def get(self, task_id: str, tenant_id: str) -> Optional[TaskModel]:
        stmt = select(TaskModel).where(
            TaskModel.id == task_id,
            TaskModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self, tenant_id: str, status: Optional[str] = None,
        limit: int = 50, offset: int = 0,
    ) -> tuple[list[TaskModel], int]:
        stmt = select(TaskModel).where(TaskModel.tenant_id == tenant_id)
        count_stmt = select(func.count()).select_from(TaskModel).where(TaskModel.tenant_id == tenant_id)

        if status:
            stmt = stmt.where(TaskModel.status == status)
            count_stmt = count_stmt.where(TaskModel.status == status)

        stmt = stmt.order_by(TaskModel.created_at.desc()).limit(limit).offset(offset)

        result = await self._session.execute(stmt)
        count_result = await self._session.execute(count_stmt)

        return list(result.scalars().all()), count_result.scalar_one()

    async def update(self, task_id: str, tenant_id: str, **kwargs) -> Optional[TaskModel]:
        task = await self.get(task_id, tenant_id)
        if not task:
            return None
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        await self._session.flush()
        return task

    async def delete(self, task_id: str, tenant_id: str) -> bool:
        stmt = delete(TaskModel).where(
            TaskModel.id == task_id,
            TaskModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0


class PolicyRepository:
    """CRUD operations for policies with tenant isolation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, tenant_id: str, **kwargs) -> PolicyModel:
        policy = PolicyModel(tenant_id=tenant_id, **kwargs)
        self._session.add(policy)
        await self._session.flush()
        return policy

    async def get(self, policy_id: str, tenant_id: str) -> Optional[PolicyModel]:
        stmt = select(PolicyModel).where(
            PolicyModel.id == policy_id,
            PolicyModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, tenant_id: str, limit: int = 50, offset: int = 0) -> tuple[list[PolicyModel], int]:
        stmt = (
            select(PolicyModel)
            .where(PolicyModel.tenant_id == tenant_id)
            .order_by(PolicyModel.created_at.desc())
            .limit(limit).offset(offset)
        )
        count_stmt = select(func.count()).select_from(PolicyModel).where(PolicyModel.tenant_id == tenant_id)

        result = await self._session.execute(stmt)
        count_result = await self._session.execute(count_stmt)

        return list(result.scalars().all()), count_result.scalar_one()

    async def update(self, policy_id: str, tenant_id: str, **kwargs) -> Optional[PolicyModel]:
        policy = await self.get(policy_id, tenant_id)
        if not policy:
            return None
        for key, value in kwargs.items():
            if hasattr(policy, key):
                setattr(policy, key, value)
        await self._session.flush()
        return policy

    async def delete(self, policy_id: str, tenant_id: str) -> bool:
        stmt = delete(PolicyModel).where(
            PolicyModel.id == policy_id,
            PolicyModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0


class RunRepository:
    """CRUD operations for runs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, tenant_id: str, **kwargs) -> RunModel:
        run = RunModel(tenant_id=tenant_id, **kwargs)
        self._session.add(run)
        await self._session.flush()
        return run

    async def get(self, run_id: str, tenant_id: str) -> Optional[RunModel]:
        stmt = select(RunModel).where(RunModel.id == run_id, RunModel.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, run_id: str, tenant_id: str, **kwargs) -> Optional[RunModel]:
        run = await self.get(run_id, tenant_id)
        if not run:
            return None
        for key, value in kwargs.items():
            if hasattr(run, key):
                setattr(run, key, value)
        await self._session.flush()
        return run

    async def list_by_task(self, task_id: str, tenant_id: str) -> list[RunModel]:
        stmt = (
            select(RunModel)
            .where(RunModel.task_id == task_id, RunModel.tenant_id == tenant_id)
            .order_by(RunModel.started_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class ResultRepository:
    """CRUD operations for results."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, tenant_id: str, **kwargs) -> ResultModel:
        result_obj = ResultModel(tenant_id=tenant_id, **kwargs)
        self._session.add(result_obj)
        await self._session.flush()
        return result_obj

    async def get(self, result_id: str, tenant_id: str) -> Optional[ResultModel]:
        stmt = select(ResultModel).where(ResultModel.id == result_id, ResultModel.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self, tenant_id: str, limit: int = 50, offset: int = 0,
        min_confidence: float | None = None, sort_by: str = "created_at", sort_order: str = "desc",
    ) -> tuple[list[ResultModel], int]:
        stmt = select(ResultModel).where(ResultModel.tenant_id == tenant_id)
        count_stmt = select(func.count()).select_from(ResultModel).where(ResultModel.tenant_id == tenant_id)

        if min_confidence is not None:
            stmt = stmt.where(ResultModel.confidence >= min_confidence)
            count_stmt = count_stmt.where(ResultModel.confidence >= min_confidence)

        col = getattr(ResultModel, sort_by, ResultModel.created_at)
        stmt = stmt.order_by(col.desc() if sort_order == "desc" else col.asc())
        stmt = stmt.offset(offset).limit(limit)

        result = await self._session.execute(stmt)
        count_result = await self._session.execute(count_stmt)
        return list(result.scalars().all()), count_result.scalar() or 0

    async def list_by_task(self, task_id: str, tenant_id: str) -> list[ResultModel]:
        stmt = (
            select(ResultModel)
            .where(ResultModel.task_id == task_id, ResultModel.tenant_id == tenant_id)
            .order_by(ResultModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class ArtifactRepository:
    """CRUD operations for artifacts with tenant isolation."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, tenant_id: str, **kwargs) -> ArtifactModel:
        artifact = ArtifactModel(tenant_id=tenant_id, **kwargs)
        self._session.add(artifact)
        await self._session.flush()
        return artifact

    async def get(self, artifact_id: str, tenant_id: str) -> Optional[ArtifactModel]:
        stmt = select(ArtifactModel).where(
            ArtifactModel.id == artifact_id,
            ArtifactModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_result(self, result_id: str, tenant_id: str) -> list[ArtifactModel]:
        stmt = (
            select(ArtifactModel)
            .where(ArtifactModel.result_id == result_id, ArtifactModel.tenant_id == tenant_id)
            .order_by(ArtifactModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_tenant(
        self, tenant_id: str, limit: int = 50, offset: int = 0,
    ) -> tuple[list[ArtifactModel], int]:
        stmt = (
            select(ArtifactModel)
            .where(ArtifactModel.tenant_id == tenant_id)
            .order_by(ArtifactModel.created_at.desc())
            .limit(limit).offset(offset)
        )
        count_stmt = select(func.count()).select_from(ArtifactModel).where(
            ArtifactModel.tenant_id == tenant_id,
        )

        result = await self._session.execute(stmt)
        count_result = await self._session.execute(count_stmt)

        return list(result.scalars().all()), count_result.scalar_one()

    async def delete(self, artifact_id: str, tenant_id: str) -> bool:
        stmt = delete(ArtifactModel).where(
            ArtifactModel.id == artifact_id,
            ArtifactModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0


class ActorStrategyProfileRepository:
    """Persistence for actor self-learning profiles and promotion artifacts."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_profile(self, actor_id: str, tenant_id: str) -> StrategyProfile | None:
        stmt = (
            select(ActorStrategyProfileModel)
            .where(
                ActorStrategyProfileModel.actor_id == actor_id,
                ActorStrategyProfileModel.tenant_id == tenant_id,
                ActorStrategyProfileModel.active.is_(True),
            )
            .order_by(ActorStrategyProfileModel.promoted_at.desc(), ActorStrategyProfileModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        row = result.scalars().first()
        return self._profile_from_row(row) if row is not None else None

    async def list_profiles(self, actor_id: str, tenant_id: str, limit: int = 25) -> list[StrategyProfile]:
        stmt = (
            select(ActorStrategyProfileModel)
            .where(
                ActorStrategyProfileModel.actor_id == actor_id,
                ActorStrategyProfileModel.tenant_id == tenant_id,
            )
            .order_by(ActorStrategyProfileModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._profile_from_row(row) for row in result.scalars().all()]

    async def save_profile(self, profile: StrategyProfile, tenant_id: str, *, active: bool = True) -> StrategyProfile:
        if active:
            existing = await self._session.execute(
                select(ActorStrategyProfileModel).where(
                    ActorStrategyProfileModel.actor_id == profile.actor_id,
                    ActorStrategyProfileModel.tenant_id == tenant_id,
                    ActorStrategyProfileModel.active.is_(True),
                )
            )
            for row in existing.scalars().all():
                row.active = False

        row = ActorStrategyProfileModel(
            tenant_id=tenant_id,
            actor_id=profile.actor_id,
            base_family=profile.base_family,
            version=profile.version,
            policy_version=profile.policy_version,
            promoted_by=profile.promoted_by,
            provider_order_json=list(profile.provider_order),
            schema_aliases_json={key: list(value) for key, value in profile.schema_aliases.items()},
            freshness_overrides_json=profile.freshness_overrides,
            replay_fixture_ids_json=list(profile.replay_fixture_ids),
            metrics_json=profile.metrics,
            active=active,
        )
        self._session.add(row)
        await self._session.flush()
        return self._profile_from_row(row)

    async def record_learning_event(self, event: ActorLearningEvent) -> str:
        row = ActorLearningEventModel(
            tenant_id=event.tenant_id,
            actor_id=event.actor_id,
            base_family=event.base_family,
            event_type=event.event_type.value,
            trigger_reason=event.trigger_reason,
            observed_at=event.observed_at.replace(tzinfo=None),
            profile_version=event.profile_version,
            payload_fingerprint=event.payload_fingerprint,
            redacted_payload_keys_json=list(event.redacted_payload_keys),
            metrics_json=event.metrics,
            evidence_json=list(event.evidence),
        )
        self._session.add(row)
        await self._session.flush()
        return row.id

    async def list_learning_events(
        self,
        actor_id: str,
        tenant_id: str,
        limit: int = 50,
    ) -> list[ActorLearningEventModel]:
        stmt = (
            select(ActorLearningEventModel)
            .where(
                ActorLearningEventModel.actor_id == actor_id,
                ActorLearningEventModel.tenant_id == tenant_id,
            )
            .order_by(ActorLearningEventModel.observed_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_proposal(self, proposal: StrategyPatchProposal, tenant_id: str) -> StrategyPatchProposal:
        row = StrategyPatchProposalModel(
            proposal_id=proposal.proposal_id,
            tenant_id=tenant_id,
            actor_id=proposal.actor_id,
            base_family=proposal.base_family,
            current_profile_version=proposal.current_profile_version,
            proposed_profile_version=proposal.proposed_profile_version,
            patch_json=proposal.patch,
            rationale=proposal.rationale,
            required_replay_fixture_ids_json=list(proposal.required_replay_fixture_ids),
            status=proposal.status.value,
            created_at=proposal.created_at.replace(tzinfo=None),
        )
        self._session.add(row)
        await self._session.flush()
        return self._proposal_from_row(row)

    async def get_proposal(self, proposal_id: str, actor_id: str, tenant_id: str) -> StrategyPatchProposal | None:
        stmt = select(StrategyPatchProposalModel).where(
            StrategyPatchProposalModel.proposal_id == proposal_id,
            StrategyPatchProposalModel.actor_id == actor_id,
            StrategyPatchProposalModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._proposal_from_row(row) if row is not None else None

    async def list_proposals(
        self,
        actor_id: str,
        tenant_id: str,
        limit: int = 50,
    ) -> list[StrategyPatchProposal]:
        stmt = (
            select(StrategyPatchProposalModel)
            .where(
                StrategyPatchProposalModel.actor_id == actor_id,
                StrategyPatchProposalModel.tenant_id == tenant_id,
            )
            .order_by(StrategyPatchProposalModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._proposal_from_row(row) for row in result.scalars().all()]

    async def set_proposal_status(
        self,
        proposal_id: str,
        actor_id: str,
        tenant_id: str,
        status: StrategyPatchStatus,
    ) -> None:
        row = await self._session.get(StrategyPatchProposalModel, proposal_id)
        if row is None or row.actor_id != actor_id or row.tenant_id != tenant_id:
            return
        row.status = status.value
        await self._session.flush()

    async def record_replay_validation(
        self,
        actor_id: str,
        tenant_id: str,
        validation: ReplayValidationResult,
    ) -> ReplayValidationResult:
        row = ReplayValidationResultModel(
            tenant_id=tenant_id,
            actor_id=actor_id,
            proposal_id=validation.proposal_id,
            passed=validation.passed,
            fixtures_run_json=list(validation.fixtures_run),
            score_before=validation.score_before,
            score_after=validation.score_after,
            security_blockers_json=list(validation.security_blockers),
            errors_json=list(validation.errors),
            validated_at=validation.validated_at.replace(tzinfo=None),
        )
        self._session.add(row)
        await self._session.flush()
        return self._validation_from_row(row)

    async def latest_replay_validation(
        self,
        proposal_id: str,
        actor_id: str,
        tenant_id: str,
    ) -> ReplayValidationResult | None:
        stmt = (
            select(ReplayValidationResultModel)
            .where(
                ReplayValidationResultModel.proposal_id == proposal_id,
                ReplayValidationResultModel.actor_id == actor_id,
                ReplayValidationResultModel.tenant_id == tenant_id,
            )
            .order_by(ReplayValidationResultModel.validated_at.desc())
        )
        result = await self._session.execute(stmt)
        row = result.scalars().first()
        return self._validation_from_row(row) if row is not None else None

    def _profile_from_row(self, row: ActorStrategyProfileModel) -> StrategyProfile:
        return StrategyProfile(
            actor_id=row.actor_id,
            base_family=row.base_family,
            version=row.version,
            policy_version=row.policy_version,
            promoted_by=row.promoted_by,
            provider_order=tuple(row.provider_order_json or []),
            schema_aliases={key: tuple(value) for key, value in (row.schema_aliases_json or {}).items()},
            freshness_overrides=row.freshness_overrides_json or {},
            replay_fixture_ids=tuple(row.replay_fixture_ids_json or []),
            metrics=row.metrics_json or {},
        )

    def _proposal_from_row(self, row: StrategyPatchProposalModel) -> StrategyPatchProposal:
        return StrategyPatchProposal(
            proposal_id=row.proposal_id,
            actor_id=row.actor_id,
            base_family=row.base_family,
            current_profile_version=row.current_profile_version,
            proposed_profile_version=row.proposed_profile_version,
            patch=row.patch_json or {},
            rationale=row.rationale,
            required_replay_fixture_ids=tuple(row.required_replay_fixture_ids_json or []),
            status=StrategyPatchStatus(row.status),
            created_at=row.created_at,
        )

    def _validation_from_row(self, row: ReplayValidationResultModel) -> ReplayValidationResult:
        return ReplayValidationResult(
            proposal_id=row.proposal_id,
            passed=row.passed,
            fixtures_run=tuple(row.fixtures_run_json or []),
            score_before=row.score_before,
            score_after=row.score_after,
            security_blockers=tuple(row.security_blockers_json or []),
            errors=tuple(row.errors_json or []),
            validated_at=row.validated_at,
        )


class ActorFixtureRepository:
    """Persistence for reviewed trace-to-fixture candidates."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_candidate(self, candidate: RegressionFixtureCandidate) -> RegressionFixtureCandidate:
        row = ActorRegressionFixtureCandidateModel(
            fixture_id=candidate.fixture_id,
            tenant_id=candidate.tenant_id,
            actor_id=candidate.actor_id,
            base_family=candidate.base_family,
            status=FixtureReviewStatus.PENDING_REVIEW.value,
            source_trace_id=candidate.source_trace_id,
            state=candidate.state,
            provider=candidate.provider,
            trigger_reasons_json=list(candidate.trigger_reasons),
            sanitized_input_json=candidate.sanitized_input,
            redacted_payload_keys_json=list(candidate.redacted_payload_keys),
            expected_assertions_json=list(candidate.expected_assertions),
            tags_json=list(candidate.tags),
            created_at=candidate.created_at.replace(tzinfo=None),
        )
        self._session.add(row)
        await self._session.flush()
        return self._candidate_from_row(row)

    async def get_candidate(
        self,
        fixture_id: str,
        actor_id: str,
        tenant_id: str,
    ) -> ActorRegressionFixtureCandidateModel | None:
        stmt = select(ActorRegressionFixtureCandidateModel).where(
            ActorRegressionFixtureCandidateModel.fixture_id == fixture_id,
            ActorRegressionFixtureCandidateModel.actor_id == actor_id,
            ActorRegressionFixtureCandidateModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_candidates(
        self,
        actor_id: str,
        tenant_id: str,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[ActorRegressionFixtureCandidateModel]:
        stmt = select(ActorRegressionFixtureCandidateModel).where(
            ActorRegressionFixtureCandidateModel.actor_id == actor_id,
            ActorRegressionFixtureCandidateModel.tenant_id == tenant_id,
        )
        if status:
            stmt = stmt.where(ActorRegressionFixtureCandidateModel.status == status)
        stmt = stmt.order_by(ActorRegressionFixtureCandidateModel.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def review_candidate(
        self,
        fixture_id: str,
        actor_id: str,
        tenant_id: str,
        *,
        status: FixtureReviewStatus,
        reviewed_by: str,
        notes: str = "",
    ) -> ActorRegressionFixtureCandidateModel | None:
        row = await self.get_candidate(fixture_id, actor_id, tenant_id)
        if row is None:
            return None
        row.status = status.value
        row.reviewed_by = reviewed_by
        row.review_notes = notes
        row.reviewed_at = datetime.utcnow()
        await self._session.flush()
        return row

    async def materialize_candidate(
        self,
        fixture_id: str,
        actor_id: str,
        tenant_id: str,
        *,
        reviewed_by: str,
    ) -> MaterializedRegressionFixture | None:
        row = await self.get_candidate(fixture_id, actor_id, tenant_id)
        if row is None:
            return None
        if row.status not in {FixtureReviewStatus.APPROVED.value, FixtureReviewStatus.MATERIALIZED.value}:
            raise ValueError("Fixture candidate must be approved before materialization")
        candidate = self._candidate_from_row(row)
        materialized = materialize_regression_fixture(candidate, reviewed_by=reviewed_by)
        row.status = FixtureReviewStatus.MATERIALIZED.value
        row.materialized_fixture_json = materialized.model_dump(mode="json")
        row.materialized_at = materialized.materialized_at.replace(tzinfo=None)
        await self._session.flush()
        return materialized

    def serialize_row(self, row: ActorRegressionFixtureCandidateModel) -> dict:
        return {
            "fixture_id": row.fixture_id,
            "tenant_id": row.tenant_id,
            "actor_id": row.actor_id,
            "base_family": row.base_family,
            "status": row.status,
            "source_trace_id": row.source_trace_id,
            "state": row.state,
            "provider": row.provider,
            "trigger_reasons": row.trigger_reasons_json or [],
            "sanitized_input": row.sanitized_input_json or {},
            "redacted_payload_keys": row.redacted_payload_keys_json or [],
            "expected_assertions": row.expected_assertions_json or [],
            "tags": row.tags_json or [],
            "review_notes": row.review_notes,
            "reviewed_by": row.reviewed_by,
            "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
            "materialized_fixture": row.materialized_fixture_json,
            "materialized_at": row.materialized_at.isoformat() if row.materialized_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    def _candidate_from_row(self, row: ActorRegressionFixtureCandidateModel) -> RegressionFixtureCandidate:
        return RegressionFixtureCandidate(
            fixture_id=row.fixture_id,
            actor_id=row.actor_id,
            base_family=row.base_family,
            tenant_id=row.tenant_id,
            trigger_reasons=tuple(row.trigger_reasons_json or []),
            source_trace_id=row.source_trace_id,
            state=row.state,
            provider=row.provider,
            sanitized_input=row.sanitized_input_json or {},
            redacted_payload_keys=tuple(row.redacted_payload_keys_json or []),
            expected_assertions=tuple(row.expected_assertions_json or []),
            tags=tuple(row.tags_json or []),
            created_at=row.created_at,
        )
