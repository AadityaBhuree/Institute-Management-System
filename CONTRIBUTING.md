# Contributing to Institute Management System (IMS Enterprise)

Thank you for your interest in contributing to the **Institute Management System (IMS Enterprise)**. We are committed to engineering robust, performant, and secure academic administration software.

---

## 📋 Code of Conduct & Core Engineering Standards

When contributing code, adhere to our core architectural hierarchy:
1. **Correctness** — Functional logic must be deterministic and verified with unit and integration tests.
2. **Security** — All user input must be sanitized and validated via Pydantic schemas. Destructive actions require administrative authentication and audit logging.
3. **Maintainability** — Clean separation of concerns across API routers (`src/api`), service layer (`src/services`), domain models (`src/models`), and data layer (`src/database`).
4. **Performance** — Leverage SQLite WAL mode, pooled database connections, and server-side pagination for collections exceeding default page sizes.

---

## 🛠️ Development Setup

### 1. Prerequisites
- Python 3.10 or higher
- Git
- Virtual environment (`venv` or `conda`)

### 2. Clone and Setup Environment

```bash
# Clone the repository
git clone https://github.com/AadityaBhuree/Institute-Management-System.git
cd Institute-Management-System

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy template configuration
cp .env.example .env

# Generate a cryptographically secure key for local development:
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
```

### 4. Seed Demonstration Data & Launch

```bash
# Seed realistic demo datasets (courses, scholars, admissions, attendance, clinic, assets)
python scripts/seed_demo_data.py

# Launch FastAPI development server with hot-reloading
python -m uvicorn src.app:app --host 127.0.0.1 --port 8000 --reload
```

Access the dashboard at `http://127.0.0.1:8000`.

---

## 🧪 Testing Guidelines

We enforce a comprehensive automated testing policy with **231+ automated unit and integration tests**.

```bash
# Run the complete test suite
pytest -v

# Run with short tracebacks
pytest -v --tb=short

# Run specific domain test suite (e.g., student admissions)
pytest tests/test_students_api.py -v

# Run with test coverage report
pytest --cov=src --cov-report=term-missing
```

Every PR that introduces a new endpoint or modifies business logic **must** include automated tests verifying:
- Happy path execution
- Validation failure rejection (invalid inputs, duplicate codes)
- Authorization and role constraints
- Database state and rollback integrity

---

## 🎨 Code Style, Formatting & Linting

We use **Ruff** for linting and formatting. Ensure your code passes all checks before committing:

```bash
# Check for lint errors
ruff check .

# Check code formatting
ruff format --check .

# Automatically apply formatting
ruff format .
```

### Optional: Pre-commit Hooks
Install pre-commit to run formatting checks automatically on git commit:
```bash
pip install pre-commit
pre-commit install
```

---

## 🔀 Branching & Commit Conventions

### Branch Naming
- `feat/feature-name` — New domain modules or capabilities
- `fix/bug-description` — Defect fixes and edge case patches
- `perf/optimization` — Query optimization, indexing, caching
- `test/suite-name` — Expanding unit or integration test coverage
- `docs/doc-update` — Documentation, guides, or changelogs

### Commit Messages
Follow the Conventional Commits standard:
- `feat(admissions): add batch student enrollment CSV parser`
- `fix(timetable): prevent instructor double-booking collisions`
- `perf(database): add composite index on attendance dates`
- `test(health): add validation tests for prescription dispensary`
- `docs(readme): update test coverage badges and setup instructions`

---

## 🚀 Pull Request Checklist

Before opening a Pull Request, verify:
- [ ] Code passes all lint checks: `ruff check .`
- [ ] Code is formatted cleanly: `ruff format --check .`
- [ ] All 231 tests pass: `pytest`
- [ ] New service operations or endpoints include Pytest coverage
- [ ] No hardcoded secrets, API keys, or raw SQL queries
- [ ] Pydantic v2 schemas used for request and response validation
- [ ] Documentation or CHANGELOG updated if API contracts changed
