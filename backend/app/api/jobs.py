"""API endpoints for job postings and job description intake (T-008)."""

from typing import Annotated, Any

import sqlalchemy.exc
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.domain.schemas import ExtractionMetadata, JobPosting
from app.domain.services.jobs import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobCreateRequest(BaseModel):
    id: str
    url_normalized: str | None = None
    raw_job_description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    extraction_metadata: ExtractionMetadata = Field(default_factory=ExtractionMetadata)
    source: str = "raw"


@router.post("", response_model=JobPosting, status_code=status.HTTP_201_CREATED)
def create_job(body: JobCreateRequest, db: Annotated[Session, Depends(get_db)]) -> Any:
    """Store raw JD and handle URL normalization and duplicate detection."""
    try:
        job_obj = JobPosting(
            id=body.id,
            url_normalized=body.url_normalized,
            raw_job_description=body.raw_job_description,
            extraction_metadata=body.extraction_metadata,
            source=body.source,
        )
        created = JobService.create_job_posting(db, job_obj)
        return JobPosting(
            schema_version=created.schema_version,
            id=created.id,
            url_normalized=created.url_normalized,
            raw_job_description=created.raw_job_description,
            extraction_metadata=ExtractionMetadata(**created.extraction_metadata),
            source=created.source,
        )
    except (ValueError, sqlalchemy.exc.IntegrityError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/{job_id}", response_model=JobPosting)
def get_job(job_id: str, db: Annotated[Session, Depends(get_db)]) -> Any:
    """Retrieve a specific job posting by ID."""
    job = JobService.get_job_posting(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job posting not found")
    return JobPosting(
        schema_version=job.schema_version,
        id=job.id,
        url_normalized=job.url_normalized,
        raw_job_description=job.raw_job_description,
        extraction_metadata=ExtractionMetadata(**job.extraction_metadata),
        source=job.source,
    )
