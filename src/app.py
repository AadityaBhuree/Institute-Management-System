"""Institute Management System - FastAPI Core Application.
Orchestrates static assets, Jinja2 template rendering, REST API routes, and database lifespan.
"""

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
    RATE_LIMIT_DEFAULT,
    RATE_LIMIT_ENABLED,
    STATIC_DIR,
)
from src.core.logging_config import setup_logging
from src.database.init_db import init_database
from src.web.pages import router as pages_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown routines."""
    setup_logging()
    init_database()
    yield


OPENAPI_TAGS = [
    {
        "name": "Students & Admissions",
        "description": "Admissions registry, student demographics, enrollment ID generation, and dossier profiles.",
    },
    {
        "name": "Courses & Curriculum",
        "description": "Department course catalog, credit tracking, and capacity-enforced student course enrollments.",
    },
    {
        "name": "Faculty Directory",
        "description": "Academic instructors, designation hierarchy, course assignments, and faculty portal.",
    },
    {
        "name": "Academics & Attendance",
        "description": "Daily session registers, examination scheduling, letter grading evaluation, and performance.",
    },
    {
        "name": "Finance & Bursar",
        "description": "Fee schedules, student invoicing, payment receipts, overdue balances, and fiscal audit ledger.",
    },
    {
        "name": "Notice Board",
        "description": "Campus announcements, priority broadcast levels, and audience-targeted institutional bulletins.",
    },
    {
        "name": "Lecture Timetable",
        "description": "Weekly academic schedule matrix with classroom collision prevention and instructor conflict guards.",
    },
    {
        "name": "Leave Management",
        "description": "Absence petitions, medical leaves, duty slips, and Dean review decision workflows.",
    },
    {
        "name": "Library Circulation",
        "description": "Campus library monograph catalog, ISBN inventory tracking, and scholar book loan checkouts.",
    },
    {
        "name": "Hostel & Housing",
        "description": "Residential hall blocks, room capacities, and student bed allocations.",
    },
    {
        "name": "Placements & Recruitment",
        "description": "Corporate recruitment drives, GPA eligibility gating, interview pipeline, and CTC telemetry.",
    },
    {
        "name": "Transport Fleet & Logistics",
        "description": "Multi-stop bus transit routes, vehicle fleet directory, and sequential transit passes.",
    },
    {
        "name": "Scholarships & Financial Aid",
        "description": "Institutional fellowships, government grants, and bursar review disbursement cycles.",
    },
    {
        "name": "Alumni Network & Mentorship",
        "description": "Graduate network directory, industry matchmaking, and career guidance sessions.",
    },
    {
        "name": "Campus Events & Symposiums",
        "description": "Institutional seminars, workshops, hackathons, symposiums, registrations, and certificate issuance.",
    },
    {
        "name": "Campus Assets & Lab Inventory",
        "description": "Scientific lab instruments, computing clusters, circulation checkouts, and maintenance work orders.",
    },
    {
        "name": "Campus Health & Infirmary",
        "description": "Electronic health profiles, clinical consultation encounters, dispensary medicine stock, and medical leave certificates.",
    },
    {
        "name": "Reports & Analytics",
        "description": "Institutional intelligence, low-attendance risk sentinel (<75%), and automated CSV export engine.",
    },
    {
        "name": "Departments",
        "description": "Academic departments directory and administrative department management.",
    },
    {
        "name": "Dashboard",
        "description": "Executive KPI telemetry, real-time metrics aggregation, and administrative summaries.",
    },
    {
        "name": "System",
        "description": "Health checks, database diagnostics, telemetry, and hot point-in-time online backups.",
    },
]


app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
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

# Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST API Routers
app.include_router(students_router)
app.include_router(courses_router)
app.include_router(faculty_router)
app.include_router(academics_router)
app.include_router(finance_router)
app.include_router(reports_router)
app.include_router(announcements_router)
app.include_router(leaves_router)
app.include_router(timetable_router)
app.include_router(library_router)
app.include_router(hostel_router)
app.include_router(placements_router)
app.include_router(transport_router)
app.include_router(scholarships_router)
app.include_router(alumni_router)
app.include_router(events_router)
app.include_router(inventory_router)
app.include_router(health_center_router)
app.include_router(departments_router)
app.include_router(dashboard_router)
app.include_router(system_router)

# Mount Web Page Routers
app.include_router(pages_router)

# Ensure directories exist and mount static assets
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
