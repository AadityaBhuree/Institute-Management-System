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
