.PHONY: install dev dev-web dev-api test lint format clean deploy
.PHONY: seed

# ── Install ────────────────────────────────────────────────────────────────────
install:
	cd apps/web && python3 -m pip install -r requirements.txt
	cd apps/api && python3 -m pip install -r requirements.txt

# ── Dev ────────────────────────────────────────────────────────────────────────
dev:
	@echo "Starting Jonche Platform..."
	make dev-api & make dev-web

dev-web:
	cd apps/web && python3 app.py

dev-api:
	cd apps/api && python3 app.py

# ── DB Seed (dev) ──────────────────────────────────────────────────────────────
seed:
	cd apps/api && python3 -m db.seed

# ── Test ───────────────────────────────────────────────────────────────────────
test:
	cd apps/api && python3 -m pytest tests/ -v
	cd apps/web && python3 -m pytest tests/ -v

test-api:
	cd apps/api && python3 -m pytest tests/ -v

test-web:
	cd apps/web && python3 -m pytest tests/ -v

# ── Code Quality ───────────────────────────────────────────────────────────────
lint:
	ruff check apps/ packages/

format:
	ruff format apps/ packages/

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
