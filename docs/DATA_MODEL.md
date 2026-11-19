# DATA_MODEL.md
All persisted JSON documents include `schema_version`; use stable string IDs (`<kind>_<ulid>`).

| Entity | Key fields / rules |
|---|---|
| CandidateProfile | id, name, contacts, locale prefs, hard constraints (visa, location, languages) |
| CandidateFact | id, text, normalized_claim, category, tags[], risk_tier, verification_status (source_backed/confirmed/unverified/user_stretch; user_stretch needs interview_note, low-risk categories only), source_reference, evidence_ref, approved_variants[], version, created_at |
| FactAlias | canonical_skill_id, alias, locale, source, reviewed; alias normalizes terminology but does not prove experience |
| MasterResume | id, profile_id, immutable source structure and fact references |
| BaseResume | id, profile_id, structured sections/items with stable IDs, priority, approved variants, fact_ids |
| ResumeVersion | immutable copy of BaseResume, version, content_hash |
| JobPosting | id, url_normalized (dedupe), raw_job_description, extraction_metadata{confidence,warnings,unparsed}, source |
| JobRequirement | id, job_id, text, kind (must/nice/hard_constraint), normalized_skill_ids[], evidence_ids[], user_confirmed |
| MatchReport | job_id, resume_version, per-requirement match category (direct/transferable/potential/genuine_gap) with fact_ids, hard_constraint pass/fail, bucket (strong/possible/stretch/blocked), inputs_hash; no percentage |
| SkillEdge | source_skill_id, target_skill_id, relation (evidences/part_of/adjacent_to), reviewed; relational Skill Graph, unreviewed edges are never proof |
| RoleTaxonomyEntry | id, title, level 1–4, skill_ids[] |
| TransferableFinding | id, requirement_id, category, competence, fact_ids[], rationale; direct/transferable require fact_ids, genuine_gap forbids them |
| RoleSuggestion | role_id, level, why, supporting_fact_ids[≥1], gap_skill_ids[]; run in a SearchMode (strict/expanded/exploration) |
| Application | id, job_id, status, next_action_date, contacts |
| JobOverlay | application_id, base_resume_version, approved patches[] |
| ChangeProposal | id, run_id, target_id, operation, before, after, change_reason, requirement_ids[], fact_ids[], risk_tier (R0–R2), dedupe_key, expected_version, status, validators_passed[], blocked_reason |
| ClarificationQuestion | requirement_id, question, status, answer, resulting_fact_id |
| AnswerBank | key, locale, value, kind |
| ApplicationSnapshot | application_id, frozen approved docs, content_hash, pdf_hash, template_version, renderer_version; immutable |
| LLMRun | id, run_id, step, prompt_id@version, input_hash, model, tokens, latency_ms, error_class |
| AuditEvent | actor, action, entity, before/after hash, ts |

## Invariants
0. A transferable/direct finding without Fact IDs is invalid; transferable never equals confirmed experience in the target role (ADR-013).
1. Master facts are changed only by explicit user action through domain services; LLM proposals cannot mutate them.
2. Every factual claim in an exported resume/letter traces to one or more eligible, approved Fact IDs.
3. `confidence` is informational and never confirms a fact.
4. Base edits never alter ResumeVersions/Snapshots. Overlay binds to one ResumeVersion.
5. A proposal applies only when expected_version matches current version; otherwise conflict/rebase.
6. Statuses change only through domain services; state-machine tests are mandatory.
7. Duplicate dedupe_key insert is ignored/idempotent.
8. Snapshot is created only after G4 passes and all included changes are approved.
