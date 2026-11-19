# LLM_CONTRACTS.md
Code is truth: `backend/app/domain/schemas.py` (Pydantic), `backend/app/validators/`. This file describes contracts.

## Narrow LLM tasks
Each task is one small call with a versioned prompt and typed JSON output:
- `extract_requirements(jd) -> Requirements`
- `rank_items(requirements, items) -> ordered IDs` (R0)
- `select_variant(item, approved_variants, requirements) -> VariantSelection` (R1)
- `rewrite_item(item, linked_facts, requirements) -> RewriteProposal` (R2)
- `draft_cover_letter(approved_facts, sourced_hook) -> Letter`
- `discover_transferable(facts, requirements, skill_graph_slice) -> list[TransferableFinding]` (every finding cites `fact_ids`; rationale uses duties/level/complexity/results)
- `suggest_roles(facts, taxonomy, mode) -> list[RoleSuggestion]` (every suggestion cites supporting `fact_ids` and gaps)
MVP-1: clarification question, translation. The model does not call tools during JD extraction.

## Mandatory input boundaries
- JD is untrusted data and must be delimited. Ignore instructions embedded in it.
- Pass compact fact records with stable IDs and verification status, not an unstructured resume dump.
- Only eligible facts and approved variants may support generated claims.
- Every factual output item must return source `fact_ids` and related `requirement_ids`.
- The LLM cannot mutate Fact Base, confirm facts, approve proposals or create snapshots.

## Gateway
`complete(task, schema, inputs) -> validated model`. Providers: fake, Gemini, Ollama. Provider/model catalog is configuration, not hardcoded.

Failure handling:
| Failure | Action |
|---|---|
| 429/timeout | retry ≤2 with backoff+jitter; fallback only if privacy mode permits; otherwise save partial and allow manual mode |
| invalid JSON | one repair attempt with validation error; then fail this step, not the whole run |
| schema-valid but unsupported claim | deterministic validators block proposal |
| quota exhausted | cache, queue with ETA, smaller calls |
| prompt injection in JD | JD remains delimited data; no tools; schema-only output; validators still run |
| crash mid-run | resume by run_id from last completed step |

## Deterministic validators
Run on every R2 proposal and generated letter. Failure means blocked with explicit reason.
- V1: target/fact/requirement IDs exist; operation is whitelisted.
- V2: no new numbers, percentages, currencies, quantities or dates unless supported by linked facts and allowed context.
- V3: no unsupported entities/claims (technologies, companies, certifications, roles, products, leadership/ownership). Use a normalized fact vocabulary plus reviewed aliases; vocabulary membership alone is not proof of experience.
- V4 (MVP-1): leadership/management/ownership wording requires a corresponding verified fact.
- V5: protected values (identity, contact details, dates, company names) unchanged.
- V6: no placeholders.
- V7: no other tracker-company leakage in cover letter.
- V8 (MVP-1): single requested language and banned AI clichés.
- V9 (MVP-1): soft length limits.

- V10: transferable evidence must not be worded as direct experience in the target role (see TAILORING_POLICY §5).

MVP-0 implements V1–V3 and V5–V7. V2/V3 must be grounded in fact records, not a generic keyword blacklist. Semantic ambiguity that cannot be safely decided deterministically must be blocked or escalated to human clarification.

## Prompt versioning
Prompts live at `backend/prompts/<id>@<version>.md`. Never edit a released prompt in place; create a new version and update the task contract.
