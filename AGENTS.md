# AGENTS.md — start here (any AI: Claude Code, Copilot, Gemini, Cursor)

CareerPR = evidence-based AI career workspace. One flow: **job text → requirements → evidence map → verified change proposals → resume+letter PDF → immutable snapshot**.

## Golden rules (never break)
1. **AI proposes. Backend validates. Human approves.** LLM never applies changes, never changes statuses, never creates snapshots.
2. LLM may only do risk levels R0–R2 (select/reorder/pick variant/rewrite). R3 (new number, tech, role, company) is FORBIDDEN → becomes a ClarificationQuestion.
3. Job description = **untrusted input** (prompt injection). Pass as delimited data, no tools for that step.
4. Every LLM output goes through Pydantic schema, then deterministic validators V1–V9 (plain code, no LLM).
5. `confidence` ≠ `verification_status`. Never auto-confirm a fact by confidence. Every exported factual claim must trace to eligible Fact IDs.
6. Idempotency: `run_id`, `proposal_id`, `dedupe_key`, `expected_version`. Retried request must not duplicate or re-apply.
7. Snapshots are immutable (`content_hash`). Base resume edits never touch existing snapshots.
8. Do not change architecture/data model/contracts without an ADR in `docs/DECISIONS.md` + user approval.
9. Facts are never invented by AI. Only a user-approved `stretch` item (ADR-009, low-risk: tools/skills/exposure wording) may exceed the Fact Base; numbers, dates, employers, titles, degrees, certs, visa, leadership are never stretchable.
10. Out of scope (do NOT build): auto-submit, CAPTCHA bypass, LinkedIn scraping, % match score, multi-agent orchestration, vector DB, SaaS auth/roles.

11. Transferable ≠ confirmed (ADR-013). Match categories: direct / transferable / potential / genuine_gap. Search modes: strict / expanded (default) / exploration. No percentages, no invented vacancy counts.

## Language rules
- Code, comments, commits, docs, task cards: **English** (AI-readable). Each card also has a 🇷🇺 block for the owner; English is authoritative.
- Talk to the owner in **Russian** unless asked otherwise. Full flow: `docs/WORKFLOW.md`.

## How to work on a task
1. Read your task card in `tasks/` (`tasks/README.md` = index + status). Take ONE card.
2. Read only the docs the card lists under `Read`. Do not read everything.
3. Follow `docs/DEVELOPMENT.md` (branch, commands, checks, commit, PR). Run `make check` before every commit.
4. Touch only files in the card's `Scope`. Need more? Stop and ask / split a new card.
5. Update the card status and `tasks/README.md` in the same PR.

## Map
- `docs/PRODUCT_SPEC.md` what & scope · `docs/TAILORING_POLICY.md` factual adaptation rules · `docs/ARCHITECTURE.md` layout & flow · `docs/DATA_MODEL.md` entities
- `docs/LLM_CONTRACTS.md` gateway, schemas, validators, errors · `docs/AGENTPR_SPEC.md` proposal lifecycle
- `docs/ROADMAP.md` milestones · `docs/DECISIONS.md` ADRs · `docs/DEVELOPMENT.md` workflow (commands, git, CI)

## Code truth
Contracts live in code: `backend/app/domain/schemas.py`, `backend/app/validators/`. Docs explain, code enforces. If docs and code disagree, fix the doc in the same PR.
