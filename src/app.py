"""Institute Management System - FastAPI Core Application.
Orchestrates static assets, Jinja2 template rendering, REST API routers, and database lifespan.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from src.api.academics import router as academics_router
from src.api.alumni import router as alumni_router
from src.api.announcements import router as announcements_router
from src.api.auth import router as auth_router
from src.api.courses import router as courses_router
from src.api.dashboard import router as dashboard_router
from src.api.departments import router as departments_router
from src.api.events import router as events_router
from src.api.faculty import router as faculty_router
from src.api.finance import router as finance_router
from src.api.health_center import router as health_center_router
from src.api.hostel import router as hostel_router
from src.api.inventory import router as inventory_router
from src.api.leaves import router as leaves_router
from src.api.library import router as library_router
from src.api.notifications import router as notifications_router
from src.api.placements import router as placements_router
from src.api.reports import router as reports_router
from src.api.scholarships import router as scholarships_router
from src.api.students import router as students_router
from src.api.system import router as system_router
from src.api.timetable import router as timetable_router
from src.api.transport import router as transport_router
from src.core.config import (
    ALLOWED_ORIGINS,
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
    ENABLE_DOCS,
    MAX_REQUEST_SIZE_BYTES,
    RATE_LIMIT_DEFAULT,
    RATE_LIMIT_ENABLED,
    STATIC_DIR,
)
from src.core.exceptions import register_exception_handlers
from src.core.logging_config import setup_logging
from src.core.openapi import OPENAPI_TAGS
from src.core.security_hardening import (
    RequestBodySizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from src.database.init_db import init_database
from src.web.pages import router as pages_router
from src.web.pages import templates


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown routines."""
    setup_logging()
    init_database()

    # Startup: Run overdue invoice synchronization in background
    try:
        from src.database.connection import get_connection, release_connection
        from src.services.finance_service import FinanceService

        startup_conn = get_connection()
        try:
            synced = FinanceService.sync_overdue_invoices(startup_conn)
            if synced > 0:
                logging.getLogger("ims").info(
                    "Synchronized %d overdue invoices on startup.", synced
                )
        finally:
            release_connection(startup_conn)
    except Exception as e:
        logging.getLogger("ims").warning("Overdue sync on startup skipped: %s", e)

    yield

    # Shutdown: Close database connection pool
    from src.database.connection import close_pool

    close_pool()


app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None,
)

# Global Rate Limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[RATE_LIMIT_DEFAULT],
    enabled=RATE_LIMIT_ENABLED,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Register Glassmorphic HTML and Structured JSON Error Handlers
register_exception_handlers(app, templates)

# Security Hardening & Cross-Origin Resource Sharing (CORS) Middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    RequestBodySizeLimitMiddleware,
    max_body_bytes=MAX_REQUEST_SIZE_BYTES,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST API Routers
api_routers = [
    auth_router,
    students_router,
    courses_router,
    faculty_router,
    academics_router,
    finance_router,
    reports_router,
    announcements_router,
    leaves_router,
    timetable_router,
    library_router,
    hostel_router,
    placements_router,
    transport_router,
    scholarships_router,
    alumni_router,
    events_router,
    inventory_router,
    health_center_router,
    departments_router,
    dashboard_router,
    notifications_router,
    system_router,
]
for r in api_routers:
    app.include_router(r)

# Mount Web Page Routers
app.include_router(pages_router)

# Ensure directories exist and mount static assets
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
