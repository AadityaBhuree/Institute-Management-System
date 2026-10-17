"""Institute Management System - Core Configuration.
Provides application-wide settings, paths, and environment defaults.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _load_env_file(env_path: Path) -> None:
    """Load key-value pairs from .env file into os.environ if not already present."""
    if not env_path.is_file():
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


_load_env_file(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = Path(os.getenv("IMS_DB_PATH", str(DATA_DIR / "institute.db")))
DATABASE_URL = f"sqlite:///{DB_PATH}"

APP_NAME = "Institute Management System"
APP_DESCRIPTION = (
    "Modular Educational Enterprise Management, Admissions, Academic Schedules & Financial Audit"
)
APP_VERSION = "1.0.0"
API_V1_STR = "/api"

DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

# Security & Secrets
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG or os.getenv("TESTING") or os.getenv("PYTEST_CURRENT_TEST"):
        SECRET_KEY = "dev-insecure-secret-key-change-in-production"
    else:
        raise RuntimeError(
            "CRITICAL SECURITY CONFIGURATION ERROR: 'SECRET_KEY' environment variable is not set. "
            "Define it in your environment or create a .env file (see .env.example)."
        )

# Cross-Origin Resource Sharing (CORS)
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000"
    ).split(",")
    if origin.strip()
]

# Rate Limiting
RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "100/minute")

STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
