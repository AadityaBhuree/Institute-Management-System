"""Institute Management System - FastAPI Core Application.
Orchestrates static assets, Jinja2 template rendering, REST API routes, and database lifespan.
"""

import sqlite3
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.api.academics import router as academics_router
from src.api.announcements import router as announcements_router
from src.api.courses import router as courses_router
from src.api.faculty import router as faculty_router
from src.api.finance import router as finance_router
from src.api.leaves import router as leaves_router
from src.api.reports import router as reports_router
from src.api.students import router as students_router
from src.api.timetable import router as timetable_router
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
from src.models.department import DepartmentCreate
from src.services.academics_service import AcademicsService
from src.services.announcement_service import AnnouncementService
from src.services.course_service import CourseService
from src.services.dashboard_service import DashboardService
from src.services.department_service import DepartmentService
from src.services.faculty_service import FacultyService
from src.services.finance_service import FinanceService
from src.services.leave_service import LeaveService
from src.services.reports_service import ReportsService
from src.services.student_service import StudentService
from src.services.system_service import SystemService
from src.services.timetable_service import TimetableService



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
app.include_router(reports_router)
app.include_router(announcements_router)
app.include_router(leaves_router)
app.include_router(timetable_router)


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


@app.post("/api/departments", status_code=status.HTTP_201_CREATED, tags=["Departments"])
def create_department(dept_in: DepartmentCreate, conn: sqlite3.Connection = Depends(get_db)):
    """Create a new academic department."""
    try:
        return DepartmentService.create(conn, dept_in)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@app.get("/api/system/telemetry", tags=["System"])
def get_system_telemetry(conn: sqlite3.Connection = Depends(get_db)):
    """Retrieve system diagnostics, database size, and table telemetry."""
    return SystemService.get_system_telemetry(conn)


@app.post("/api/system/backup", tags=["System"])
def create_system_backup(conn: sqlite3.Connection = Depends(get_db)):
    """Perform hot online SQLite database backup snapshot."""
    return SystemService.create_backup(conn)


@app.get("/api/system/backups", tags=["System"])
def list_system_backups():
    """List all available database snapshots in data/backups/."""
    return SystemService.list_backups()



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


@app.get("/reports", response_class=HTMLResponse, tags=["Web"])
def view_reports_page(
    request: Request,
    department_id: Optional[int] = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render institutional analytics, attendance risk sentinel, and financial recovery hub."""
    summary = ReportsService.get_analytics_summary(conn, department_id=department_id)
    departments = DepartmentService.list_all(conn)
    return templates.TemplateResponse(
        request=request,
        name="reports.html",
        context={
            "active_page": "reports",
            "summary": summary,
            "departments": departments,
            "selected_dept": department_id,
        },
    )


@app.get("/settings", response_class=HTMLResponse, tags=["Web"])
def view_settings_page(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render administrative settings, department configuration, and database backup engine."""
    telemetry = SystemService.get_system_telemetry(conn)
    departments = DepartmentService.list_all(conn)
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "active_page": "settings",
            "telemetry": telemetry,
            "departments": departments,
        },
    )


@app.get("/announcements", response_class=HTMLResponse, tags=["Web"])
def view_announcements_page(
    request: Request,
    category: Optional[str] = None,
    audience: Optional[str] = None,
    search: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render the campus notice board and announcements hub."""
    bulletins = AnnouncementService.list_announcements(
        conn,
        category=category,
        target_audience=audience,
        search=search,
    )
    return templates.TemplateResponse(
        request=request,
        name="announcements.html",
        context={
            "active_page": "announcements",
            "announcements": bulletins,
            "selected_category": category,
            "selected_audience": audience,
            "search": search or "",
        },
    )


@app.get("/leaves", response_class=HTMLResponse, tags=["Web"])
def view_leaves_page(
    request: Request,
    status: Optional[str] = None,
    applicant_type: Optional[str] = None,
    search: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render the institutional leave application and approval workflow portal."""
    leaves = LeaveService.list_leaves(
        conn,
        status=status,
        applicant_type=applicant_type,
        search=search,
    )
    stats = LeaveService.get_leave_stats(conn)
    students = StudentService.list_students(conn, limit=100)
    faculty = FacultyService.list_faculty(conn)
    return templates.TemplateResponse(
        request=request,
        name="leaves.html",
        context={
            "active_page": "leaves",
            "leaves": leaves,
            "stats": stats,
            "students": students,
            "faculty": faculty,
            "selected_status": status,
            "selected_type": applicant_type,
            "search": search or "",
        },
    )


@app.get("/timetable", response_class=HTMLResponse, tags=["Web"])
def view_timetable_page(
    request: Request,
    department_id: Optional[int] = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render the academic lecture timetable and weekly schedule matrix."""
    matrix = TimetableService.get_weekly_matrix(conn, department_id=department_id)
    departments = DepartmentService.list_all(conn)
    courses = CourseService.list_courses(conn, department_id=department_id)
    return templates.TemplateResponse(
        request=request,
        name="timetable.html",
        context={
            "active_page": "timetable",
            "matrix": matrix,
            "departments": departments,
            "courses": courses,
            "selected_dept": department_id,
        },
    )



