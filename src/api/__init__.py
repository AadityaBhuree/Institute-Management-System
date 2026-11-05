"""API routers package."""

from src.api.academics import router as academics_router
from src.api.alumni import router as alumni_router
from src.api.announcements import router as announcements_router
from src.api.auth import router as auth_router
from src.api.courses import router as courses_router
from src.api.dashboard import router as dashboard_router
from src.api.departments import router as departments_router
from src.api.email import router as email_router
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
from src.api.storage import router as storage_router
from src.api.students import router as students_router
from src.api.system import router as system_router
from src.api.timetable import router as timetable_router
from src.api.transport import router as transport_router

ALL_API_ROUTERS = [
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
    storage_router,
    email_router,
    system_router,
]

__all__ = [
    "ALL_API_ROUTERS",
    "academics_router",
    "alumni_router",
    "announcements_router",
    "auth_router",
    "courses_router",
    "dashboard_router",
    "departments_router",
    "email_router",
    "events_router",
    "faculty_router",
    "finance_router",
    "health_center_router",
    "hostel_router",
    "inventory_router",
    "leaves_router",
    "library_router",
    "notifications_router",
    "placements_router",
    "reports_router",
    "scholarships_router",
    "storage_router",
    "students_router",
    "system_router",
    "timetable_router",
    "transport_router",
]
