# ==============================================================================
# Institute Management System (IMS Enterprise) — Developer Makefile
# ==============================================================================
# Cross-platform developer convenience targets for running, testing, linting,
# seeding demo records, generating hot database backups, and building containers.
# ==============================================================================

.PHONY: help install run dev test test-cov lint format check seed backup restore load-test clean docker-build docker-run

# Determine python command
PYTHON ?= python
PYTEST ?= $(PYTHON) -m pytest
RUFF ?= $(PYTHON) -m ruff

help:
	@echo "Institute Management System (IMS Enterprise) — Available Targets:"
	@echo "  make install      - Install Python dependencies from requirements.txt"
	@echo "  make run          - Start production ASGI server with Uvicorn"
	@echo "  make dev          - Start development server with hot reload on port 8000"
	@echo "  make test         - Run full Pytest test suite (238+ tests)"
	@echo "  make test-cov     - Run Pytest with test coverage reporting"
	@echo "  make lint         - Check codebase with Ruff linter"
	@echo "  make format       - Format codebase with Ruff"
	@echo "  make check        - Run linter, format check, and test suite in sequence"
	@echo "  make seed         - Seed SQLite database with realistic demonstration data"
	@echo "  make backup       - Create an atomic hot point-in-time database backup"
	@echo "  make restore      - Restore database from snapshot (FILE=ims_backup_YYYYMMDD_HHMMSS.db)"
	@echo "  make load-test    - Run concurrent load and benchmark test (15 workers, 150 requests)"
	@echo "  make clean        - Clean cache directories (.pytest_cache, .ruff_cache, __pycache__)"
	@echo "  make docker-build - Build production multi-stage Docker container"
	@echo "  make docker-run   - Run application via Docker Compose"

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) -m uvicorn src.app:app --host 0.0.0.0 --port 8000

dev:
	$(PYTHON) -m uvicorn src.app:app --host 127.0.0.1 --port 8000 --reload

test:
	$(PYTEST) -v --tb=short

test-cov:
	$(PYTEST) --cov=src --cov-report=term-missing --cov-report=html

lint:
	$(RUFF) check .

format:
	$(RUFF) format .

check: lint
	$(RUFF) format --check .
	$(PYTEST) -q

seed:
	$(PYTHON) scripts/seed_demo_data.py

backup:
	$(PYTHON) -c "from src.database.connection import get_connection, release_connection; from src.services.system_service import SystemService; conn = get_connection(); res = SystemService.create_backup(conn); release_connection(conn); print('Backup created:', res['filename'], '(', res['size_kb'], 'KB)')"

restore:
	@echo "Restoring database from: $(FILE)"
	$(PYTHON) -c "import sys; from src.database.connection import get_connection, release_connection; from src.services.system_service import SystemService; file = sys.argv[1]; conn = get_connection(); res = SystemService.restore_backup(conn, file); release_connection(conn); print('Restore successful:', res['filename'])" "$(FILE)"

load-test:
	$(PYTHON) scripts/load_test.py --concurrency 15 --requests 10

clean:
	@rm -rf .pytest_cache .ruff_cache .coverage htmlcov
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

docker-build:
	docker build -t ims-enterprise:latest .

docker-run:
	docker compose up --build -d
