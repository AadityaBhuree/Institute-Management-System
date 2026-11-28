"""Institute Management System - Role-Based Access Control (RBAC) Service.
Manages institutional roles, permission matrices, staff account authorization, and access auditing.
"""

import json
import sqlite3
from typing import Any, Dict, List, Optional

from src.core.security import (
    INSTITUTIONAL_ROLES,
    ROLE_PERMISSIONS,
    SYSTEM_PERMISSIONS_CATALOG,
    get_user_permissions,
    has_permission,
)
from src.database.connection import transaction
from src.models.rbac import (
    PermissionItem,
    RBACMatrixOut,
    RoleInfo,
)
from src.services.auth_service import AuthService

ROLE_METADATA: Dict[str, Dict[str, str]] = {
    "admin": {
        "title": "Super Administrator",
        "description": "Full unrestricted system authority across all academic, financial, medical, and technical domains.",
    },
    "registrar": {
        "title": "Academic Registrar & Admissions Director",
        "description": "Authority over scholar admissions, identity verification, enrollment dossiers, courses, grades, and archival.",
    },
    "bursar": {
        "title": "Bursar & Financial Comptroller",
        "description": "Authority over tuition fee structures, student invoicing, payment verification, scholarships, and financial ledgers.",
    },
    "librarian": {
        "title": "Head of Library Circulation",
        "description": "Authority over monograph cataloging, textbook issues, return inspections, and overdue fine collection.",
    },
    "health_officer": {
        "title": "Campus Physician & Chief Medical Officer",
        "description": "Authority over infirmary health encounters, clinical diagnoses, pharmacy dispensary, and medical clearance certificates.",
    },
    "placement_officer": {
        "title": "Dean of Corporate Relations & Career Services",
        "description": "Authority over campus placement recruitment drives, corporate job postings, interview scheduling, and package analytics.",
    },
    "faculty": {
        "title": "Academic Faculty & Lecturer",
        "description": "Authority over classroom instruction workbench, student grading, attendance rosters, and leave requests.",
    },
    "student": {
        "title": "Undergraduate / Graduate Scholar",
        "description": "Self-service scholar dossier, enrolled courses, attendance summaries, exam transcripts, and leave petitions.",
    },
}


class RBACService:
    """Service encapsulating institutional authorization logic, staff role assignments, and permission audits."""

    @staticmethod
    def get_matrix() -> RBACMatrixOut:
        """Construct the complete institutional RBAC matrix with roles and permission catalog."""
        roles: List[RoleInfo] = []
        for role in INSTITUTIONAL_ROLES:
            meta = ROLE_METADATA.get(role, {"title": role.capitalize(), "description": ""})
            perms = sorted(ROLE_PERMISSIONS.get(role, set()))
            roles.append(
                RoleInfo(
                    role=role,
                    title=meta["title"],
                    description=meta["description"],
                    permissions=perms,
                )
            )

        permissions = [PermissionItem(**p) for p in SYSTEM_PERMISSIONS_CATALOG]
        return RBACMatrixOut(
            roles=roles,
            permissions=permissions,
            total_permissions=len(permissions),
        )

    @staticmethod
    def list_roles() -> List[RoleInfo]:
        """Retrieve list of institutional staff roles and default permissions."""
        return RBACService.get_matrix().roles

    @staticmethod
    def list_permissions() -> List[PermissionItem]:
        """Retrieve complete catalog of system permissions."""
        return [PermissionItem(**p) for p in SYSTEM_PERMISSIONS_CATALOG]

    @staticmethod
    def list_staff_users(
        conn: sqlite3.Connection,
        role: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List user accounts with their assigned role and resolved effective permissions."""
        query = """
            SELECT id, username, email, role, status, faculty_id, student_id, custom_permissions, last_login, created_at
            FROM users
            WHERE 1=1
        """
        params: List[Any] = []
        if role:
            query += " AND role = ?"
            params.append(role)
        if search:
            query += " AND (username LIKE ? OR email LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term])

        query += " ORDER BY id ASC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()

        results = []
        for r in rows:
            u = dict(r)
            u["effective_permissions"] = get_user_permissions(u)
            results.append(u)
        return results

    @staticmethod
    def update_user_role(
        conn: sqlite3.Connection,
        user_id: int,
        new_role: str,
        admin_user: dict,
    ) -> Dict[str, Any]:
        """Reassign an institutional user's role with safeguards and audit logging."""
        if new_role not in INSTITUTIONAL_ROLES:
            raise ValueError(
                f"Invalid role '{new_role}'. Allowed roles: {', '.join(INSTITUTIONAL_ROLES)}."
            )

        user = AuthService.get_user_by_id(conn, user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} does not exist.")

        # Prevent accidental lockout: cannot demote the last active super-administrator
        if user["role"] == "admin" and new_role != "admin":
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as admin_count FROM users WHERE role = 'admin' AND status = 'active';"
            )
            count_row = cursor.fetchone()
            cursor.close()
            admin_count = count_row["admin_count"] if count_row else 0
            if admin_count <= 1:
                raise ValueError("Cannot demote the sole active administrator of the institution.")

        old_role = user["role"]
        with transaction(conn) as cur:
            cur.execute(
                "UPDATE users SET role = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (new_role, user_id),
            )
            cur.execute(
                """
                INSERT INTO audit_logs (user_id, username, action, resource, resource_id, details)
                VALUES (?, ?, 'ROLE_UPDATED', 'rbac', ?, ?);
                """,
                (
                    admin_user.get("id"),
                    admin_user.get("username", "admin"),
                    str(user_id),
                    f"User '{user['username']}' role changed from '{old_role}' to '{new_role}'.",
                ),
            )

        updated_user = AuthService.get_user_by_id(conn, user_id)
        if not updated_user:
            raise RuntimeError("Failed to retrieve updated user record.")
        updated_user["effective_permissions"] = get_user_permissions(updated_user)
        return updated_user

    @staticmethod
    def update_user_permissions(
        conn: sqlite3.Connection,
        user_id: int,
        custom_permissions: List[str],
        admin_user: dict,
    ) -> Dict[str, Any]:
        """Set custom permission grants/revocations for an institutional staff member."""
        user = AuthService.get_user_by_id(conn, user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} does not exist.")

        # Clean and serialize custom permissions
        cleaned = [p.strip() for p in custom_permissions if p and p.strip()]
        perm_json = json.dumps(cleaned) if cleaned else None

        with transaction(conn) as cur:
            cur.execute(
                "UPDATE users SET custom_permissions = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (perm_json, user_id),
            )
            cur.execute(
                """
                INSERT INTO audit_logs (user_id, username, action, resource, resource_id, details)
                VALUES (?, ?, 'PERMISSIONS_UPDATED', 'rbac', ?, ?);
                """,
                (
                    admin_user.get("id"),
                    admin_user.get("username", "admin"),
                    str(user_id),
                    f"User '{user['username']}' custom permissions set to: {perm_json or '[]'}.",
                ),
            )

        updated_user = AuthService.get_user_by_id(conn, user_id)
        if not updated_user:
            raise RuntimeError("Failed to retrieve updated user record.")
        updated_user["effective_permissions"] = get_user_permissions(updated_user)
        return updated_user

    @staticmethod
    def evaluate_access(
        conn: sqlite3.Connection,
        user_id: int,
        permission: str,
    ) -> Dict[str, Any]:
        """Simulate and evaluate whether a user has authority to perform an action."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, username, email, role, status, faculty_id, student_id, custom_permissions, last_login, created_at
            FROM users
            WHERE id = ?;
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        cursor.close()

        if not row:
            raise ValueError(f"User with ID {user_id} does not exist.")

        user = dict(row)
        granted = has_permission(user, permission)

        role = user.get("role", "student")
        if role == "admin":
            reason = "Granted via Super Administrator wildcard authority (*)."
        elif permission in ROLE_PERMISSIONS.get(role, set()):
            reason = f"Granted via institutional role '{role}' baseline capability."
        elif granted:
            reason = "Granted via user-level custom permission override."
        else:
            reason = f"Denied: Role '{role}' does not possess '{permission}' and no custom grant was applied."

        return {
            "user_id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "permission": permission,
            "granted": granted,
            "reason": reason,
        }
