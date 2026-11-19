# ARCHITECTURE.md
```
frontend (Next.js/TS, later card) ── REST ──> backend (FastAPI)
backend/app
  api/         thin HTTP routers, no logic
  domain/      schemas.py (Pydantic), models (SQLAlchemy), services (pure logic: apply patch, versioning, snapshot, state machines)
  gateway/     LLMGateway.complete(task, schema) → providers: fake, gemini, ollama (+fallback in MVP-1)
  career/      skill_graph, transferable (discovery), roles (taxonomy + discovery, search modes), gaps
  validators/  V1–V9 deterministic, each: (proposal, ctx) -> list[Violation]
  pipeline/    steps G1..G4, each step persisted; resumable by run_id
  render/      Markdown + PDF (RenderCV or Typst/WeasyPrint — ADR-005), fit-loop, round-trip (PyMuPDF)
  core/        config, logging, db
prompts/       versioned prompt files <id>@<ver>.md
```
## Pipeline
`Import JD → [G1 extract] → [G2 user confirms reqs] → triage → evidence map → clarify gaps → proposals R0→R2 → [G3 validators] → review → render+fit → [G4 readiness] → snapshot`
Career layer (before/around triage): `Fact Base → Skill Graph → Transferable Skills Engine → Role Discovery (mode: strict|expanded|exploration) → Gap Analysis → Adaptive Tailoring`. Skill Graph is relational (no vector DB).
Each step writes to DB; `run_id` resumes from last finished step. Steps are narrow LLM calls with small JSON outputs.

## Layer rules
- api → domain/services → (gateway, validators, render). Domain never imports api.
- Only `domain/services` mutate resumes/statuses. LLM output is data until validated.
- Gateway: one method `complete(task, schema, inputs)`; provider chosen by config; each call logs an `LLMRun` (prompt_id@ver, input hash, model, tokens, latency, error class).
- Cache key: `hash(inputs + prompt_version + facts_version)`.
- Whole Fact Bank fits in context (hundreds of facts) → pass compact list with IDs; no retrieval.
- DB: SQLite in MVP-0, Postgres in MVP-1 (SQLAlchemy 2 + Alembic from day 1). JSON docs carry `schema_version`.

## Stack
Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, pytest, ruff, mypy; PyMuPDF (round-trip), LiteLLM optional behind Gateway; Next.js + shadcn/ui frontend; Docker Compose.
