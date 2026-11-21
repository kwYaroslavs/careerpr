"""API endpoints for Readiness Gate G4 and Application Snapshots (T-024)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.domain.schemas import ApplicationSnapshot, BaseResume
from app.domain.services.snapshots import SnapshotService

router = APIRouter(prefix="/applications", tags=["applications"])


class SnapshotCreateRequest(BaseModel):
    application_id: str
    base_resume: BaseResume
    run_id: str | None = None
    max_pages: int = 1
    template_version: str = "1.0"
    renderer_version: str = "1.0"


class G4CheckRequest(BaseModel):
    application_id: str
    base_resume: BaseResume
    run_id: str | None = None
    max_pages: int = 1


@router.post("/g4-check", response_model=dict[str, Any])
def check_readiness_g4(body: G4CheckRequest, db: Annotated[Session, Depends(get_db)]) -> Any:
    """Check Readiness Gate G4 requirements without creating a snapshot."""
    try:
        result = SnapshotService.check_readiness_g4(
            db,
            application_id=body.application_id,
            base_resume=body.base_resume,
            run_id=body.run_id,
            max_pages=body.max_pages,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/snapshots", response_model=ApplicationSnapshot, status_code=status.HTTP_201_CREATED)
def create_application_snapshot(
    body: SnapshotCreateRequest, db: Annotated[Session, Depends(get_db)]
) -> Any:
    """Enforce Gate G4 and create an immutable ApplicationSnapshot."""
    try:
        snap = SnapshotService.create_application_snapshot(
            db,
            application_id=body.application_id,
            base_resume=body.base_resume,
            run_id=body.run_id,
            max_pages=body.max_pages,
            template_version=body.template_version,
            renderer_version=body.renderer_version,
        )
        return ApplicationSnapshot(
            schema_version=snap.schema_version,
            id=snap.id,
            application_id=snap.application_id,
            frozen_approved_docs=snap.frozen_approved_docs,
            content_hash=snap.content_hash,
            pdf_hash=snap.pdf_hash,
            template_version=snap.template_version,
            renderer_version=snap.renderer_version,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
