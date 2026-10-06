"""Institute Management System - Core Configuration.
Provides application-wide settings, paths, and environment defaults.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
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

# Security & Sessions
SECRET_KEY = os.getenv("SECRET_KEY", "ims_enterprise_secure_token_key_2026")
DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
