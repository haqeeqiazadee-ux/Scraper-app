"""Policy management API endpoints — database-backed."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from packages.contracts.policy import Policy, PolicyCreate, PolicyUpdate
from packages.core.storage.repositories import PolicyRepository
from services.control_plane.dependencies import get_session, get_tenant_id

router = APIRouter()


@router.post("/policies", status_code=201)
async def create_policy(
    policy_input: PolicyCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Create a new extraction policy."""
    repo = PolicyRepository(session)
    policy = await repo.create(
        tenant_id=tenant_id,
        id=str(uuid4()),
        name=policy_input.name,
        target_domains=policy_input.target_domains,
        preferred_lane=policy_input.preferred_lane.value,
        extraction_rules=policy_input.extraction_rules,
        rate_limit=policy_input.rate_limit.model_dump(),
        proxy_policy=policy_input.proxy_policy.model_dump(),
        session_policy=policy_input.session_policy.model_dump(),
        retry_policy=policy_input.retry_policy.model_dump(),
        timeout_ms=policy_input.timeout_ms,
        robots_compliance=policy_input.robots_compliance,
    )
    return {
        "id": policy.id,
        "tenant_id": policy.tenant_id,
        "name": policy.name,
        "preferred_lane": policy.preferred_lane,
        "timeout_ms": policy.timeout_ms,
        "created_at": policy.created_at.isoformat() if policy.created_at else None,
    }


@router.get("/policies/{policy_id}")
async def get_policy(
    policy_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Get a policy by ID."""
    repo = PolicyRepository(session)
    policy = await repo.get(policy_id, tenant_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {
        "id": policy.id,
        "tenant_id": policy.tenant_id,
        "name": policy.name,
        "target_domains": policy.target_domains,
        "preferred_lane": policy.preferred_lane,
        "extraction_rules": policy.extraction_rules,
        "rate_limit": policy.rate_limit,
        "proxy_policy": policy.proxy_policy,
        "session_policy": policy.session_policy,
        "retry_policy": policy.retry_policy,
        "timeout_ms": policy.timeout_ms,
        "robots_compliance": policy.robots_compliance,
        "created_at": policy.created_at.isoformat() if policy.created_at else None,
    }


@router.get("/policies")
async def list_policies(
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """List all policies."""
    repo = PolicyRepository(session)
    policies, total = await repo.list(tenant_id, limit=limit, offset=offset)
    return {
        "items": [
            {
                "id": p.id,
                "name": p.name,
                "preferred_lane": p.preferred_lane,
                "target_domains": p.target_domains,
                "timeout_ms": p.timeout_ms,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in policies
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.patch("/policies/{policy_id}")
async def update_policy(
    policy_id: str,
    policy_update: PolicyUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Update a policy."""
    repo = PolicyRepository(session)
    update_data = policy_update.model_dump(exclude_unset=True)

    # Serialize nested Pydantic models to dicts for JSON columns
    for field in ("rate_limit", "proxy_policy", "session_policy", "retry_policy"):
        if field in update_data and update_data[field] is not None:
            update_data[field] = update_data[field].model_dump() if hasattr(update_data[field], "model_dump") else update_data[field]
    if "preferred_lane" in update_data and update_data["preferred_lane"]:
        update_data["preferred_lane"] = update_data["preferred_lane"].value

    policy = await repo.update(policy_id, tenant_id, **update_data)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {
        "id": policy.id,
        "name": policy.name,
        "preferred_lane": policy.preferred_lane,
        "timeout_ms": policy.timeout_ms,
    }


@router.delete("/policies/{policy_id}", status_code=204)
async def delete_policy(
    policy_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> None:
    """Delete a policy."""
    repo = PolicyRepository(session)
    deleted = await repo.delete(policy_id, tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Policy not found")
