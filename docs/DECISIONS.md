# DECISIONS.md (ADR log — append only)
| # | Decision | Status |
|---|---|---|
| 001 | Backend Python/FastAPI, Pydantic v2, SQLAlchemy+Alembic | accepted |
| 002 | Gateway `complete(task, schema)`; FakeLLM first; fallback via config in MVP-1 | accepted |
| 003 | Structured resume with stable IDs; Master→Base→Overlay; immutable versions/snapshots | accepted |
| 004 | Apache-2.0 | accepted (verify dep licenses) |
| 005 | PDF engine: pick RenderCV(Typst) vs WeasyPrint in card T-008; bundle Cyrillic fonts | open |
| 006 | SQLite in MVP-0 → Postgres MVP-1; no pgvector | accepted |
| 007 | No match %, use table + buckets; no auto-submit | accepted |
| 008 | Reuse as reference only: Reactive Resume (UX), RenderCV (PDF), Resume Matcher (ideas); no monolith merge | accepted |
Template: `NNN | decision | context | consequences`.
| 009 | Stretch layer: user-approved, low-risk-only claim softening (`verification_status=user_stretch`, required `interview_note`, labeled in UI/snapshot). AI may suggest, never apply. Context: market expects CV tuned to unfamiliar tools. Consequences: V3 allows approved stretch; V2/V5 never; card T-030. | accepted |
| 010 | Positioning: AI Career Adaptation Platform. Add Transferable Skills Discovery, Skill Graph (relational reviewed edges, no vector DB), Role Taxonomy (4 distance levels), Role Discovery, Gap Analysis, Adaptive Tailoring. Context: matching only by job title/tech name loses fitting vacancies. Consequences: cards T-031..T-037. | accepted |
| 011 | Match categories replace matched/partial/unmatched/unclear: `direct`, `transferable`, `potential`, `genuine_gap` (old→new: matched→direct, partial→transferable, unclear→potential, unmatched→genuine_gap). Buckets Strong/Possible/Stretch/Blocked and "no percentage" (ADR-007) unchanged. | accepted |
| 012 | Search modes `strict` / `expanded` (default) / `exploration`; no artificial limit on role distance. Hard constraints always gate. Vacancy counts per direction only from user-supplied/licensed data, never fabricated; no scraping of closed sites. | accepted |
| 013 | Transferable ≠ confirmed experience. Transferable/direct findings must cite `fact_ids`; `potential` becomes a ClarificationQuestion; transferable evidence may be framed (R2) but never worded as direct experience in a new area (validator V10, T-036). Skill Graph edges suggested by LLM are `reviewed=false` and are never proof. Matching must analyse duties, level, complexity, results, not tech-name overlap. | accepted |
