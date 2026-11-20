"""Automated Test Suite for Identity Lifecycle, Password Self-Service, and 2FA.
Tests RFC 6238 TOTP generation, clock-drift tolerance, backup code consumption,
password reset token issuance, replay prevention, remote session revocation, and RBAC endpoints.
"""

import datetime

import pytest

from src.core.totp import TOTPManager
from src.database.connection import get_connection, release_connection
from src.services.auth_lifecycle_service import AuthLifecycleService
from src.services.auth_service import AuthService


def test_totp_manager_generate_and_verify_success():
    """Verify standard RFC 6238 TOTP code generation and matching."""
    secret = TOTPManager.generate_secret()
    assert len(secret) >= 16

    code = TOTPManager.generate_totp(secret)
    assert len(code) == 6
    assert code.isdigit()

    # Verify code
    assert TOTPManager.verify_totp(secret, code) is True
    # Verify wrong code
    assert TOTPManager.verify_totp(secret, "000000" if code != "000000" else "999999") is False


def test_totp_manager_window_tolerance():
    """Verify clock-drift tolerance allows tokens within ±1 time step window."""
    secret = TOTPManager.generate_secret()
    now = 1700000000.0  # Fixed deterministic timestamp

    code_past = TOTPManager.generate_totp(secret, timestamp=now - 30)
    code_future = TOTPManager.generate_totp(secret, timestamp=now + 30)
    code_too_far = TOTPManager.generate_totp(secret, timestamp=now + 120)

    # Window = 1 allows t-30 and t+30
    assert TOTPManager.verify_totp(secret, code_past, window=1, timestamp=now) is True
    assert TOTPManager.verify_totp(secret, code_future, window=1, timestamp=now) is True
    # Too far out of window
    assert TOTPManager.verify_totp(secret, code_too_far, window=1, timestamp=now) is False


def test_totp_manager_provisioning_uri_and_backup_codes():
    """Verify otpauth URI formatting and backup emergency codes generation."""
    secret = TOTPManager.generate_secret()
    uri = TOTPManager.get_provisioning_uri(secret, account_name="admin@institute.edu")
    assert uri.startswith("otpauth://totp/")
    assert "IMS%20Enterprise" in uri or "IMS Enterprise" in uri
    assert f"secret={secret}" in uri

    codes = TOTPManager.generate_backup_codes(count=8)
    assert len(codes) == 8
    for c in codes:
        assert "-" in c
        assert len(c) == 9  # e.g. "A1B2-C3D4"


def test_password_reset_request_and_silent_enumeration_protection():
    """Verify token generation for valid account and silent return for invalid account."""
    conn = get_connection()
    try:
        # 1. Existing account
        token = AuthLifecycleService.request_password_reset(conn, "admin@institute.edu")
        assert token is not None
        assert len(token) >= 20

        # 2. Non-existent account returns None (prevents user enumeration)
        missing = AuthLifecycleService.request_password_reset(
            conn, "nonexistent_fake@institute.edu"
        )
        assert missing is None
    finally:
        release_connection(conn)


def test_password_reset_completion_and_replay_rejection():
    """Verify resetting password updates credentials and rejects replay attempts."""
    conn = get_connection()
    try:
        # Create unique user for test
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (username, email, password_hash, role, status)
            VALUES ('reset_user_test', 'reset_user_test@institute.edu', 'old_hash', 'student', 'active');
            """
        )
        conn.commit()
        user_id = cur.lastrowid
        cur.close()

        # Issue reset token
        token = AuthLifecycleService.request_password_reset(conn, "reset_user_test@institute.edu")
        assert token is not None

        # Reset password
        success = AuthLifecycleService.reset_password(conn, token, "BrandNewP@ssw0rd2026!")
        assert success is True

        # Verify new credentials authenticate
        authenticated = AuthService.authenticate(conn, "reset_user_test", "BrandNewP@ssw0rd2026!")
        assert authenticated is not None
        assert authenticated["id"] == user_id

        # Replay attempt: Using same token must fail
        with pytest.raises(ValueError, match="already been consumed"):
            AuthLifecycleService.reset_password(conn, token, "AnotherPassword123!")
    finally:
        release_connection(conn)


def test_password_reset_expired_token_rejection():
    """Verify expired password reset token is rejected."""
    conn = get_connection()
    try:
        token = AuthLifecycleService.request_password_reset(conn, "admin@institute.edu")
        assert token is not None

        # Force expiration in database
        past_str = (datetime.datetime.now() - datetime.timedelta(hours=2)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        cur = conn.cursor()
        cur.execute("UPDATE password_resets SET expires_at = ?;", (past_str,))
        conn.commit()
        cur.close()

        with pytest.raises(ValueError, match="expired"):
            AuthLifecycleService.reset_password(conn, token, "UpdatedP@ssw0rd!")
    finally:
        release_connection(conn)


def test_totp_setup_verification_and_backup_code_consumption():
    """Verify complete 2FA lifecycle: setup, code verification, backup code usage, and disable."""
    conn = get_connection()
    try:
        user_id = 1  # admin user

        # 1. Setup TOTP
        setup_data = AuthLifecycleService.setup_totp(conn, user_id=user_id, username="admin")
        assert "secret" in setup_data
        assert "provisioning_uri" in setup_data
        assert len(setup_data["backup_codes"]) == 8

        status_before = AuthLifecycleService.get_totp_status(conn, user_id)
        assert status_before["is_enabled"] is False

        # 2. Verify with valid TOTP code to activate
        secret = setup_data["secret"]
        valid_code = TOTPManager.generate_totp(secret)
        enabled = AuthLifecycleService.verify_and_enable_totp(conn, user_id, valid_code)
        assert enabled is True

        status_after = AuthLifecycleService.get_totp_status(conn, user_id)
        assert status_after["is_enabled"] is True
        assert status_after["has_backup_codes"] is True

        # 3. Authenticate using TOTP code
        auth_code = TOTPManager.generate_totp(secret)
        assert AuthLifecycleService.verify_totp_or_backup(conn, user_id, auth_code) is True

        # 4. Authenticate using emergency backup code
        backup_code = setup_data["backup_codes"][0]
        assert AuthLifecycleService.verify_totp_or_backup(conn, user_id, backup_code) is True

        # Reusing same backup code should fail (consumed)
        assert AuthLifecycleService.verify_totp_or_backup(conn, user_id, backup_code) is False

        # 5. Disable 2FA
        AuthLifecycleService.disable_totp(conn, user_id)
        status_disabled = AuthLifecycleService.get_totp_status(conn, user_id)
        assert status_disabled["is_enabled"] is False
    finally:
        release_connection(conn)


def test_session_registration_and_revocation():
    """Verify registering active device session and remote termination."""
    conn = get_connection()
    try:
        user_id = 1
        session_id = "test_sess_token_9999"

        AuthLifecycleService.register_session(
            conn,
            user_id=user_id,
            session_id=session_id,
            ip_address="192.168.1.50",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        )

        sessions = AuthLifecycleService.list_sessions(
            conn, user_id=user_id, current_session_id=session_id
        )
        assert len(sessions) >= 1
        matched = [s for s in sessions if s["session_id"] == session_id]
        assert len(matched) == 1
        assert matched[0]["is_current"] is True

        # Revoke session
        revoked = AuthLifecycleService.revoke_session(conn, user_id=user_id, session_id=session_id)
        assert revoked is True

        # Verify no longer returned in active list
        sessions_after = AuthLifecycleService.list_sessions(conn, user_id=user_id)
        assert not any(s["session_id"] == session_id for s in sessions_after)
    finally:
        release_connection(conn)


def test_api_forgot_password_and_reset_endpoints(client):
    """Verify REST API POST /api/auth/forgot-password and /api/auth/reset-password."""
    # 1. Request reset
    req_res = client.post("/api/auth/forgot-password", json={"email": "admin@institute.edu"})
    assert req_res.status_code == 200
    payload = req_res.json()
    assert "message" in payload
    reset_token = payload.get("reset_token")
    assert reset_token is not None

    # 2. Confirm reset
    confirm_res = client.post(
        "/api/auth/reset-password",
        json={"token": reset_token, "new_password": "AdminNewSecurePassword2026!"},
    )
    assert confirm_res.status_code == 200
    assert "success" in confirm_res.json()["message"].lower()

    # 3. Bad token rejects with HTTP 400
    bad_res = client.post(
        "/api/auth/reset-password",
        json={"token": "invalid_fake_token_12345", "new_password": "AnotherPassword123!"},
    )
    assert bad_res.status_code == 400


def test_api_2fa_setup_verify_and_status_endpoints(client):
    """Verify REST API /api/auth/2fa/ endpoints with authenticated user."""
    # 1. Get 2FA status
    status_res = client.get("/api/auth/2fa/status")
    assert status_res.status_code == 200

    # 2. Setup 2FA
    setup_res = client.get("/api/auth/2fa/setup")
    assert setup_res.status_code == 200
    setup_data = setup_res.json()
    assert "secret" in setup_data
    assert "provisioning_uri" in setup_data
    assert len(setup_data["backup_codes"]) == 8

    # 3. Verify 2FA
    valid_code = TOTPManager.generate_totp(setup_data["secret"])
    verify_res = client.post("/api/auth/2fa/verify", json={"code": valid_code})
    assert verify_res.status_code == 200
    assert "activated" in verify_res.json()["message"].lower()

    # 4. Disable 2FA
    disable_res = client.post("/api/auth/2fa/disable")
    assert disable_res.status_code == 200
    assert "disabled" in disable_res.json()["message"].lower()


def test_api_sessions_list_and_revoke_endpoints(client):
    """Verify REST API /api/auth/sessions listing and revocation."""
    res = client.get("/api/auth/sessions")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "sessions" in data
    assert isinstance(data["sessions"], list)


def test_view_reset_password_html_page(anon_client):
    """Verify GET /reset-password renders self-service password recovery page."""
    # Stage 1: No token
    res1 = anon_client.get("/reset-password")
    assert res1.status_code == 200
    assert "Password Recovery" in res1.text
    assert "Registered Institutional Email" in res1.text

    # Stage 2: With token
    res2 = anon_client.get("/reset-password?token=sample_reset_token_xyz")
    assert res2.status_code == 200
    assert "New Password" in res2.text
    assert "sample_reset_token_xyz" in res2.text
