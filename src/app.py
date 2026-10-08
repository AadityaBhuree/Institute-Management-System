"""Institute Management System - FastAPI Core Application.
Orchestrates static assets, Jinja2 template rendering, REST API routes, and database lifespan.
"""

import sqlite3
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.api.academics import router as academics_router
from src.api.courses import router as courses_router
from src.api.faculty import router as faculty_router
from src.api.finance import router as finance_router
from src.api.students import router as students_router
from src.core.config import (
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
    DB_PATH,
    STATIC_DIR,
    TEMPLATES_DIR,
)
from src.database.connection import get_db
from src.database.init_db import init_database
from src.services.academics_service import AcademicsService
from src.services.course_service import CourseService
from src.services.dashboard_service import DashboardService
from src.services.department_service import DepartmentService
from src.services.faculty_service import FacultyService
from src.services.finance_service import FinanceService
from src.services.student_service import StudentService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown routines."""
    # Ensure database tables and schema are initialized
    init_database()
    yield


app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
)

# Mount API Routers
app.include_router(students_router)
app.include_router(courses_router)
app.include_router(faculty_router)
app.include_router(academics_router)
app.include_router(finance_router)

# Ensure directories exist and mount static assets
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/api/health", tags=["System"])
def health_check(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    """System health check and database connectivity verification."""
    cursor = conn.cursor()
    cursor.execute("SELECT 1 AS ok;")
    result = cursor.fetchone()["ok"]
    cursor.close()
    return {
        "status": "healthy",
        "app": APP_NAME,
        "version": APP_VERSION,
        "database": "connected" if result == 1 else "unhealthy",
        "db_path": str(DB_PATH),
    }


@app.get("/api/departments", tags=["Departments"])
def list_departments(conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve all academic departments."""
    return DepartmentService.list_all(conn)


@app.get("/api/dashboard/stats", tags=["Dashboard"])
def get_dashboard_stats(conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve real-time KPI metrics and administrative summary."""
    return DashboardService.get_kpi_summary(conn)


# Frontend Web Routes
@app.get("/", response_class=HTMLResponse, tags=["Web"])
def view_dashboard(request: Request, conn: sqlite3.Connection = Depends(get_db)):
    """Render the executive overview dashboard."""
    summary = DashboardService.get_kpi_summary(conn)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "active_page": "dashboard",
            "summary": summary,
        },
    )


@app.get("/students", response_class=HTMLResponse, tags=["Web"])
def view_students_page(
    request: Request,
    department_id: Optional[int] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render the interactive student registry and admissions page."""
    students = StudentService.list_students(
        conn,
        department_id=department_id,
        status=status,
        search=search,
    )
    departments = DepartmentService.list_all(conn)
    return templates.TemplateResponse(
        request=request,
        name="students.html",
        context={
            "active_page": "students",
            "students": students,
            "departments": departments,
            "selected_dept": department_id,
            "selected_status": status,
            "search": search,
        },
    )


@app.get("/portal", response_class=HTMLResponse, tags=["Web"])
def view_student_portal_page(
    request: Request,
    student_id: Optional[int] = None,
    search: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render the student self-service academic portal and personal dossier."""
    all_students = StudentService.list_students(conn, limit=100)

    selected_id = student_id
    if not selected_id and search:
        matching = StudentService.list_students(conn, search=search, limit=1)
        if matching:
            selected_id = matching[0]["id"]

    if not selected_id and all_students:
        selected_id = all_students[0]["id"]

    dossier = None
    if selected_id:
        dossier = StudentService.get_student_portal_dossier(conn, selected_id)

    return templates.TemplateResponse(
        request=request,
        name="portal.html",
        context={
            "active_page": "portal",
            "dossier": dossier,
            "all_students": all_students,
            "selected_student_id": selected_id,
            "search": search or "",
        },
    )


@app.get("/faculty-portal", response_class=HTMLResponse, tags=["Web"])
def view_faculty_portal_page(
    request: Request,
    faculty_id: Optional[int] = None,
    search: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render the faculty instructor portal and teaching workbench."""
    all_faculty = FacultyService.list_faculty(conn)

    selected_id = faculty_id
    if not selected_id and search:
        matching = FacultyService.list_faculty(conn, search=search)
        if matching:
            selected_id = matching[0]["id"]

    if not selected_id and all_faculty:
        selected_id = all_faculty[0]["id"]

    dossier = None
    if selected_id:
        dossier = FacultyService.get_faculty_portal_data(conn, selected_id)

    return templates.TemplateResponse(
        request=request,
        name="faculty_portal.html",
        context={
            "active_page": "faculty_portal",
            "dossier": dossier,
            "all_faculty": all_faculty,
            "selected_faculty_id": selected_id,
            "search": search or "",
        },
    )



@app.get("/courses", response_class=HTMLResponse, tags=["Web"])
def view_courses_page(
    request: Request,
    department_id: Optional[int] = None,
    semester: Optional[int] = None,
    search: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render the course catalog and faculty roster management page."""
    courses = CourseService.list_courses(
        conn,
        department_id=department_id,
        semester=semester,
        search=search,
    )
    faculty_members = FacultyService.list_faculty(conn)
    departments = DepartmentService.list_all(conn)
    return templates.TemplateResponse(
        request=request,
        name="courses.html",
        context={
            "active_page": "courses",
            "courses": courses,
            "faculty_members": faculty_members,
            "departments": departments,
            "selected_dept": department_id,
            "selected_sem": semester,
            "search": search,
        },
    )


@app.get("/academics", response_class=HTMLResponse, tags=["Web"])
def view_academics_page(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render the daily attendance register and examination grading hub."""
    courses = CourseService.list_courses(conn)
    exams = AcademicsService.list_examinations(conn)
    return templates.TemplateResponse(
        request=request,
        name="academics.html",
        context={
            "active_page": "academics",
            "courses": courses,
            "exams": exams,
        },
    )


@app.get("/finance", response_class=HTMLResponse, tags=["Web"])
def view_finance_page(
    request: Request,
    status: Optional[str] = None,
    department_id: Optional[int] = None,
    search: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render the institutional bursar portal, fee invoicing, and audit ledger."""
    summary = FinanceService.get_financial_summary(conn)
    invoices = FinanceService.list_invoices(
        conn,
        status=status,
        department_id=department_id,
        search=search,
    )
    structures = FinanceService.list_fee_structures(conn)
    payments = FinanceService.list_payments(conn, limit=100)
    departments = DepartmentService.list_all(conn)
    students = StudentService.list_students(conn, limit=200)
    return templates.TemplateResponse(
        request=request,
        name="finance.html",
        context={
            "active_page": "finance",
            "summary": summary,
            "invoices": invoices,
            "structures": structures,
            "payments": payments,
            "departments": departments,
            "students": students,
            "selected_status": status,
            "selected_dept": department_id,
            "search": search,
        },
    )

