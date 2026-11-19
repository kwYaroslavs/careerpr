# DEVELOPMENT.md — the correct way to work (humans and AIs)

## 1. Prerequisites
Python 3.12, Node 20+ (frontend, later), Git, Make, Docker (optional in MVP-0). Optional: Ollama for local models.

## 2. First run
```bash
git clone <repo> && cd careerpr
cp .env.example .env          # LLM_PROVIDER=fake works with no keys
make setup                    # venv + deps + pre-commit hooks
make test                     # must be green on a clean checkout
make dev                      # API on http://localhost:8000 (/docs = Swagger)
```
Default is `LLM_PROVIDER=fake` (FakeLLM + fixtures): the whole pipeline runs offline, deterministic, zero quota. Switch to a real provider only via `.env`.

## 3. Commands
| Command | Purpose |
|---|---|
| `make dev` | run API with reload |
| `make test` | all tests (offline) |
| `make golden` | golden e2e only (CV+JD → PDF on FakeLLM) |
| `make lint` / `make fmt` | ruff check+format check / autofix |
| `make typecheck` | mypy (strict on `app/`) |
| `make check` | lint + typecheck + test. **Run before every commit** |
| Live LLM smoke | `LLM_PROVIDER=gemini pytest -m live` (manual, never in CI) |
| Migrations | `cd backend && alembic revision --autogenerate -m "msg"` then `alembic upgrade head` |

## 4. Branching
- `main` is always green and releasable. **Never push to main directly**; branch protection: PR + passing CI.
- One task card = one branch = one PR. Small PRs (< ~400 changed lines excl. fixtures).
- Branch name: `<type>/T-<id>-<slug>`, e.g. `feat/T-004-validators-v1-v3`. Types: `feat fix refactor test docs chore`.
```bash
git switch main && git pull --ff-only
git switch -c feat/T-004-validators-v1-v3
```

## 5. Commit rules
Conventional Commits: `type(scope): imperative summary` ≤ 72 chars.
Examples: `feat(validators): add V2 no-new-numbers`, `fix(gateway): retry only on 429/timeout`, `docs(data-model): add AnswerBank`.
- Commit small, logical steps. Body explains *why* if not obvious. Reference card: `Refs T-004`.
- Never commit: `.env`, keys, real CVs/PII, `data/`, `*.sqlite`, generated PDFs (except golden fixtures with fake data).

## 6. Pre-commit routine (every time)
```bash
git status && git diff          # read your own diff; remove debug/unrelated changes
make fmt                        # autofix style
make check                      # lint + mypy + tests — must be green
git add -p                      # stage deliberately, not `git add .`
git commit -m "feat(scope): ..."
```
Pre-commit hooks (ruff, secrets/large-file guards) run automatically; if a hook modifies files, re-stage and recommit. Do not use `--no-verify`.

## 7. Pushing & PR
```bash
git fetch origin && git rebase origin/main     # keep linear, resolve conflicts locally
make check                                     # again after rebase
git push -u origin HEAD                        # force only with --force-with-lease on YOUR branch
gh pr create --fill                            # or via web UI; fill PR template
```
PR must: link the card, pass CI, tick checklist, list what was NOT done. Draft PR if unfinished.

## 8. Review & merge
- Reviewer (human or AI) checks: scope matches card; golden rules in `AGENTS.md` intact; tests for new logic; no contract drift; no secrets.
- Review AI-written PRs adversarially: look for invented facts paths, missing validator, LLM doing backend work.
- Merge: **squash merge** into `main` (title = conventional commit). Delete branch after.
- After merge: `git switch main && git pull --ff-only`; mark card `done` (done in the PR already; verify).

## 9. Testing policy
- Validators V1–V9, versioning, dedupe/idempotency, state machines → **unit tests, mandatory**.
- LLM parts → contract tests with recorded responses (`tests/fixtures/cassettes/`) through Pydantic + validators.
- Golden e2e: 3–5 fake CV+JD pairs, no network. Adversarial set: injection JD, empty JD, wrong language, huge JD, CV w/o dates, visa mismatch.
- CI never calls real LLMs. Live smoke is manual/scheduled, marked `@pytest.mark.live`.
- Bug fix = first a failing test, then the fix.

## 10. Rules for AI coders
- Take exactly one card. Don't refactor outside Scope; don't "improve" architecture.
- Don't invent endpoints/fields: use `schemas.py` and `DATA_MODEL.md`. Missing something → open a card/ADR, not a silent change.
- Prompts live in `backend/prompts/<id>@<version>.md`; changing a prompt = new version, never edit in place.
- Fixtures contain fake data only.
- If blocked or uncertain: write the question in the PR/card under `Open questions`, keep the PR draft.
- Keep context small: read only the docs the card lists.

## 11. Definition of Done (per card)
Acceptance criteria met · `make check` green · tests added · docs/contracts updated · card status updated · PR squash-merged.

## 12. Release/Backup notes
Tag milestones `mvp-0`, `mvp-1`. DB migrations only forward via Alembic; JSON documents carry `schema_version`. Export-all endpoint is a required feature (data loss protection).
