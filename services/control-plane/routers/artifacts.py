"""Artifact storage and download API endpoints."""

from __future__ import annotations

import hashlib
import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.storage.repositories import ArtifactRepository
from packages.core.storage.filesystem_store import FilesystemObjectStore
from services.control_plane.dependencies import get_session, get_tenant_id

logger = logging.getLogger(__name__)

router = APIRouter()

# Module-level object store instance (lazy init)
_object_store: FilesystemObjectStore | None = None


def _get_object_store() -> FilesystemObjectStore:
    """Get or create the filesystem object store."""
    global _object_store
    if _object_store is None:
        _object_store = FilesystemObjectStore()
    return _object_store


@router.post("/artifacts", status_code=201)
async def create_artifact(
    file: UploadFile = File(...),
    result_id: str = Form(...),
    artifact_type: str = Form(...),
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Upload and store a new artifact."""
    # Read file content
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file upload")

    # Calculate checksum
    checksum = f"sha256:{hashlib.sha256(content).hexdigest()}"

    # Generate artifact ID and storage path
    artifact_id = str(uuid4())
    filename = file.filename or artifact_id
    storage_path = f"artifacts/{tenant_id}/{result_id}/{artifact_id}/{filename}"
    content_type = file.content_type or "application/octet-stream"

    # Store content in object store
    store = _get_object_store()
    await store.put(storage_path, content, content_type=content_type)

    # Create database record
    repo = ArtifactRepository(session)
    artifact = await repo.create(
        tenant_id=tenant_id,
        id=artifact_id,
        result_id=result_id,
        artifact_type=artifact_type,
        storage_path=storage_path,
        content_type=content_type,
        size_bytes=len(content),
        checksum=checksum,
    )
    await session.flush()

    return {
        "id": artifact.id,
        "result_id": artifact.result_id,
        "tenant_id": artifact.tenant_id,
        "artifact_type": artifact.artifact_type,
        "storage_path": artifact.storage_path,
        "content_type": artifact.content_type,
        "size_bytes": artifact.size_bytes,
        "checksum": artifact.checksum,
        "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
        "expires_at": artifact.expires_at.isoformat() if artifact.expires_at else None,
    }


@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Get artifact metadata by ID."""
    repo = ArtifactRepository(session)
    artifact = await repo.get(artifact_id, tenant_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {
        "id": artifact.id,
        "result_id": artifact.result_id,
        "tenant_id": artifact.tenant_id,
        "artifact_type": artifact.artifact_type,
        "storage_path": artifact.storage_path,
        "content_type": artifact.content_type,
        "size_bytes": artifact.size_bytes,
        "checksum": artifact.checksum,
        "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
        "expires_at": artifact.expires_at.isoformat() if artifact.expires_at else None,
    }


@router.get("/artifacts/{artifact_id}/download")
async def download_artifact(
    artifact_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> Response:
    """Download artifact content from object store."""
    repo = ArtifactRepository(session)
    artifact = await repo.get(artifact_id, tenant_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    store = _get_object_store()
    try:
        data = await store.get(artifact.storage_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Artifact content not found in storage")

    # Extract filename from storage path
    filename = artifact.storage_path.rsplit("/", 1)[-1] if "/" in artifact.storage_path else artifact_id

    return Response(
        content=data,
        media_type=artifact.content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/results/{result_id}/artifacts")
async def list_result_artifacts(
    result_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """List all artifacts for a given result."""
    repo = ArtifactRepository(session)
    artifacts = await repo.list_by_result(result_id, tenant_id)
    return {
        "items": [
            {
                "id": a.id,
                "result_id": a.result_id,
                "artifact_type": a.artifact_type,
                "content_type": a.content_type,
                "size_bytes": a.size_bytes,
                "checksum": a.checksum,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in artifacts
        ],
        "total": len(artifacts),
    }


@router.delete("/artifacts/{artifact_id}", status_code=200)
async def delete_artifact(
    artifact_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Delete an artifact and its stored content."""
    repo = ArtifactRepository(session)

    # Fetch artifact first to get storage path
    artifact = await repo.get(artifact_id, tenant_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Delete from object store
    store = _get_object_store()
    try:
        await store.delete(artifact.storage_path)
    except Exception:
        logger.warning("Failed to delete artifact content from storage", extra={
            "artifact_id": artifact_id,
            "storage_path": artifact.storage_path,
        })

    # Delete database record
    deleted = await repo.delete(artifact_id, tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return {"deleted": True, "id": artifact_id}
