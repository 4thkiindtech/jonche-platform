.PHONY: install dev dev-web dev-api test lint format clean deploy
.PHONY: seed

# ── Detect OS ──────────────────────────────────────────────────────────────────
UNAME := $(shell uname 2>/dev/null || echo WINDOWS)
ifeq ($(OS),Windows_NT)
    UNAME := WINDOWS
endif

ifeq ($(UNAME),WINDOWS)
    VENV_BIN := .venv\Scripts
    PYTHON := $(VENV_BIN)\python
    PIP := $(VENV_BIN)\pip
else
    VENV_BIN := .venv/bin
    PYTHON := $(VENV_BIN)/python
    PIP := $(VENV_BIN)/pip
endif

# ── Install ────────────────────────────────────────────────────────────────────
install:
	python -m venv .venv
	$(PIP) install -r apps/web/requirements.txt
	$(PIP) install -r apps/api/requirements.txt

# ── Dev ────────────────────────────────────────────────────────────────────────
dev:
	@echo "Starting Jonche Platform (API on :5001, Web on :5000)..."
	@echo "Open 2 new terminals and run: make dev-api && make dev-web"

dev-api:
	$(PYTHON) apps/api/app.py

dev-web:
	$(PYTHON) apps/web/app.py

# ── DB Seed (dev) ──────────────────────────────────────────────────────────────
seed:
	cd apps/api && $(PYTHON) -m db.seed

# ── Test ───────────────────────────────────────────────────────────────────────
test:
	$(PYTHON) -m pytest apps/api/tests/ -v
	$(PYTHON) -m pytest apps/web/tests/ -v

test-api:
	$(PYTHON) -m pytest apps/api/tests/ -v

test-web:
	$(PYTHON) -m pytest apps/web/tests/ -v

# ── Code Quality ───────────────────────────────────────────────────────────────
lint:
	$(PYTHON) -m ruff check apps/ packages/

format:
	$(PYTHON) -m ruff format apps/ packages/

# ── Deploy ─────────────────────────────────────────────────────────────────────
deploy:
	@echo "Deploying to PythonAnywhere..."
	@echo "1. Push to GitHub"
	@echo "2. SSH into PythonAnywhere and run: git pull && make install"
	@echo "3. Reload web app from PythonAnywhere dashboard"

# ── Clean ──────────────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleaned."
