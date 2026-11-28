"""Institute Management System - Security & Authentication Primitives.
Provides password hashing, session token creation/verification, granular permission checking,
and RBAC FastAPI dependencies.
"""

import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from typing import Callable, Dict, List, Optional, Set

from fastapi import Depends, HTTPException, Request, status

from src.core.config import SECRET_KEY
from src.database.connection import get_db

SESSION_COOKIE_NAME = "ims_session"
DEFAULT_SESSION_MAX_AGE = 7 * 24 * 3600  # 7 days

# Institutional Staff & Student Roles
INSTITUTIONAL_ROLES = (
    "admin",
    "registrar",
    "bursar",
    "librarian",
    "health_officer",
    "placement_officer",
    "faculty",
    "student",
)

# Standard Role to Default Permissions Mapping
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "admin": {"*"},  # Super-admin wildcard access
    "registrar": {
        "students:read",
        "students:write",
        "students:delete",
        "academics:read",
        "academics:write",
        "grades:read",
        "attendance:read",
        "reports:read",
        "reports:archive",
        "id_cards:manage",
    },
    "bursar": {
        "finance:read",
        "finance:write",
        "students:read",
        "scholarships:manage",
        "reports:read",
    },
    "librarian": {
        "library:read",
        "library:write",
        "students:read",
    },
    "health_officer": {
        "health:read",
        "health:write",
        "students:read",
        "reports:read",
    },
    "placement_officer": {
        "placements:read",
        "placements:write",
        "students:read",
        "reports:read",
    },
    "faculty": {
        "students:read",
        "academics:read",
        "grades:read",
        "grades:write",
        "attendance:read",
        "attendance:write",
        "leaves:write",
    },
    "student": {
        "leaves:write",
    },
}

# Catalog of System Permissions for UI & Management APIs
SYSTEM_PERMISSIONS_CATALOG: List[Dict[str, str]] = [
    {
        "code": "students:read",
        "category": "STUDENTS",
        "name": "View Scholar Profiles",
        "description": "Read scholar records, dossiers, and academic enrollment status.",
    },
    {
        "code": "students:write",
        "category": "STUDENTS",
        "name": "Manage Scholars",
        "description": "Register, modify, enroll, and update scholar profiles.",
    },
    {
        "code": "students:delete",
        "category": "STUDENTS",
        "name": "Archive / Delete Scholars",
        "description": "Soft-delete or purge scholar files from the active registry.",
    },
    {
        "code": "academics:read",
        "category": "ACADEMICS",
        "name": "View Academic Curricula",
        "description": "Inspect departments, courses, syllabi, and lecture timetables.",
    },
    {
        "code": "academics:write",
        "category": "ACADEMICS",
        "name": "Manage Courses & Timetables",
        "description": "Create departments, update courses, and allocate timetable slots.",
    },
    {
        "code": "grades:read",
        "category": "EXAMINATIONS",
        "name": "View Marks & Transcripts",
        "description": "Inspect semester exam marks, grade sheets, and transcripts.",
    },
    {
        "code": "grades:write",
        "category": "EXAMINATIONS",
        "name": "Record Grades & Transcripts",
        "description": "Submit exam scores, finalize GPAs, and issue transcripts.",
    },
    {
        "code": "attendance:read",
        "category": "ATTENDANCE",
        "name": "View Attendance Logs",
        "description": "Inspect student attendance rosters and absence percentage metrics.",
    },
    {
        "code": "attendance:write",
        "category": "ATTENDANCE",
        "name": "Record Attendance",
        "description": "Take roll call and log daily class attendance sessions.",
    },
    {
        "code": "finance:read",
        "category": "FINANCE",
        "name": "View Bursar Financials",
        "description": "Inspect tuition fee structures, invoices, payments, and ledger balances.",
    },
    {
        "code": "finance:write",
        "category": "FINANCE",
        "name": "Manage Bursar Operations",
        "description": "Configure fee structures, issue student invoices, and record payments.",
    },
    {
        "code": "library:read",
        "category": "LIBRARY",
        "name": "Search Library Catalog",
        "description": "Search monographs, textbooks, and inspect loan status.",
    },
    {
        "code": "library:write",
        "category": "LIBRARY",
        "name": "Manage Library Circulation",
        "description": "Catalog monographs, checkout/return books, and assess overdue fines.",
    },
    {
        "code": "health:read",
        "category": "HEALTH",
        "name": "View Infirmary Logs",
        "description": "Inspect campus health center visits and patient medical records.",
    },
    {
        "code": "health:write",
        "category": "HEALTH",
        "name": "Manage Clinical Care",
        "description": "Record medical encounters, dispense medication, and sign clearance certificates.",
    },
    {
        "code": "placements:read",
        "category": "PLACEMENTS",
        "name": "Browse Corporate Drives",
        "description": "View placement drives, recruitment schedules, and job openings.",
    },
    {
        "code": "placements:write",
        "category": "PLACEMENTS",
        "name": "Manage Career Services",
        "description": "Post corporate drives, shortlist scholars, and log salary packages.",
    },
    {
        "code": "hostel:manage",
        "category": "CAMPUS_SERVICES",
        "name": "Manage Student Housing",
        "description": "Allocate rooms, inspect occupancy, and manage hostel blocks.",
    },
    {
        "code": "transport:manage",
        "category": "CAMPUS_SERVICES",
        "name": "Manage Transit Fleet",
        "description": "Configure bus routes, fleet vehicles, and transit passes.",
    },
    {
        "code": "scholarships:manage",
        "category": "CAMPUS_SERVICES",
        "name": "Manage Financial Aid",
        "description": "Configure scholarship schemes, review applications, and disburse aid.",
    },
    {
        "code": "events:manage",
        "category": "CAMPUS_SERVICES",
        "name": "Manage Campus Events",
        "description": "Schedule symposiums, hackathons, and handle registrations.",
    },
    {
        "code": "inventory:manage",
        "category": "CAMPUS_SERVICES",
        "name": "Manage Physical Assets",
        "description": "Track laboratory equipment, campus assets, and maintenance.",
    },
    {
        "code": "reports:read",
        "category": "REPORTS",
        "name": "Export Analytics & Workbooks",
        "description": "Download Excel audit workbooks and vector PDF summaries.",
    },
    {
        "code": "reports:archive",
        "category": "REPORTS",
        "name": "Execute Cohort Archival",
        "description": "Perform cold storage archival on graduated scholar cohorts.",
    },
    {
        "code": "id_cards:manage",
        "category": "CREDENTIALS",
        "name": "Manage Digital ID Cards",
        "description": "Compile, preview, and batch-print official institutional ID cards.",
    },
    {
        "code": "system:admin",
        "category": "SYSTEM",
        "name": "System Diagnostics & Backups",
        "description": "Execute database backups, WAL optimize, and inspect telemetry.",
    },
    {
        "code": "rbac:manage",
        "category": "SYSTEM",
        "name": "Manage Roles & Permissions",
        "description": "Reassign institutional staff roles and customize granular permissions.",
    },
]


def hash_password(password: str) -> str:
    """Hash a plaintext password using PBKDF2-HMAC-SHA256 with 100,000 iterations and a random salt."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"pbkdf2_sha256$100000${salt}${dk.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored PBKDF2 hash using timing-safe comparison."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = parts[2]
        expected_hex = parts[3]
        dk = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iterations
        )
        return hmac.compare_digest(dk.hex(), expected_hex)
    except Exception:
        return False


def create_session_token(
    user_id: int,
    username: str,
    role: str,
    expires_in_seconds: int = DEFAULT_SESSION_MAX_AGE,
) -> str:
    """Generate a tamper-proof HMAC-SHA256 signed session token containing user identity and expiration."""
    exp = int(time.time()) + expires_in_seconds
    payload = {
        "uid": user_id,
        "sub": username,
        "role": role,
        "exp": exp,
    }
    payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode("utf-8").rstrip("=")

    secret_bytes = SECRET_KEY.encode("utf-8")
    signature = hmac.new(secret_bytes, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()

    return f"{payload_b64}.{signature}"


def verify_session_token(token: str) -> Optional[dict]:
    """Verify token signature and expiration, returning decoded payload if valid."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature = parts

        # Recompute signature
        secret_bytes = SECRET_KEY.encode("utf-8")
        expected_sig = hmac.new(
            secret_bytes, payload_b64.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None

        # Decode payload with padding
        padding = 4 - (len(payload_b64) % 4)
        if padding and padding < 4:
            payload_b64 += "=" * padding

        payload_bytes = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
        payload = json.loads(payload_bytes.decode("utf-8"))

        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None


def get_user_permissions(user: dict) -> List[str]:
    """Calculate the resolved effective permissions list for a user.

    Combines role-derived permissions with any user-level custom grants and revocations.
    """
    role = user.get("role", "student")
    if role == "admin":
        return ["*"]

    perms: Set[str] = set(ROLE_PERMISSIONS.get(role, set()))

    custom_raw = user.get("custom_permissions")
    if custom_raw:
        try:
            if isinstance(custom_raw, str):
                custom_list = json.loads(custom_raw)
            elif isinstance(custom_raw, list):
                custom_list = custom_raw
            else:
                custom_list = []

            for item in custom_list:
                item_str = str(item).strip()
                if item_str.startswith("-"):
                    perms.discard(item_str[1:])
                elif item_str.startswith("+"):
                    perms.add(item_str[1:])
                else:
                    perms.add(item_str)
        except Exception:
            pass

    return sorted(perms)


def has_permission(user: Optional[dict], permission: str) -> bool:
    """Evaluate whether a user holds a specific permission code."""
    if not user:
        return False
    if user.get("role") == "admin":
        return True
    perms = get_user_permissions(user)
    return "*" in perms or permission in perms


def get_current_user_optional(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
) -> Optional[dict]:
    """Extract authenticated user from cookie or Authorization header without raising an exception if absent."""
    token: Optional[str] = request.cookies.get(SESSION_COOKIE_NAME)

    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header:
            if auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()
            else:
                token = auth_header.strip()

    if not token:
        # Also check query param 'token' for EventSource / WebSocket clients
        token = request.query_params.get("token")

    if not token:
        return None

    payload = verify_session_token(token)
    if not payload:
        return None

    user_id = payload.get("uid")
    if not user_id:
        return None

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, username, email, role, status, faculty_id, student_id, custom_permissions, last_login, created_at
        FROM users
        WHERE id = ? AND status = 'active';
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    cursor.close()

    if not row:
        return None

    user_dict = dict(row)
    user_dict["permissions"] = get_user_permissions(user_dict)
    return user_dict


def get_current_user(
    request: Request,
    user: Optional[dict] = Depends(get_current_user_optional),
) -> dict:
    """Dependency that requires an authenticated user; raises HTTP 401 if not authenticated."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(*allowed_roles: str) -> Callable:
    """Dependency factory that enforces Role-Based Access Control (RBAC)."""

    def role_dependency(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Insufficient privileges. Required role(s): {', '.join(allowed_roles)}.",
            )
        return current_user

    return role_dependency


def require_permission(permission: str) -> Callable:
    """FastAPI dependency factory enforcing a specific functional permission."""

    def permission_dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if not has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Insufficient privileges. Required permission: '{permission}'.",
            )
        return current_user

    return permission_dependency


def require_any_permission(*permissions: str) -> Callable:
    """FastAPI dependency factory requiring at least one of the specified permissions."""

    def any_permission_dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") == "admin":
            return current_user
        user_perms = set(get_user_permissions(current_user))
        if "*" in user_perms or any(p in user_perms for p in permissions):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Insufficient privileges. Required one of: {', '.join(permissions)}.",
        )

    return any_permission_dependency
