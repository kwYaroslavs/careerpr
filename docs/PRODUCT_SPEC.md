# PRODUCT_SPEC.md
## Idea
Evidence-based AI career workspace. The candidate maintains a verified Fact Base and a structured Master Resume. For each vacancy, CareerPR maps requirements to evidence and proposes a tailored presentation without inventing facts. The user approves changes; the final application is frozen as an immutable snapshot.

Positioning: **AI Career Adaptation Platform** (ADR-010): understand the whole professional potential of a person, find roles and vacancies beyond the current job title, discover transferable skills, and honestly show where the candidate fits and where experience is missing. AI automation with human-in-the-loop, deterministic validation and provider-independent LLM gateway.

## Primary scenario
1. Candidate creates/imports a profile and Master Resume. Facts are stored with stable IDs, verification status and evidence references.
2. Candidate pastes vacancy text. The system stores the raw JD and extracts must-have, nice-to-have and hard constraints.
3. Candidate reviews and confirms extracted requirements.
4. System builds a requirement-to-fact evidence map and hard-constraint gate. Each requirement gets a category: `direct`, `transferable`, `potential` or `genuine_gap` (ADR-011). Overall bucket: Strong / Possible / Stretch / Blocked. Never show a percentage match.
5. System proposes minimal changes: reorder, select approved variant, or rewrite without new facts. Every proposal links to source facts and vacancy requirements.
6. Deterministic validators check IDs, numbers, entities, protected data, placeholders and company leakage. Uncertain claims are blocked or sent to clarification.
7. User reviews and approves/rejects/edits proposals. High-risk claims require individual approval.
8. Cover letter uses 2–3 supported facts and one sourced company hook. If no reliable hook is available, ask the user; do not invent research.
9. Render Markdown/PDF, run fit-loop and round-trip text checks, then Readiness Gate G4.
10. Create immutable ApplicationSnapshot from approved content only.

## Career adaptation (ADR-010..013)
- **Search modes:** Strict Match (direct only) · Expanded Match (adjacent roles + transferable skills, **default**) · Career Exploration (widest, incl. distant IT directions with explanations). No artificial limit on role distance; hard constraints still gate.
- **Transferable Skills Discovery:** from Fact Base facts finds competences applicable elsewhere (e.g. Redis → caching/performance engineering; Docker + CI/CD → platform/deployment automation). A transferable competence is not confirmed experience in the new area.
- **Match categories:** Direct (confirmed) · Transferable (other-area experience applies) · Potential (likely, ask the user) · Genuine Gap (absent). Example, requirement AWS: used AWS → Direct; other cloud/infra → Transferable; infra work not described → Potential; none → Genuine Gap.
- **Role Discovery:** proposes role directions from the Role Taxonomy (levels 1–4) with a "why this may fit" explanation and gaps. Vacancy counts per direction are shown only when real data exists (user-saved JDs or a licensed source); never invented.
- **Adaptive Tailoring:** resume for a distant role frames true experience in that role's terms; never claims direct experience that is only transferable.
- LLM must reason over duties, responsibility level, task complexity and confirmed results, not tech-name matching.

## Tailoring policy
See `TAILORING_POLICY.md`. The product has three layers:
- Immutable Fact Base / Master Resume: factual source of truth.
- Adaptive Framing: vacancy-specific ordering and truthful rewriting.
- Controlled Gap / Authenticity Buffer: retain useful adjacent evidence; never fill missing requirements with invented claims.

Do not target a fixed 80–90% or 100% match. No percentage scoring. Optimize evidence coverage, clarity, relevance and credibility. Keep a useful adjacent achievement when it adds signal; there is no fixed quota.

## Scope
- MVP-0: structured profile and resume, manual fact entry, FakeLLM, one real provider behind Gateway, JD paste/extraction/confirmation, evidence map, bucket/hard-constraint gate, proposals and deterministic validators, cover letter, Markdown/PDF renderer, fit-loop/round-trip, snapshot, golden tests and simple workspace UI.
- MVP-1: PDF/DOCX import, richer Fact Bank and evidence capture, Master→Base→Overlay versioning, clarification workflow, Answer Bank, reviewed skill ontology, tracker, provider fallback, privacy controls, Postgres and additional validators.
- Phase 2: MCP server, sourced company research, interview copilot, DOCX/ZIP export and analytics.

## Never build
Auto-submit, CAPTCHA bypass, scraping closed sites (including LinkedIn), percentage match score, multi-agent orchestration, vector DB, SaaS auth/roles.

## Key product rules
- Risk ladder: R0 select/reorder; R1 choose approved variant; R2 rewrite without new data; R3 introduce unsupported data and is forbidden.
- LLM output is untrusted data. It cannot mutate facts, statuses, approvals or snapshots.
- Minimal Intervention: no proposal without tangible benefit.
- Every proposal includes `change_reason`, `requirement_ids`, `fact_ids`, `expected_version`.
- High-risk factual claims require individual review.
- Privacy default is local-only; cloud provider requires explicit consent.
- JD URL import is best-effort; pasted text is the primary path.

## MVP acceptance
Three real vacancies can be processed text-to-PDF; every factual claim in final output is traceable to approved evidence; no unverified claim is exported; page limit and round-trip checks pass; reruns do not duplicate proposals; offline tests are green.
