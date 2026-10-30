"""Tests for Core Architecture, Database Initialization, and Dashboard Operations."""

from src.database.connection import get_connection
from src.database.init_db import init_database


def test_database_initialization():
    """Verify that all core tables and schemas are created."""
    init_database()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row["name"] for row in cursor.fetchall()}
    cursor.close()
    conn.close()

    expected_tables = {
        "departments",
        "faculty",
        "courses",
        "students",
        "course_enrollments",
        "attendance_records",
        "examinations",
        "exam_results",
        "fee_structures",
        "fee_invoices",
        "fee_payments",
    }
    assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"


def test_default_departments_seeded():
    """Verify default academic departments exist in database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT code, name FROM departments ORDER BY code ASC;")
    rows = cursor.fetchall()
    dept_codes = [r["code"] for r in rows]
    cursor.close()
    conn.close()

    assert "CSE" in dept_codes
    assert "ECE" in dept_codes
    assert "MECH" in dept_codes
    assert "BIOTECH" in dept_codes
    assert "MGMT" in dept_codes


def test_health_check_endpoint(client):
    """Verify system health endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "Institute Management System" in data["app"]
    assert "db_path" not in data


def test_cors_headers(client):
    """Verify CORS headers are returned for allowed origins."""
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:8000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:8000"


def test_departments_api(client):
    """Verify listing departments."""
    response = client.get("/api/departments")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    first = data[0]
    assert "code" in first
    assert "name" in first


def test_dashboard_stats_api(client):
    """Verify KPI aggregation endpoint."""
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_students" in data
    assert "total_faculty" in data
    assert "total_courses" in data
    assert "total_invoiced" in data
    assert "total_collected" in data
    assert "recovery_rate" in data
    assert "department_distribution" in data


def test_dashboard_html_view(client):
    """Verify overview HTML rendering."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert "Executive Overview" in html
    assert "IMS Enterprise" in html
    assert "Department Enrollment Distribution" in html


def test_reports_analytics_summary_api(client):
    """Verify institutional reports analytics REST API summary."""
    response = client.get("/api/reports/analytics-summary")
    assert response.status_code == 200
    data = response.json()

    assert "total_students" in data
    assert "overall_attendance_pct" in data
    assert "at_risk_students_count" in data
    assert "at_risk_scholars" in data
    assert "grade_distribution" in data
    assert "total_invoiced" in data
    assert "total_collected" in data
    assert "collection_rate_pct" in data
    assert "department_metrics" in data
    assert "exam_performance" in data
    assert len(data["department_metrics"]) >= 5


def test_reports_analytics_filtered_by_department(client):
    """Verify filtering reports analytics by department ID."""
    response = client.get("/api/reports/analytics-summary?department_id=1")
    assert response.status_code == 200
    data = response.json()
    assert "total_students" in data
    assert "overall_attendance_pct" in data


def test_view_reports_html_page(client):
    """Verify HTML rendering of institutional reports and analytics page."""
    response = client.get("/reports")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert "Reports & Analytics Hub" in html
    assert "Institutional Attendance Rate" in html
    assert "Attendance Risk Sentinel" in html
    assert "Department Matrix" in html


def test_create_department_api(client):
    """Verify creating a new department via REST API."""
    payload = {
        "code": "AIDS",
        "name": "Artificial Intelligence & Data Science",
        "description": "Next-gen machine learning and big data systems",
    }
    response = client.post("/api/departments", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == "AIDS"
    assert data["name"] == "Artificial Intelligence & Data Science"


def test_system_telemetry_api(client):
    """Verify system diagnostics and telemetry endpoint."""
    response = client.get("/api/system/telemetry")
    assert response.status_code == 200
    data = response.json()
    assert "app_name" in data
    assert "app_version" in data
    assert "db_size_kb" in data
    assert "integrity_status" in data
    assert "table_stats" in data
    assert "students" in data["table_stats"]


def test_system_database_backup_flow(client):
    """Verify hot online database backup generation and retrieval."""
    backup_res = client.post("/api/system/backup")
    assert backup_res.status_code == 200
    backup_data = backup_res.json()
    assert backup_data["status"] == "SUCCESS"
    assert backup_data["filename"].startswith("ims_backup_")
    assert backup_data["size_kb"] > 0

    list_res = client.get("/api/system/backups")
    assert list_res.status_code == 200
    snapshots = list_res.json()
    assert len(snapshots) >= 1
    assert any(s["filename"] == backup_data["filename"] for s in snapshots)


def test_view_settings_html_page(client):
    """Verify HTML rendering of system settings and backup page."""
    response = client.get("/settings")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert "System Settings & Diagnostics" in html
    assert "Database Backup Engine" in html
    assert "Academic Departments" in html
    assert "Relational Schema Telemetry" in html


def test_rate_limiter_configuration():
    """Verify that the slowapi rate limiter is properly mounted on FastAPI app."""
    from src.app import app

    assert hasattr(app.state, "limiter")
    assert app.state.limiter is not None


def test_rate_limiting_enforcement():
    """Verify rate limiting triggers HTTP 429 Too Many Requests when threshold is exceeded."""
    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.util import get_remote_address

    test_app = FastAPI()
    test_limiter = Limiter(key_func=get_remote_address, default_limits=["2/minute"], enabled=True)
    test_app.state.limiter = test_limiter
    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    test_app.add_middleware(SlowAPIMiddleware)

    @test_app.get("/test-limited")
    @test_limiter.limit("2/minute")
    def limited_endpoint(request: Request):
        return {"status": "ok"}

    with TestClient(test_app) as tc:
        r1 = tc.get("/test-limited")
        assert r1.status_code == 200
        r2 = tc.get("/test-limited")
        assert r2.status_code == 200
        r3 = tc.get("/test-limited")
        assert r3.status_code == 429


def test_system_database_restore_flow(client):
    """Verify taking a snapshot, creating new records, restoring snapshot, and validating rollback."""
    # 1. Take a backup snapshot
    backup_res = client.post("/api/system/backup")
    assert backup_res.status_code == 200
    snapshot_filename = backup_res.json()["filename"]

    # 2. Add a new department
    new_dept_payload = {
        "code": "RESTORE",
        "name": "Temporary Department For Restore Verification",
        "description": "Will be wiped out by restore operation",
    }
    create_res = client.post("/api/departments", json=new_dept_payload)
    assert create_res.status_code == 201

    # Verify department exists
    dept_check = client.get("/api/departments")
    assert any(d["code"] == "RESTORE" for d in dept_check.json())

    # 3. Restore snapshot
    restore_res = client.post("/api/system/restore", json={"filename": snapshot_filename})
    assert restore_res.status_code == 200
    restore_data = restore_res.json()
    assert restore_data["status"] == "RESTORED"
    assert restore_data["filename"] == snapshot_filename

    # 4. Verify department is gone (state reverted to pre-snapshot state)
    dept_after = client.get("/api/departments")
    assert not any(d["code"] == "RESTORE" for d in dept_after.json())


def test_system_database_restore_validation(client):
    """Verify input validation and error handling on restore endpoint."""
    # Missing filename
    res_empty = client.post("/api/system/restore", json={})
    assert res_empty.status_code == 400

    # Path traversal attack attempt
    res_traversal = client.post("/api/system/restore", json={"filename": "../../../etc/passwd"})
    assert res_traversal.status_code == 400

    # Non-existent backup file
    res_404 = client.post(
        "/api/system/restore", json={"filename": "ims_backup_nonexistent_9999.db"}
    )
    assert res_404.status_code == 404
