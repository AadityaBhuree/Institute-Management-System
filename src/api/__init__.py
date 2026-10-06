"""API routers package."""

from src.api.academics import router as academics_router
from src.api.courses import router as courses_router
from src.api.faculty import router as faculty_router
from src.api.finance import router as finance_router
from src.api.students import router as students_router

__all__ = [
    "students_router",
    "courses_router",
    "faculty_router",
    "academics_router",
    "finance_router",
]
