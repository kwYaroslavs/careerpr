"""Domain services for managing job postings, URL normalization, and duplicate detection."""

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy.orm import Session

from app.domain.models import JobPostingModel
from app.domain.schemas import JobPosting


class JobService:
    """Service for job posting intake, URL normalization, and duplicate detection."""

    @staticmethod
    def normalize_url(url: str | None) -> str | None:
        """Normalize a URL for deduplication.

        Removes fragments and common tracking query params, lowercases scheme/host,
        strips a leading "www." and trailing slash.
        """
        if not url or not url.strip():
            return None

        parsed = urlparse(url.strip())
        if not parsed.scheme or not parsed.netloc:
            return url.strip().lower()

        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]

        path = parsed.path
        if path.endswith("/") and len(path) > 1:
            path = path.rstrip("/")

        ignored_params = {
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "ref",
            "source",
            "fbclid",
            "gclid",
        }
        query_params = parse_qsl(parsed.query, keep_blank_values=True)
        filtered_params = [(k, v) for k, v in query_params if k.lower() not in ignored_params]
        query = urlencode(filtered_params) if filtered_params else ""

        return urlunparse((scheme, netloc, path, parsed.params, query, ""))

    @staticmethod
    def create_job_posting(session: Session, job_in: JobPosting) -> JobPostingModel:
        """Create a job posting, performing URL normalization and duplicate URL detection."""
        normalized_url = JobService.normalize_url(job_in.url_normalized or job_in.source)

        if normalized_url and (
            "http://" in normalized_url or "https://" in normalized_url or "." in normalized_url
        ):
            existing = (
                session.query(JobPostingModel)
                .filter(JobPostingModel.url_normalized == normalized_url)
                .first()
            )
            if existing:
                raise ValueError(f"Duplicate job posting URL detected: {normalized_url}")

        db_job = JobPostingModel(
            id=job_in.id,
            schema_version=job_in.schema_version,
            url_normalized=normalized_url,
            raw_job_description=job_in.raw_job_description,
            extraction_metadata=job_in.extraction_metadata.model_dump(),
            source=job_in.source,
        )
        session.add(db_job)
        session.commit()
        session.refresh(db_job)
        return db_job

    @staticmethod
    def get_job_posting(session: Session, job_id: str) -> JobPostingModel | None:
        """Retrieve a job posting by ID."""
        return session.get(JobPostingModel, job_id)
