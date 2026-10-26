"""Tests for Phase 7 Enterprise Security Hardening.
Verifies security response headers, request body size limits, brute-force login throttling,
admin-only deletion enforcement, and template auto-escaping.
"""

import pytest

from src.core.config import MAX_REQUEST_SIZE_BYTES
from src.core.security_hardening import login_limiter
from src.web.pages import templates


@pytest.fixture(autouse=True)
def reset_limiter():
    """Ensure clean brute-force limiter state before and after each test."""
    login_limiter.reset()
    yield
    login_limiter.reset()


def test_security_headers_present(client):
    """Verify standard OWASP security response headers are injected on all endpoints."""
    res = client.get("/api/health")
    assert res.status_code == 200
    headers = res.headers

    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("x-xss-protection") == "1; mode=block"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "geolocation=()" in headers.get("permissions-policy", "")
    assert "default-src 'self'" in headers.get("content-security-policy", "")


def test_request_body_size_limit_rejection(client):
    """Verify request bodies exceeding size bounds are rejected with HTTP 413."""
    oversized_length = str(MAX_REQUEST_SIZE_BYTES + 1024)
    res = client.post(
        "/api/students",
        headers={"content-length": oversized_length, "content-type": "application/json"},
        content=b"{}",
    )
    assert res.status_code == 413
    data = res.json()
    assert "exceeds maximum allowed size" in data.get("detail", "")


def test_brute_force_login_lockout(anon_client):
    """Verify repeated failed login attempts trigger HTTP 429 lockout."""
    target_username = "victim_admin"

    # Attempt 5 consecutive failed logins
    for _ in range(5):
        res = anon_client.post(
            "/api/auth/login",
            json={"username": target_username, "password": "WrongPassword123!"},
        )
        assert res.status_code == 401

    # 6th attempt must be locked out with HTTP 429
    locked_res = anon_client.post(
        "/api/auth/login",
        json={"username": target_username, "password": "WrongPassword123!"},
    )
    assert locked_res.status_code == 429
    assert "Too many failed login attempts" in locked_res.json().get("detail", "")


def test_successful_login_resets_brute_force_tracking(anon_client):
    """Verify valid credentials reset failure count for the target user."""
    # Register 3 failed attempts
    for _ in range(3):
        anon_client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "BadPassword!"},
        )

    # Valid admin login succeeds and resets tracker
    login_res = anon_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_res.status_code == 200
    assert not login_limiter.is_locked("admin")


def test_unauthorized_delete_student_rejected(anon_client, student_client):
    """Verify DELETE /api/students/{id} rejects anonymous and student roles."""
    # Anonymous request -> 401
    res_anon = anon_client.delete("/api/students/1")
    assert res_anon.status_code == 401

    # Student role -> 403
    res_student = student_client.delete("/api/students/1")
    assert res_student.status_code == 403


def test_unauthorized_delete_faculty_rejected(anon_client, student_client):
    """Verify DELETE /api/faculty/{id} rejects anonymous and student roles."""
    res_anon = anon_client.delete("/api/faculty/1")
    assert res_anon.status_code == 401

    res_student = student_client.delete("/api/faculty/1")
    assert res_student.status_code == 403


def test_unauthorized_delete_course_rejected(anon_client, student_client):
    """Verify DELETE /api/courses/{id} rejects anonymous and student roles."""
    res_anon = anon_client.delete("/api/courses/1")
    assert res_anon.status_code == 401

    res_student = student_client.delete("/api/courses/1")
    assert res_student.status_code == 403


def test_unauthorized_delete_timetable_rejected(anon_client, student_client):
    """Verify DELETE /api/timetable/{id} rejects anonymous and student roles."""
    res_anon = anon_client.delete("/api/timetable/1")
    assert res_anon.status_code == 401

    res_student = student_client.delete("/api/timetable/1")
    assert res_student.status_code == 403


def test_unauthorized_delete_announcement_rejected(anon_client, student_client):
    """Verify DELETE /api/announcements/{id} rejects anonymous and student roles."""
    res_anon = anon_client.delete("/api/announcements/1")
    assert res_anon.status_code == 401

    res_student = student_client.delete("/api/announcements/1")
    assert res_student.status_code == 403


def test_admin_delete_generates_audit_log(client):
    """Verify admin deletion succeeds and writes an audit trail entry."""
    # Create temporary announcement to delete
    create_res = client.post(
        "/api/announcements",
        json={
            "title": "Temp Notice for Audit Test",
            "content": "This notice will be deleted by admin.",
            "category": "GENERAL",
            "target_audience": "ALL",
            "is_active": 1,
        },
    )
    assert create_res.status_code == 201
    notice_id = create_res.json()["id"]

    # Delete as admin
    del_res = client.delete(f"/api/announcements/{notice_id}")
    assert del_res.status_code == 200

    # Query audit logs
    audit_res = client.get("/api/auth/audit-logs?action=DELETE_ANNOUNCEMENT")
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert any(log.get("resource_id") == str(notice_id) for log in logs)


def test_jinja2_template_autoescaping_enabled():
    """Verify Jinja2 template auto-escaping is unconditionally enabled."""
    assert templates.env.autoescape is True
