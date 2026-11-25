.PHONY: demo setup dev test lint fmt typecheck check golden clean migrate
PY=cd backend && . .venv/bin/activate &&
setup:
	if [ ! -f backend/.env ]; then cp .env.example backend/.env; fi
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]" && .venv/bin/pre-commit install || true
	$(PY) alembic upgrade head
migrate:
	$(PY) alembic upgrade head
demo:  ## open http://localhost:8000 (demo UI)
	$(PY) uvicorn app.main:app --port 8000
dev:
	$(PY) uvicorn app.main:app --reload --port 8000
test:
	$(PY) pytest -q
golden:
	$(PY) pytest -q tests/golden
lint:
	$(PY) ruff check . && ruff format --check .
fmt:
	$(PY) ruff check --fix . && ruff format .
typecheck:
	$(PY) mypy app
check: lint typecheck test   ## MUST pass before every commit/PR
clean:
	rm -rf backend/.pytest_cache backend/.ruff_cache backend/.mypy_cache
