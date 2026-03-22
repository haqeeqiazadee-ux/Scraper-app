"""Policy management API endpoints."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException

from packages.contracts.policy import Policy, PolicyCreate, PolicyUpdate

router = APIRouter()

# In-memory store for scaffolding (will be replaced by database)
_policies: dict[UUID, Policy] = {}


@router.post("/policies", status_code=201)
async def create_policy(policy_input: PolicyCreate) -> Policy:
    """Create a new extraction policy."""
    policy = Policy(
        id=uuid4(),
        tenant_id="default",  # TODO: Extract from auth middleware
        name=policy_input.name,
        target_domains=policy_input.target_domains,
        preferred_lane=policy_input.preferred_lane,
        extraction_rules=policy_input.extraction_rules,
        rate_limit=policy_input.rate_limit,
        proxy_policy=policy_input.proxy_policy,
        session_policy=policy_input.session_policy,
        retry_policy=policy_input.retry_policy,
        timeout_ms=policy_input.timeout_ms,
        robots_compliance=policy_input.robots_compliance,
    )
    _policies[policy.id] = policy
    return policy


@router.get("/policies/{policy_id}")
async def get_policy(policy_id: UUID) -> Policy:
    """Get a policy by ID."""
    policy = _policies.get(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.get("/policies")
async def list_policies(limit: int = 50, offset: int = 0) -> dict:
    """List all policies."""
    policies = list(_policies.values())
    total = len(policies)
    policies = policies[offset : offset + limit]
    return {"items": policies, "total": total, "limit": limit, "offset": offset}


@router.patch("/policies/{policy_id}")
async def update_policy(policy_id: UUID, policy_update: PolicyUpdate) -> Policy:
    """Update a policy."""
    policy = _policies.get(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    update_data = policy_update.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(policy, field_name, value)
    return policy


@router.delete("/policies/{policy_id}", status_code=204)
async def delete_policy(policy_id: UUID) -> None:
    """Delete a policy."""
    if policy_id not in _policies:
        raise HTTPException(status_code=404, detail="Policy not found")
    del _policies[policy_id]
