.PHONY: setup dev test lint fmt typecheck check golden clean
PY=cd backend && . .venv/bin/activate &&
setup:
	if [ ! -f backend/.env ]; then cp .env.example backend/.env; fi
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]" && .venv/bin/pre-commit install || true
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
