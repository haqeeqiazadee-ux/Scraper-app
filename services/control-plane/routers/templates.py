"""Template browsing and instantiation API endpoints."""

from __future__ import annotations

from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from packages.contracts.template import Template, TemplateCategory
from packages.core.template_registry import get_template, list_templates, search_templates
from packages.core.storage.repositories import PolicyRepository
from services.control_plane.dependencies import get_session, get_tenant_id

router = APIRouter()


def _template_summary(t: Template) -> dict:
    """Return a lightweight summary for list endpoints."""
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "category": t.category.value,
        "tags": t.tags,
        "icon": t.icon,
        "platform": t.platform,
        "version": t.version,
        "field_count": len(t.config.fields),
        "preferred_lane": t.config.preferred_lane,
        "browser_required": t.config.browser_required,
        "stealth_required": t.config.stealth_required,
    }


@router.get("/templates")
async def list_all_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    platform: Optional[str] = Query(None, description="Filter by platform name"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    q: Optional[str] = Query(None, description="Search query"),
) -> dict:
    """List available scraping templates with optional filters."""
    if q:
        templates = search_templates(q)
    else:
        templates = list_templates(category=category, platform=platform, tag=tag)

    return {
        "items": [_template_summary(t) for t in templates],
        "total": len(templates),
    }


@router.get("/templates/categories")
async def list_categories() -> dict:
    """List all template categories with counts."""
    all_templates = list_templates()
    counts: dict[str, int] = {}
    for t in all_templates:
        cat = t.category.value
        counts[cat] = counts.get(cat, 0) + 1
    return {
        "categories": [
            {"name": cat.value, "label": cat.value.replace("_", " ").title(), "count": counts.get(cat.value, 0)}
            for cat in TemplateCategory
        ],
    }


@router.get("/templates/{template_id}")
async def get_template_detail(template_id: str) -> dict:
    """Get full details of a specific template."""
    tmpl = get_template(template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    return {
        "id": tmpl.id,
        "name": tmpl.name,
        "description": tmpl.description,
        "category": tmpl.category.value,
        "tags": tmpl.tags,
        "icon": tmpl.icon,
        "platform": tmpl.platform,
        "version": tmpl.version,
        "config": {
            "target_domains": tmpl.config.target_domains,
            "example_urls": tmpl.config.example_urls,
            "fields": [
                {
                    "name": f.name,
                    "description": f.description,
                    "field_type": f.field_type,
                    "required": f.required,
                    "css_selector": f.css_selector,
                    "xpath_selector": f.xpath_selector,
                    "json_path": f.json_path,
                    "ai_hint": f.ai_hint,
                }
                for f in tmpl.config.fields
            ],
            "preferred_lane": tmpl.config.preferred_lane,
            "extraction_type": tmpl.config.extraction_type,
            "pagination": tmpl.config.pagination,
            "rate_limit_rpm": tmpl.config.rate_limit_rpm,
            "proxy_required": tmpl.config.proxy_required,
            "proxy_type": tmpl.config.proxy_type,
            "browser_required": tmpl.config.browser_required,
            "stealth_required": tmpl.config.stealth_required,
            "timeout_ms": tmpl.config.timeout_ms,
            "robots_compliance": tmpl.config.robots_compliance,
            "extraction_rules": tmpl.config.extraction_rules,
        },
    }


@router.post("/templates/{template_id}/apply", status_code=201)
async def apply_template(
    template_id: str,
    overrides: dict | None = None,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """
    Instantiate a template as a Policy.

    Creates a new Policy pre-configured with the template's extraction rules,
    rate limits, proxy settings, and lane preferences. Optional overrides
    allow customizing the generated policy.
    """
    tmpl = get_template(template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    overrides = overrides or {}

    # Build policy fields from template config
    cfg = tmpl.config
    policy_name = overrides.get("name", f"{tmpl.name} Policy")
    target_domains = overrides.get("target_domains", cfg.target_domains)
    preferred_lane = overrides.get("preferred_lane", cfg.preferred_lane)
    timeout_ms = overrides.get("timeout_ms", cfg.timeout_ms)

    # Build extraction rules including field definitions
    extraction_rules = {
        **cfg.extraction_rules,
        "template_id": tmpl.id,
        "template_version": tmpl.version,
        "extraction_type": cfg.extraction_type,
        "fields": [f.model_dump(exclude_none=True) for f in cfg.fields],
    }
    if cfg.pagination:
        extraction_rules["pagination"] = cfg.pagination

    rate_limit = {
        "max_requests_per_minute": cfg.rate_limit_rpm,
        "max_requests_per_hour": cfg.rate_limit_rpm * 60,
        "max_concurrent": max(1, cfg.rate_limit_rpm // 10),
    }

    proxy_policy = {
        "enabled": cfg.proxy_required,
        "geo": None,
        "proxy_type": cfg.proxy_type,
        "rotation_strategy": "weighted",
        "sticky_session": False,
    }

    session_policy = {
        "reuse_sessions": True,
        "max_session_age_minutes": 60,
        "max_requests_per_session": 100,
        "rotate_on_failure": True,
    }

    retry_policy = {
        "max_retries": 3,
        "backoff_base_seconds": 2.0,
        "backoff_max_seconds": 60.0,
        "retry_on_status_codes": [429, 500, 502, 503, 504],
    }

    repo = PolicyRepository(session)
    policy = await repo.create(
        tenant_id=tenant_id,
        id=str(uuid4()),
        name=policy_name,
        target_domains=target_domains,
        preferred_lane=preferred_lane,
        extraction_rules=extraction_rules,
        rate_limit=rate_limit,
        proxy_policy=proxy_policy,
        session_policy=session_policy,
        retry_policy=retry_policy,
        timeout_ms=timeout_ms,
        robots_compliance=cfg.robots_compliance,
    )

    return {
        "policy_id": policy.id,
        "policy_name": policy.name,
        "template_id": tmpl.id,
        "template_name": tmpl.name,
        "message": f"Policy created from template '{tmpl.name}'",
    }
