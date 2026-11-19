# Product architecture review: scalable CV generation and template system

Date: 2026-11-19
Scope: review of the supplied `careerpr_final.zip`. This document is a proposal; it does not claim that the proposed features are implemented.

## Executive assessment

CareerPR has a sound trust model: a verified Fact Base, evidence-linked tailoring proposals, deterministic validation, human approval and immutable application snapshots. This is a strong foundation.

However, the repository is currently a scaffold, not a working CV generator:
- `backend/app/main.py` exposes only `GET /health`.
- `backend/app/domain/schemas.py` contains only a small subset of the entities described in `DATA_MODEL.md`.
- `backend/app/gateway/` has a protocol and FakeLLM, but no real provider.
- `frontend/` contains only `.gitkeep`.
- `backend/app/render/`, persistence models/migrations, API routers, import pipeline and prompt files are not implemented in the supplied archive.
- All 30 task cards are `todo`.
- Template management and batch generation are not defined as implemented features.

The current design is best described as a vacancy-tailoring workflow prototype specification. It needs a product-level expansion to become a scalable CV production platform.

## Current input and output contracts

### Inputs described by the specification

1. Candidate profile: identity/contact data, location, language preferences and hard constraints.
2. Candidate facts: employment, roles, dates, skills, achievements, education, certifications, metrics and evidence/source references.
3. Master/Base resume: structured sections and items linked to stable Fact IDs.
4. Job posting: pasted job-description text (primary path); URL ingestion is best-effort.
5. User decisions: requirement confirmation, clarification answers, proposal approvals/rejections and optional user-approved stretch wording.
6. Generation preferences: currently under-specified; should include target role, locale, seniority, page limit, tone and selected template.

### Inputs actually accepted by running code today

There is no candidate/JD API or import endpoint in the supplied code. The only HTTP endpoint is `/health`. The Pydantic classes `Fact`, `Resume`, `ResumeItem`, `JobRequirement` and `ChangeProposal` are data contracts only; they are not connected to a persistence or generation pipeline.

### Outputs described by the specification

- Requirement extraction and confirmation records.
- Requirement-to-fact evidence map and Strong/Possible/Stretch/Blocked bucket.
- Tailoring proposals and validation results.
- User-approved resume overlay/version.
- Cover letter.
- Markdown and PDF rendering.
- Immutable application snapshot with hashes and template/renderer version metadata.

### Outputs actually produced by running code today

Only `{"status": "ok"}` from `/health`. No resume, PDF, DOCX, HTML, JSON export or batch result is currently generated.

## Recommended target architecture

Keep the existing evidence-first core, but separate five concerns:

1. **Candidate Intelligence** — imports, parsing, normalized candidate profile, Fact Base, evidence and provenance.
2. **Content/Resume Engine** — role-specific content variants, summary, experience selection/order, skills, locale and vacancy tailoring. It never owns visual layout.
3. **Template Engine** — versioned design definitions and renderers. It never invents or rewrites candidate facts.
4. **Batch Orchestrator** — queues, parallelism limits, retries, idempotency, progress, cancellation and per-item failures.
5. **Quality & Export** — ATS/text extraction checks, layout checks, factual traceability, PDF/DOCX/HTML/JSON exports and immutable snapshots.

Recommended flow:

`Upload/manual input → parse → candidate reviews extracted data → Fact Base → Master Resume → generation brief (role + locale + JD + constraints) → content variant → evidence/claim validation → approved content snapshot → template render → PDF/DOCX/HTML/JSON → QA report`

For batch work, the same flow runs as a job over a set of candidates, target roles, vacancies or template variants. Each generated artifact remains individually traceable and reviewable.

## Data model additions recommended

Add explicit, versioned entities rather than storing all content in free-form text:

- `ResumeSection`: stable id, section type, localized title, order and visibility.
- `ExperienceEntry`: employer, title, dates, location, description and linked Fact IDs.
- `EducationEntry`, `CertificationEntry`, `ProjectEntry`, `SkillEntry`, `LanguageEntry`.
- `GenerationBrief`: candidate/profile version, target role, seniority, locale, target market, page limit, JD id, content strategy and constraints.
- `ResumeContentVariant`: structured sections/items, selected Fact IDs, locale, role focus, version and content hash.
- `Template`: stable id, name, category, supported locales, layout capabilities, ATS profile and status.
- `TemplateVersion`: immutable version, manifest/schema version, assets/font references, renderer compatibility and preview metadata.
- `RenderJob`: content variant id, template version id, requested formats, status, attempts, error and output artifact references.
- `GeneratedArtifact`: format, storage key, checksum, page count, extracted-text QA result and snapshot id.
- `BatchJob` and `BatchJobItem`: batch configuration, progress, idempotency key, item status, retry/error and artifact references.
- `QualityReport`: factual traceability, missing required sections, ATS text extraction, page/layout checks, language consistency and warnings.

Keep `ApplicationSnapshot` for a specific job application. A general CV created without a vacancy should have a separate `ResumeSnapshot` or generic `DocumentSnapshot`; do not force every CV into an application record.

## Template system: required design

Templates should be data-driven and versioned. A template manifest should describe:
- page size, margins, columns and spacing;
- typography, font assets and language/script coverage;
- section ordering and optional/required sections;
- component styles for header, experience, education, skills, projects and links;
- colors, separators, icons and density;
- ATS profile (`ats_safe` or `visual`);
- supported locales and fallback fonts;
- renderer version and template version.

Template data must not contain candidate facts. The renderer receives a validated `ResumeContentVariant` plus a pinned `TemplateVersion` and returns artifacts.

Provide two explicit output tracks:
- **ATS track:** single column, selectable text, conventional headings, predictable reading order, restrained styling, no information encoded only in icons/images.
- **Visual track:** more expressive layouts for human readers, while still preserving selectable text and a text/JSON alternative.

A template change must not trigger content regeneration. A content change must not mutate a template. Preview and final render must use the same pinned template version.

## Batch generation: required behavior

Batch is not simply a loop around an API request. Implement:
- asynchronous queue/worker model; never hold an HTTP request open for a large batch;
- per-item state: queued, parsing, generating, validating, rendering, completed, failed, cancelled;
- bounded concurrency per provider and renderer;
- retry only transient failures, exponential backoff and dead-letter handling;
- idempotency keys to prevent duplicate artifacts;
- resumable jobs and cancellation;
- progress counters and downloadable error report;
- per-candidate privacy boundaries and tenant isolation before any hosted multi-user release;
- cost/token/time tracking per item and batch;
- deterministic batch configuration snapshot (prompt, model, content schema, template version).

Support at least these batch modes:
1. one candidate → many target roles;
2. one candidate → many template variants;
3. many candidates → one role/template configuration (only with explicit separate candidate records and permissions);
4. one candidate → many vacancies, producing separate application snapshots.

Do not silently bulk-approve high-risk factual changes. Batch generation may bulk-run deterministic low-risk steps, but approval rules remain those in `TAILORING_POLICY.md`.

## Input/import improvements

Support:
- manual form and structured JSON;
- PDF and DOCX import, with original file retained as source;
- text extraction with page/paragraph provenance;
- optional OCR for scanned documents, clearly flagging OCR-derived data;
- parsing into a proposed profile, never directly into confirmed facts;
- duplicate detection for employment, skills and achievements;
- user review/confirmation before facts become eligible for generation;
- explicit locale and date normalization without losing original source text.

A job description should be accepted as pasted text first. URL fetch is optional and must preserve source URL, fetch timestamp and extracted text.

## Quality: what makes a resume competitive

Do not optimize only for keyword density or a fabricated ATS score. Produce a transparent QA report with:
- requirement coverage linked to evidence;
- hard-constraint status;
- role/title and seniority coherence;
- relevance and strength of achievements;
- action/result clarity and metric provenance;
- redundant or generic wording detection;
- missing critical information and unexplained date gaps (flag only; do not invent);
- spelling, grammar, locale and language consistency;
- section completeness and sensible length;
- ATS text extraction and reading order;
- factual claim-to-Fact-ID coverage.

A numerical score may be used internally only if calibrated against a labelled evaluation set and explained; do not present an unvalidated percentage as hiring probability or ATS pass rate. Prefer actionable findings and quality bands with reasons.

Build a golden benchmark of anonymized/synthetic profiles and job descriptions. Evaluate factuality, relevance, readability, ATS extraction and rendering separately. Compare prompt/model/template versions against the same benchmark.

## Code-level findings to address

1. `Fact.tags`, `ResumeItem.fact_ids`, `JobRequirement` lists and `ChangeProposal` lists use mutable literal defaults. Prefer `Field(default_factory=list)` consistently.
2. `Fact.risk_tier` is a free-form string; use an enum. Validate confidence range if retained, while keeping it informational.
3. `ResumeItem` only has `id`, `text`, `fact_ids`, `priority`; this is too weak for robust multi-section CVs and localization.
4. `Resume.protected` is a string dictionary; protected fields should be typed and tied to profile data, with explicit user-approved change workflow.
5. Current validators are heuristic. V2 number matching and V3 capitalized-token matching are not semantic proof of factuality. Preserve the stated policy that ambiguous claims require human review. Add tests for false positives/negatives and claim-level evidence coverage.
6. The code implements V1,V2,V3,V5,V6,V7 only. The docs mention V1–V9 in places; define the complete validator registry and versioned validation contract before relying on it.
7. Validate `expected_version`, operation-specific target shape, and proposal state transitions in domain services; current sample validator does not enforce optimistic concurrency.
8. The Gateway is synchronous. For batch generation, define async provider calls, timeouts, rate limits, structured retries and cancellation, or isolate synchronous providers in worker processes.
9. `DATA_MODEL.md` describes many entities that do not yet have SQLAlchemy models/migrations/services/API endpoints. Track each layer separately in acceptance criteria.
10. ADR-005 (PDF engine) is still open. Resolve font licensing, Cyrillic/Latin/Greek coverage, DOCX strategy and deterministic rendering before implementing template marketplace/custom templates.

## Recommended implementation order

1. Stabilize current contracts, persistence and domain services.
2. Implement candidate profile, Fact Base, structured resume sections and PDF/DOCX import/review.
3. Implement one strong ATS template and one visual template through the template manifest interface.
4. Implement content generation and claim-level validation against golden tests.
5. Implement PDF, DOCX, HTML and JSON renderers/export.
6. Implement preview, template versioning and user-created template configuration.
7. Implement asynchronous batch orchestration, retries, progress and artifact management.
8. Add quality benchmark and operational metrics before scaling volume.
9. Add hosted multi-user tenancy, access control, encryption and retention controls before exposing other people's CVs in a SaaS service.

## Product decision

Make the core product **one canonical candidate profile + many independently versioned content variants + many independently versioned templates + reproducible artifacts**.

This separation is the key architectural decision. It prevents template proliferation from duplicating AI logic and lets one verified profile produce many targeted, branded and localized CVs at scale.
