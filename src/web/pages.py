"""Institute Management System - Web Page Route Handlers.
Renders all Jinja2 templates and user interfaces for institutional administration.
"""

import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.core.config import TEMPLATES_DIR
from src.core.security import (
    DEFAULT_SESSION_MAX_AGE,
    SESSION_COOKIE_NAME,
    create_session_token,
    get_current_user_optional,
)
from src.database.connection import get_db
from src.services.academics_service import AcademicsService
from src.services.alumni_service import AlumniService
from src.services.announcement_service import AnnouncementService
from src.services.asset_service import AssetService
from src.services.auth_service import AuthService
from src.services.course_service import CourseService
from src.services.dashboard_service import DashboardService
from src.services.department_service import DepartmentService
from src.services.event_service import EventService
from src.services.faculty_service import FacultyService
from src.services.finance_service import FinanceService
from src.services.health_service import HealthService
from src.services.hostel_service import HostelService
from src.services.leave_service import LeaveService
from src.services.library_service import LibraryService
from src.services.placement_service import PlacementService
from src.services.reports_service import ReportsService
from src.services.scholarship_service import ScholarshipService
from src.services.student_service import StudentService
from src.services.system_service import SystemService
from src.services.timetable_service import TimetableService
from src.services.transport_service import TransportService

router = APIRouter(tags=["Web"])

TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.autoescape = True


@router.get("/login", response_class=HTMLResponse)
def view_login_page(
    request: Request,
    next: Optional[str] = None,
    error: Optional[str] = None,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """Render the user authentication and login interface."""
    if current_user:
        return RedirectResponse(url=next or "/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "active_page": "login",
            "next": next or "/",
            "error": error,
            "current_user": current_user,
        },
    )


@router.post("/login", response_class=HTMLResponse)
async def handle_login_form(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Handle traditional HTML form submission for login."""
    body_bytes = await request.body()
    import urllib.parse

    form_dict = urllib.parse.parse_qs(body_bytes.decode("utf-8", errors="replace"))
    username = form_dict.get("username", [""])[0].strip()
    password = form_dict.get("password", [""])[0].strip()
    next_url = form_dict.get("next", ["/"])[0].strip() or "/"

    user = AuthService.authenticate(conn, username, password)
    ip_addr = request.client.host if request.client else None

    if not user:
        AuthService.log_audit(
            conn,
            action="LOGIN_FAILED",
            resource="web_auth",
            details=f"Failed web login attempt for '{username}'.",
            ip_address=ip_addr,
        )
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "active_page": "login",
                "next": next_url,
                "error": "Invalid username or password.",
                "username": username,
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    AuthService.update_last_login(conn, user["id"])
    token = create_session_token(
        user_id=user["id"],
        username=user["username"],
        role=user["role"],
    )
    AuthService.log_audit(
        conn,
        action="LOGIN_SUCCESS",
        resource="web_auth",
        resource_id=str(user["id"]),
        user_id=user["id"],
        username=user["username"],
        details=f"User '{user['username']}' logged in via web portal.",
        ip_address=ip_addr,
    )

    response = RedirectResponse(url=next_url, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=DEFAULT_SESSION_MAX_AGE,
        path="/",
    )
    return response


@router.get("/logout")
def handle_logout_page(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """Clear session cookie and redirect to login page."""
    if current_user:
        AuthService.log_audit(
            conn,
            action="LOGOUT",
            resource="web_auth",
            resource_id=str(current_user["id"]),
            user_id=current_user["id"],
            username=current_user["username"],
            details=f"User '{current_user['username']}' logged out via web portal.",
        )
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return response


@router.get("/", response_class=HTMLResponse)
def view_dashboard(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """Render the executive overview dashboard."""
    summary = DashboardService.get_kpi_summary(conn)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "active_page": "dashboard",
            "summary": summary,
            "current_user": current_user,
        },
    )


@router.get("/students", response_class=HTMLResponse)
def view_students_page(
    request: Request,
    department_id: Optional[int] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render the interactive student registry and admissions page with server-side pagination."""
    import math

    page = max(1, page)
    page_size = max(5, min(100, page_size))
    total_count = StudentService.count_students(
        conn,
        department_id=department_id,
        status=status,
        search=search,
    )
    total_pages = max(1, math.ceil(total_count / page_size))
    if page > total_pages:
        page = total_pages
    offset = (page - 1) * page_size

    students = StudentService.list_students(
        conn,
        department_id=department_id,
        status=status,
        search=search,
        limit=page_size,
        offset=offset,
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
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_prev": page > 1,
                "has_next": page < total_pages,
                "prev_page": page - 1,
                "next_page": page + 1,
            },
        },
    )


@router.get("/portal", response_class=HTMLResponse)
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


@router.get("/faculty-portal", response_class=HTMLResponse)
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


@router.get("/courses", response_class=HTMLResponse)
def view_courses_page(
    request: Request,
    department_id: Optional[int] = None,
    semester: Optional[int] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render the course catalog and faculty roster management page with pagination."""
    import math

    page = max(1, page)
    page_size = max(5, min(100, page_size))
    total_count = CourseService.count_courses(
        conn,
        department_id=department_id,
        semester=semester,
        search=search,
    )
    total_pages = max(1, math.ceil(total_count / page_size))
    if page > total_pages:
        page = total_pages
    offset = (page - 1) * page_size

    courses = CourseService.list_courses(
        conn,
        department_id=department_id,
        semester=semester,
        search=search,
        limit=page_size,
        offset=offset,
    )
    faculty_members = FacultyService.list_faculty(conn, limit=100)
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
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_prev": page > 1,
                "has_next": page < total_pages,
                "prev_page": page - 1,
                "next_page": page + 1,
            },
        },
    )


@router.get("/academics", response_class=HTMLResponse)
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


@router.get("/finance", response_class=HTMLResponse)
def view_finance_page(
    request: Request,
    status: Optional[str] = None,
    department_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render the institutional bursar portal, fee invoicing, and audit ledger with pagination."""
    import math

    page = max(1, page)
    page_size = max(5, min(100, page_size))
    total_count = FinanceService.count_invoices(
        conn,
        status=status,
        department_id=department_id,
        search=search,
    )
    total_pages = max(1, math.ceil(total_count / page_size))
    if page > total_pages:
        page = total_pages
    offset = (page - 1) * page_size

    summary = FinanceService.get_financial_summary(conn)
    invoices = FinanceService.list_invoices(
        conn,
        status=status,
        department_id=department_id,
        search=search,
        limit=page_size,
        offset=offset,
    )
    structures = FinanceService.list_fee_structures(conn)
    payments = FinanceService.list_payments(conn, limit=50)
    departments = DepartmentService.list_all(conn)
    students = StudentService.list_students(conn, limit=100)
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
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_prev": page > 1,
                "has_next": page < total_pages,
                "prev_page": page - 1,
                "next_page": page + 1,
            },
        },
    )


@router.get("/reports", response_class=HTMLResponse)
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


@router.get("/settings", response_class=HTMLResponse)
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


@router.get("/announcements", response_class=HTMLResponse)
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


@router.get("/leaves", response_class=HTMLResponse)
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


@router.get("/timetable", response_class=HTMLResponse)
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


@router.get("/finance/invoices/{id}/print", response_class=HTMLResponse)
def view_print_receipt_page(
    id: int,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render official printable fee receipt and settlement statement."""
    invoice = FinanceService.get_invoice_by_id(conn, id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Invoice #{id} not found"
        )
    payments = FinanceService.list_payments(conn, invoice_id=id)
    return templates.TemplateResponse(
        request=request,
        name="print_receipt.html",
        context={
            "invoice": invoice,
            "payments": payments,
        },
    )


@router.get("/portal/transcript/{student_id}/print", response_class=HTMLResponse)
def view_print_transcript_page(
    student_id: int,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render official printable academic transcript dossier."""
    dossier = StudentService.get_student_portal_dossier(conn, student_id)
    if not dossier or not dossier.get("student"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Student #{student_id} not found"
        )
    return templates.TemplateResponse(
        request=request,
        name="print_transcript.html",
        context={
            "dossier": dossier,
        },
    )


@router.get("/library", response_class=HTMLResponse)
def view_library_page(
    request: Request,
    category: Optional[str] = None,
    search: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render the campus library monograph catalog and circulation desk."""
    books = LibraryService.list_books(conn, category=category, search=search)
    loans = LibraryService.list_loans(conn)
    stats = LibraryService.get_stats(conn)
    students = StudentService.list_students(conn)
    return templates.TemplateResponse(
        request=request,
        name="library.html",
        context={
            "active_page": "library",
            "books": books,
            "loans": loans,
            "stats": stats,
            "students": students,
            "selected_category": category,
            "search": search or "",
        },
    )


@router.get("/hostel", response_class=HTMLResponse)
def view_hostel_page(
    request: Request,
    block_id: Optional[int] = None,
    room_type: Optional[str] = None,
    status: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render residential blocks, rooms occupancy, and scholar bed allocations."""
    blocks = HostelService.list_blocks(conn)
    rooms = HostelService.list_rooms(conn, block_id=block_id, room_type=room_type, status=status)
    allocations = HostelService.list_allocations(conn, block_id=block_id)
    stats = HostelService.get_stats(conn)
    students = StudentService.list_students(conn)
    return templates.TemplateResponse(
        request=request,
        name="hostel.html",
        context={
            "active_page": "hostel",
            "blocks": blocks,
            "rooms": rooms,
            "allocations": allocations,
            "stats": stats,
            "students": students,
            "selected_block": block_id,
            "selected_type": room_type,
            "selected_status": status,
        },
    )


@router.get("/placements", response_class=HTMLResponse)
def view_placements_page(
    request: Request,
    status: Optional[str] = None,
    search: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render campus recruitment drives, applications pipeline, and placement telemetry."""
    drives = PlacementService.list_drives(conn, status=status, search=search)
    applications = PlacementService.list_applications(conn)
    stats = PlacementService.get_stats(conn)
    students = StudentService.list_students(conn)
    return templates.TemplateResponse(
        request=request,
        name="placements.html",
        context={
            "active_page": "placements",
            "drives": drives,
            "applications": applications,
            "stats": stats,
            "students": students,
            "selected_status": status,
            "search": search or "",
        },
    )


@router.get("/transport", response_class=HTMLResponse)
def view_transport_page(
    request: Request,
    route_id: Optional[int] = None,
    status: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render campus transport fleet, routes, and transit passes portal."""
    routes = TransportService.list_routes(conn)
    vehicles = TransportService.list_vehicles(conn, route_id=route_id, status=status)
    passes = TransportService.list_passes(conn)
    stats = TransportService.get_stats(conn)
    students = StudentService.list_students(conn)
    return templates.TemplateResponse(
        request=request,
        name="transport.html",
        context={
            "active_page": "transport",
            "routes": routes,
            "vehicles": vehicles,
            "passes": passes,
            "stats": stats,
            "students": students,
            "selected_route": route_id,
            "selected_status": status,
        },
    )


@router.get("/scholarships", response_class=HTMLResponse)
def view_scholarships_page(
    request: Request,
    status: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render scholarships, grants, and financial aid management hub."""
    schemes = ScholarshipService.list_schemes(conn, status=status)
    applications = ScholarshipService.list_applications(conn)
    stats = ScholarshipService.get_stats(conn)
    students = StudentService.list_students(conn)
    return templates.TemplateResponse(
        request=request,
        name="scholarships.html",
        context={
            "active_page": "scholarships",
            "schemes": schemes,
            "applications": applications,
            "stats": stats,
            "students": students,
            "selected_status": status,
        },
    )


@router.get("/alumni", response_class=HTMLResponse)
def view_alumni_page(
    request: Request,
    department_id: Optional[int] = None,
    graduation_year: Optional[int] = None,
    mentorship_status: Optional[str] = None,
    search: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render alumni network directory and student career mentorship hub."""
    alumni_list = AlumniService.list_alumni(
        conn,
        department_id=department_id,
        graduation_year=graduation_year,
        mentorship_status=mentorship_status,
        search=search,
    )
    requests = AlumniService.list_mentorship_requests(conn)
    stats = AlumniService.get_stats(conn)
    departments = DepartmentService.list_all(conn)
    students = StudentService.list_students(conn)
    return templates.TemplateResponse(
        request=request,
        name="alumni.html",
        context={
            "active_page": "alumni",
            "alumni": alumni_list,
            "requests": requests,
            "stats": stats,
            "departments": departments,
            "students": students,
            "selected_dept": department_id,
            "selected_year": graduation_year,
            "selected_status": mentorship_status,
            "search": search or "",
        },
    )


@router.get("/events", response_class=HTMLResponse)
def view_events_page(
    request: Request,
    category: Optional[str] = None,
    status: Optional[str] = None,
    department_id: Optional[int] = None,
    search: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render campus events, conferences, seminars, and symposiums hub."""
    events = EventService.list_events(
        conn,
        category=category,
        status=status,
        department_id=department_id,
        search=search,
    )
    registrations = EventService.list_registrations(conn, limit=100)
    stats = EventService.get_stats(conn)
    departments = DepartmentService.list_all(conn)
    faculty_list = FacultyService.list_faculty(conn)
    students = StudentService.list_students(conn)
    return templates.TemplateResponse(
        request=request,
        name="events.html",
        context={
            "active_page": "events",
            "events": events,
            "registrations": registrations,
            "stats": stats,
            "departments": departments,
            "faculty": faculty_list,
            "students": students,
            "selected_category": category,
            "selected_status": status,
            "selected_dept": department_id,
            "search": search or "",
        },
    )


@router.get("/inventory", response_class=HTMLResponse)
def view_inventory_page(
    request: Request,
    category: Optional[str] = None,
    status: Optional[str] = None,
    department_id: Optional[int] = None,
    lab_room: Optional[str] = None,
    search: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render campus equipment, laboratory instruments, and circulation inventory hub."""
    assets = AssetService.list_assets(
        conn,
        category=category,
        status=status,
        department_id=department_id,
        lab_room=lab_room,
        search=search,
    )
    checkouts = AssetService.list_checkouts(conn, limit=100)
    maintenance = AssetService.list_maintenance(conn, limit=100)
    stats = AssetService.get_stats(conn)
    departments = DepartmentService.list_all(conn)
    faculty_list = FacultyService.list_faculty(conn)
    students = StudentService.list_students(conn)
    return templates.TemplateResponse(
        request=request,
        name="inventory.html",
        context={
            "active_page": "inventory",
            "assets": assets,
            "checkouts": checkouts,
            "maintenance": maintenance,
            "stats": stats,
            "departments": departments,
            "faculty": faculty_list,
            "students": students,
            "selected_category": category,
            "selected_status": status,
            "selected_dept": department_id,
            "search": search or "",
        },
    )


@router.get("/health-center", response_class=HTMLResponse)
def view_health_center_page(
    request: Request,
    tab: str = "encounters",
    triage: Optional[str] = None,
    patient_type: Optional[str] = None,
    search: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Render campus health center, clinical consultations, and infirmary dispensary hub."""
    encounters = HealthService.list_encounters(
        conn,
        patient_type=patient_type,
        triage_severity=triage,
        search=search,
        limit=100,
    )
    profiles = HealthService.list_profiles(conn, search=search)
    medicines = HealthService.list_dispensary_medicines(conn, search=search)
    certificates = HealthService.list_medical_certificates(conn, search=search)
    stats = HealthService.get_health_stats(conn)
    students = StudentService.list_students(conn)
    faculty_list = FacultyService.list_faculty(conn)
    return templates.TemplateResponse(
        request=request,
        name="health_center.html",
        context={
            "active_page": "health_center",
            "tab": tab,
            "encounters": encounters,
            "profiles": profiles,
            "medicines": medicines,
            "certificates": certificates,
            "stats": stats,
            "students": students,
            "faculty": faculty_list,
            "selected_triage": triage,
            "selected_type": patient_type,
            "search": search or "",
        },
    )
