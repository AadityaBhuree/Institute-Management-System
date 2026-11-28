"""Tests for Granular Dynamic Institutional RBAC & Functional Permission Matrix (Phase 18).
Verifies role capabilities, custom permission grants/revocations, access evaluation engine,
and departmental security boundaries.
"""

import pytest
from fastapi.testclient import TestClient

from src.core.security import (
    SESSION_COOKIE_NAME,
    create_session_token,
    get_user_permissions,
    has_permission,
)
from src.database.connection import get_connection, release_connection, transaction
from src.models.auth import UserCreate
from src.services.auth_service import AuthService


@pytest.fixture
def registrar_client(setup_test_db):
    """Test client authenticated with registrar role."""
    from src.app import app

    conn = get_connection()
    try:
        user = AuthService.get_user_by_username(conn, "registrar")
        if not user:
            user = AuthService.create_user(
                conn,
                UserCreate(
                    username="registrar_test",
                    email="reg_test@institute.edu",
                    password="password123",
                    role="registrar",
                ),
            )
        user_id = user["id"]
    finally:
        release_connection(conn)

    token = create_session_token(user_id=user_id, username="registrar", role="registrar")
    with TestClient(app) as test_client:
        test_client.cookies.set(SESSION_COOKIE_NAME, token)
        yield test_client


@pytest.fixture
def bursar_client(setup_test_db):
    """Test client authenticated with bursar role."""
    from src.app import app

    conn = get_connection()
    try:
        user = AuthService.get_user_by_username(conn, "bursar")
        if not user:
            user = AuthService.create_user(
                conn,
                UserCreate(
                    username="bursar_test",
                    email="bursar_test@institute.edu",
                    password="password123",
                    role="bursar",
                ),
            )
        user_id = user["id"]
    finally:
        release_connection(conn)

    token = create_session_token(user_id=user_id, username="bursar", role="bursar")
    with TestClient(app) as test_client:
        test_client.cookies.set(SESSION_COOKIE_NAME, token)
        yield test_client


def test_rbac_matrix_and_catalog(client):
    """Verify RBAC matrix API returns complete roles and permission catalog."""
    res = client.get("/api/rbac/matrix")
    assert res.status_code == 200
    data = res.json()

    assert "roles" in data
    assert "permissions" in data
    assert data["total_permissions"] >= 26

    # Verify key roles are present
    role_names = [r["role"] for r in data["roles"]]
    assert "admin" in role_names
    assert "registrar" in role_names
    assert "bursar" in role_names
    assert "librarian" in role_names
    assert "health_officer" in role_names
    assert "placement_officer" in role_names
    assert "faculty" in role_names
    assert "student" in role_names

    # Check admin has wildcard (*)
    admin_role = next(r for r in data["roles"] if r["role"] == "admin")
    assert "*" in admin_role["permissions"]

    # Check registrar permissions
    registrar_role = next(r for r in data["roles"] if r["role"] == "registrar")
    assert "students:write" in registrar_role["permissions"]
    assert "reports:archive" in registrar_role["permissions"]
    assert "id_cards:manage" in registrar_role["permissions"]
    assert "finance:write" not in registrar_role["permissions"]


def test_rbac_roles_and_permissions_endpoints(client):
    """Verify distinct /roles and /permissions listing endpoints."""
    roles_res = client.get("/api/rbac/roles")
    assert roles_res.status_code == 200
    assert len(roles_res.json()) >= 8

    perms_res = client.get("/api/rbac/permissions")
    assert perms_res.status_code == 200
    assert len(perms_res.json()) >= 26


def test_permission_evaluation_unit():
    """Unit test has_permission and get_user_permissions logic."""
    # 1. Admin wildcard
    admin_user = {"role": "admin"}
    assert has_permission(admin_user, "anything:random") is True
    assert get_user_permissions(admin_user) == ["*"]

    # 2. Registrar permissions
    registrar_user = {"role": "registrar"}
    assert has_permission(registrar_user, "students:read") is True
    assert has_permission(registrar_user, "students:write") is True
    assert has_permission(registrar_user, "students:delete") is True
    assert has_permission(registrar_user, "finance:write") is False

    # 3. Bursar permissions
    bursar_user = {"role": "bursar"}
    assert has_permission(bursar_user, "finance:write") is True
    assert has_permission(bursar_user, "students:delete") is False

    # 4. Custom permission grant
    custom_grant_user = {
        "role": "librarian",
        "custom_permissions": '["+reports:read", "+id_cards:manage"]',
    }
    assert has_permission(custom_grant_user, "library:read") is True
    assert has_permission(custom_grant_user, "reports:read") is True
    assert has_permission(custom_grant_user, "id_cards:manage") is True
    assert has_permission(custom_grant_user, "students:delete") is False

    # 5. Custom permission revocation
    custom_revoke_user = {
        "role": "librarian",
        "custom_permissions": '["-library:write"]',
    }
    assert has_permission(custom_revoke_user, "library:read") is True
    assert has_permission(custom_revoke_user, "library:write") is False


def test_unauthenticated_and_unauthorized_rbac_rejections(anon_client, student_client):
    """Verify unauthenticated requests return 401 and students return 403."""
    # Unauthenticated client
    res = anon_client.get("/api/rbac/users")
    assert res.status_code == 401

    # Student client lacks rbac:manage / system:admin
    res2 = student_client.get("/api/rbac/users")
    assert res2.status_code == 403
    assert "Insufficient privileges" in res2.json()["detail"]


def test_registrar_boundary_success_and_restrictions(registrar_client, bursar_client):
    """Verify registrar has authority over id cards and archival, but cannot access bursar writes."""
    # Registrar can access batch ID cards endpoint
    # (May return 400 if no students, but must NOT return 403 Forbidden)
    res_batch = registrar_client.get("/api/id-cards/batch/pdf")
    assert res_batch.status_code in (200, 400)  # Not 403

    # Bursar is FORBIDDEN from batch ID cards
    res_bursar_batch = bursar_client.get("/api/id-cards/batch/pdf")
    assert res_bursar_batch.status_code == 403
    assert "id_cards:manage" in res_bursar_batch.json()["detail"]

    # Bursar is FORBIDDEN from cohort archival
    res_bursar_arch = bursar_client.post(
        "/api/reports/archival/cohort",
        json={"graduation_year": 2026},
    )
    assert res_bursar_arch.status_code == 403


def test_staff_users_listing_and_detail(client):
    """Verify listing staff users with resolved effective permissions."""
    res = client.get("/api/rbac/users")
    assert res.status_code == 200
    users = res.json()
    assert len(users) >= 1

    # Each user must have effective_permissions list
    first_user = users[0]
    assert "effective_permissions" in first_user
    assert isinstance(first_user["effective_permissions"], list)

    # Get single user
    user_id = first_user["id"]
    detail_res = client.get(f"/api/rbac/users/{user_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == user_id


def test_update_user_role_and_audit(client):
    """Verify reassigning a user's role and generating audit logs."""
    # Create a fresh user first
    conn = get_connection()
    try:
        user = AuthService.create_user(
            conn,
            UserCreate(
                username="role_test_user",
                email="roletest@institute.edu",
                password="password123",
                role="student",
            ),
        )
        user_id = user["id"]
    finally:
        release_connection(conn)

    # Reassign to librarian
    res = client.put(
        f"/api/rbac/users/{user_id}/role",
        json={"role": "librarian"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "librarian"
    assert "library:read" in data["effective_permissions"]

    # Check audit log
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT action, details FROM audit_logs WHERE resource = 'rbac' ORDER BY id DESC LIMIT 1;"
        )
        row = cursor.fetchone()
        cursor.close()
        assert row is not None
        assert row["action"] == "ROLE_UPDATED"
        assert "role_test_user" in row["details"]
    finally:
        release_connection(conn)


def test_update_user_permissions_custom_overrides(client):
    """Verify setting custom permission overrides on an account."""
    conn = get_connection()
    try:
        user = AuthService.create_user(
            conn,
            UserCreate(
                username="custom_perms_user",
                email="customperm@institute.edu",
                password="password123",
                role="librarian",
            ),
        )
        user_id = user["id"]
    finally:
        release_connection(conn)

    # Grant extra capabilities
    res = client.put(
        f"/api/rbac/users/{user_id}/permissions",
        json={"custom_permissions": ["+reports:read", "-library:write"]},
    )
    assert res.status_code == 200
    data = res.json()
    assert "reports:read" in data["effective_permissions"]
    assert "library:write" not in data["effective_permissions"]
    assert "library:read" in data["effective_permissions"]


def test_access_rights_simulation_evaluator(client):
    """Verify live access rights evaluation endpoint."""
    conn = get_connection()
    try:
        user = AuthService.get_user_by_username(conn, "admin")
        admin_id = user["id"]
        student = AuthService.get_user_by_username(conn, "student")
        student_id = student["id"]
    finally:
        release_connection(conn)

    # 1. Admin evaluation
    res_admin = client.post(
        "/api/rbac/evaluate",
        json={"user_id": admin_id, "permission": "students:delete"},
    )
    assert res_admin.status_code == 200
    data_admin = res_admin.json()
    assert data_admin["granted"] is True
    assert "Super Administrator" in data_admin["reason"]

    # 2. Student evaluation on sensitive permission
    res_student = client.post(
        "/api/rbac/evaluate",
        json={"user_id": student_id, "permission": "finance:write"},
    )
    assert res_student.status_code == 200
    data_student = res_student.json()
    assert data_student["granted"] is False
    assert "Denied" in data_student["reason"]


def test_cannot_demote_sole_active_admin(client):
    """Verify security safeguard prevents accidental lockout of the last admin."""
    conn = get_connection()
    try:
        # Find active admins
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE role = 'admin' AND status = 'active';")
        admins = cursor.fetchall()
        cursor.close()

        # If more than 1 admin, set all but 1 to inactive for the test
        if len(admins) > 1:
            with transaction(conn) as cur:
                for a in admins[1:]:
                    cur.execute("UPDATE users SET status = 'inactive' WHERE id = ?;", (a["id"],))

        sole_admin_id = admins[0]["id"]
    finally:
        release_connection(conn)

    # Attempt to demote sole admin
    res = client.put(
        f"/api/rbac/users/{sole_admin_id}/role",
        json={"role": "student"},
    )
    assert res.status_code == 400
    assert "Cannot demote the sole active administrator" in res.json()["detail"]


def test_rbac_ssr_web_page(client, anon_client, student_client):
    """Verify SSR web page /rbac access controls and rendering."""
    # 1. Anon redirects to login
    res_anon = anon_client.get("/rbac", follow_redirects=False)
    assert res_anon.status_code == 302
    assert "/login" in res_anon.headers["location"]

    # 2. Student forbidden
    res_student = student_client.get("/rbac")
    assert res_student.status_code == 403

    # 3. Admin renders glassmorphism view
    res_admin = client.get("/rbac")
    assert res_admin.status_code == 200
    assert (
        "Institutional Roles &amp; Permissions" in res_admin.text
        or "Institutional Roles & Permissions" in res_admin.text
    )
    assert "Capability Matrix" in res_admin.text
    assert "Staff Directory" in res_admin.text
    assert "Access Rights Evaluator" in res_admin.text
