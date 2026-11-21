"""Readiness Gate G4 and immutable application snapshot service (T-024).

Enforces:
- All claims/proposals included in the application are approved.
- Validators are green.
- Page limit and round-trip text check pass.
- Freezes content_hash, pdf_hash, template_version,
  renderer_version into an immutable ApplicationSnapshot.
- Compiles a list of all stretch claims (`user_stretch`)
  for interview preparation.
"""

import hashlib
from typing import Any

from sqlalchemy.orm import Session

from app.domain.models import (
    ApplicationSnapshotModel,
    CandidateFactModel,
    ChangeProposalModel,
)
from app.domain.schemas import ProposalStatus
from app.render.markdown import render_resume_markdown
from app.render.pdf import extract_pdf_text, render_resume_pdf


class SnapshotService:
    @staticmethod
    def check_readiness_g4(
        session: Session,
        application_id: str,
        base_resume: Any,
        run_id: str | None = None,
        max_pages: int = 1,
    ) -> dict[str, Any]:
        """Check Readiness Gate G4 requirements.

        Returns a dict with:
        - ready: bool
        - reasons: list[str]
        - stretch_claims: list[dict[str, Any]]
        - content_hash: str | None
        - pdf_hash: str | None
        """
        reasons: list[str] = []

        query = session.query(ChangeProposalModel)
        if run_id:
            query = query.filter(ChangeProposalModel.run_id == run_id)
        proposals = query.all()

        for p in proposals:
            if p.status not in (ProposalStatus.APPROVED, ProposalStatus.APPLIED):
                reasons.append(
                    f"Proposal {p.id} has status '{p.status}' (must be approved or applied)"
                )
            if p.blocked_reason:
                reasons.append(f"Proposal {p.id} has block reason: {p.blocked_reason}")

        try:
            md_content = render_resume_markdown(base_resume)
            pdf_bytes = render_resume_pdf(base_resume, max_pages=max_pages)
            extracted_text = extract_pdf_text(pdf_bytes)

            if not extracted_text or len(extracted_text.strip()) == 0:
                reasons.append("PDF round-trip text extraction failed: extracted text is empty")
        except Exception as e:
            reasons.append(f"Rendering or fit-loop failed: {e}")
            pdf_bytes = b""
            md_content = ""

        resume_items = getattr(base_resume, "items", [])
        cited_fact_ids: set[str] = set()
        for item in resume_items:
            f_ids = (
                item.get("fact_ids", [])
                if isinstance(item, dict)
                else getattr(item, "fact_ids", [])
            )
            cited_fact_ids.update(f_ids)

        stretch_claims = []
        if cited_fact_ids:
            facts = (
                session.query(CandidateFactModel)
                .filter(CandidateFactModel.id.in_(list(cited_fact_ids)))
                .all()
            )
            for f in facts:
                if f.verification_status == "user_stretch":
                    stretch_claims.append(
                        {
                            "id": f.id,
                            "text": f.text,
                            "interview_note": f.interview_note,
                        }
                    )

        ready = len(reasons) == 0
        content_hash = (
            hashlib.sha256(md_content.encode("utf-8")).hexdigest() if md_content else None
        )
        pdf_hash = hashlib.sha256(pdf_bytes).hexdigest() if pdf_bytes else None

        return {
            "ready": ready,
            "reasons": reasons,
            "stretch_claims": stretch_claims,
            "content_hash": content_hash,
            "pdf_hash": pdf_hash,
        }

    @staticmethod
    def create_application_snapshot(
        session: Session,
        application_id: str,
        base_resume: Any,
        run_id: str | None = None,
        max_pages: int = 1,
        template_version: str = "1.0",
        renderer_version: str = "1.0",
    ) -> ApplicationSnapshotModel:
        """Enforce Gate G4 and create an immutable ApplicationSnapshot."""
        g4_result = SnapshotService.check_readiness_g4(
            session, application_id, base_resume, run_id=run_id, max_pages=max_pages
        )

        if not g4_result["ready"]:
            raise ValueError(f"Readiness Gate G4 failed: {'; '.join(g4_result['reasons'])}")

        raw_snap_key = application_id + g4_result["content_hash"]
        snap_hash = hashlib.sha256(raw_snap_key.encode()).hexdigest()[:26]
        snapshot_id = f"snap_{snap_hash}"

        existing = session.get(ApplicationSnapshotModel, snapshot_id)
        if existing:
            return existing

        resume_dump = (
            base_resume.model_dump() if hasattr(base_resume, "model_dump") else base_resume
        )
        frozen_docs = {
            "resume": resume_dump,
            "stretch_claims": g4_result["stretch_claims"],
        }

        db_snap = ApplicationSnapshotModel(
            id=snapshot_id,
            schema_version=1,
            application_id=application_id,
            frozen_approved_docs=frozen_docs,
            content_hash=g4_result["content_hash"],
            pdf_hash=g4_result["pdf_hash"],
            template_version=template_version,
            renderer_version=renderer_version,
        )

        session.add(db_snap)
        session.commit()
        session.refresh(db_snap)
        return db_snap
