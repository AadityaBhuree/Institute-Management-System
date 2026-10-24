"""Tests for Authentication, RBAC Authorization, and Institutional Audit Trail APIs."""

import time

from src.core.security import (
    SESSION_COOKIE_NAME,
    create_session_token,
    hash_password,
    verify_password,
    verify_session_token,
)


def test_password_hashing_and_verification():
    """Verify PBKDF2-HMAC-SHA256 password hashing and timing-safe verification."""
    password = "SuperSecretPassword2026!"
    hashed = hash_password(password)

    assert hashed.startswith("pbkdf2_sha256$100000$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword123", hashed) is False
    assert verify_password(password, "invalid_hash_string") is False
    assert verify_password(password, "pbkdf2_sha256$100000$bad$hash") is False


def test_session_token_lifecycle():
    """Verify session token signing, tampering rejection, and expiration handling."""
    token = create_session_token(
        user_id=42, username="testscholar", role="student", expires_in_seconds=3600
    )
    payload = verify_session_token(token)

    assert payload is not None
    assert payload["uid"] == 42
    assert payload["sub"] == "testscholar"
    assert payload["role"] == "student"

    # Test tampering with payload
    payload_b64, sig = token.split(".")
    tampered_token = f"eyJ1aWQiOjk5OSwic3ViIjoidGFtcGVyZWQifQ.{sig}"
    assert verify_session_token(tampered_token) is None

    # Test tampering with signature
    bad_sig_token = f"{payload_b64}.0123456789abcdef"
    assert verify_session_token(bad_sig_token) is None

    # Test expired token
    expired_token = create_session_token(
        user_id=42, username="expired", role="student", expires_in_seconds=-10
    )
    assert verify_session_token(expired_token) is None


def test_api_login_success(anon_client):
    """Verify successful authentication returns token, user info, and sets HTTP-only cookie."""
    payload = {"username": "admin", "password": "admin123"}
    res = anon_client.post("/api/auth/login", json=payload)

    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "admin"
    assert SESSION_COOKIE_NAME in res.cookies


def test_api_login_invalid_password(anon_client):
    """Verify login failure with incorrect password returns 401."""
    payload = {"username": "admin", "password": "wrong_password"}
    res = anon_client.post("/api/auth/login", json=payload)

    assert res.status_code == 401
    assert "Invalid username or password" in res.json()["detail"]


def test_api_login_nonexistent_user(anon_client):
    """Verify login failure for non-existent user returns 401."""
    payload = {"username": "ghost_user", "password": "password123"}
    res = anon_client.post("/api/auth/login", json=payload)

    assert res.status_code == 401
    assert "Invalid username or password" in res.json()["detail"]


def test_api_get_current_user_profile(client, anon_client):
    """Verify /api/auth/me returns profile for authenticated user and 401 for anonymous."""
    # Authenticated request (admin)
    res_auth = client.get("/api/auth/me")
    assert res_auth.status_code == 200
    data = res_auth.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"

    # Anonymous request
    res_anon = anon_client.get("/api/auth/me")
    assert res_anon.status_code == 401


def test_api_bearer_token_authentication(anon_client):
    """Verify authentication via Authorization: Bearer header."""
    token = create_session_token(user_id=1, username="admin", role="admin")
    headers = {"Authorization": f"Bearer {token}"}
    res = anon_client.get("/api/auth/me", headers=headers)

    assert res.status_code == 200
    assert res.json()["username"] == "admin"


def test_api_logout(client):
    """Verify logout terminates session and clears cookie."""
    res = client.post("/api/auth/logout")
    assert res.status_code == 200
    assert "Session successfully terminated" in res.json()["message"]


def test_api_register_user_by_admin(client, student_client):
    """Verify that only admin can register new accounts."""
    unique_user = f"registrar_{int(time.time())}"
    payload = {
        "username": unique_user,
        "email": f"{unique_user}@institute.edu",
        "password": "SecurePassword123!",
        "role": "faculty",
    }

    # Admin registers user -> 201 Created
    res_admin = client.post("/api/auth/register", json=payload)
    assert res_admin.status_code == 201
    created = res_admin.json()
    assert created["username"] == unique_user
    assert created["role"] == "faculty"

    # Student attempts to register user -> 403 Forbidden
    res_student = student_client.post("/api/auth/register", json=payload)
    assert res_student.status_code == 403


def test_api_register_duplicate_rejection(client):
    """Verify duplicate username or email is rejected with 400 Bad Request."""
    payload = {
        "username": "admin",
        "email": "another_admin@institute.edu",
        "password": "Password123!",
        "role": "admin",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
    assert "already registered" in res.json()["detail"]


def test_rbac_backup_endpoint_protection(anon_client, student_client, client):
    """Verify /api/system/backup is protected: 401 for anon, 403 for student, 200 for admin."""
    # Anonymous -> 401
    res_anon = anon_client.post("/api/system/backup")
    assert res_anon.status_code == 401

    # Student role -> 403
    res_student = student_client.post("/api/system/backup")
    assert res_student.status_code == 403

    # Admin role -> 200
    res_admin = client.post("/api/system/backup")
    assert res_admin.status_code == 200
    assert res_admin.json()["status"] == "SUCCESS"


def test_audit_logs_recording_and_rbac(client, student_client):
    """Verify audit logs are recorded on operations and restricted to admin."""
    # Admin accesses audit logs -> 200
    res_admin = client.get("/api/auth/audit-logs")
    assert res_admin.status_code == 200
    logs = res_admin.json()
    assert isinstance(logs, list)
    assert len(logs) >= 1
    assert any("SYSTEM" in log["action"] or "USER" in log["action"] for log in logs)

    # Student attempts to access audit logs -> 403
    res_student = student_client.get("/api/auth/audit-logs")
    assert res_student.status_code == 403


def test_view_login_html_page(anon_client):
    """Verify login HTML page rendering."""
    res = anon_client.get("/login")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    html = res.text
    assert "IMS Enterprise" in html
    assert "Sign In to Portal" in html
    assert "Quick Demo Accounts" in html


def test_html_form_login_success(anon_client):
    """Verify HTML form POST login sets cookie and redirects to dashboard."""
    form_data = {
        "username": "admin",
        "password": "admin123",
        "next": "/",
    }
    res = anon_client.post("/login", data=form_data, follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == "/"
    assert SESSION_COOKIE_NAME in res.cookies


def test_html_form_login_failure(anon_client):
    """Verify HTML form POST with invalid credentials displays error with 401 status."""
    form_data = {
        "username": "admin",
        "password": "wrong_password",
    }
    res = anon_client.post("/login", data=form_data)
    assert res.status_code == 401
    assert "Invalid username or password" in res.text


def test_html_logout_flow(client):
    """Verify GET /logout clears cookie and redirects to /login."""
    res = client.get("/logout", follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == "/login"
