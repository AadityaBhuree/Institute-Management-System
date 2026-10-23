"""Institute Management System - Authentication & Audit Trail Service.
Handles user registration, authentication, credential validation, and security audit event logging.
"""

import sqlite3
from typing import Any, Dict, List, Optional

from src.core.security import hash_password, verify_password
from src.database.connection import transaction
from src.database.utils import row_to_dict, rows_to_list
from src.models.auth import UserCreate


class AuthService:
    """Service encapsulating user credentials management, RBAC entities, and audit logging."""

    @staticmethod
    def create_user(conn: sqlite3.Connection, data: UserCreate) -> Dict[str, Any]:
        """Register a new user account with a salted PBKDF2 hashed password."""
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?;", (data.username,))
        if cursor.fetchone():
            cursor.close()
            raise ValueError(f"Username '{data.username}' is already registered.")

        cursor.execute("SELECT id FROM users WHERE email = ?;", (data.email,))
        if cursor.fetchone():
            cursor.close()
            raise ValueError(f"Email address '{data.email}' is already registered.")
        cursor.close()

        password_hash = hash_password(data.password)

        with transaction(conn) as cur:
            cur.execute(
                """
                INSERT INTO users (username, email, password_hash, role, status, faculty_id, student_id)
                VALUES (?, ?, ?, ?, 'active', ?, ?);
                """,
                (
                    data.username,
                    data.email,
                    password_hash,
                    data.role,
                    data.faculty_id,
                    data.student_id,
                ),
            )
            user_id = cur.lastrowid

            cur.execute(
                """
                INSERT INTO audit_logs (user_id, username, action, resource, resource_id, details)
                VALUES (?, ?, 'USER_CREATED', 'users', ?, ?);
                """,
                (
                    user_id,
                    data.username,
                    str(user_id),
                    f"User account '{data.username}' registered with role '{data.role}'.",
                ),
            )

        user = AuthService.get_user_by_id(conn, user_id)
        if not user:
            raise RuntimeError("Failed to retrieve created user record.")
        return user

    @staticmethod
    def authenticate(
        conn: sqlite3.Connection, username_or_email: str, password: str
    ) -> Optional[Dict[str, Any]]:
        """Validate credentials and return user profile if matching and active."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, username, email, password_hash, role, status, faculty_id, student_id, last_login, created_at
            FROM users
            WHERE (username = ? OR email = ?);
            """,
            (username_or_email, username_or_email),
        )
        row = cursor.fetchone()
        cursor.close()

        if not row:
            return None

        user_dict = dict(row)
        if user_dict.get("status") != "active":
            return None

        if not verify_password(password, user_dict["password_hash"]):
            return None

        # Strip password hash before returning
        user_dict.pop("password_hash", None)
        return user_dict

    @staticmethod
    def update_last_login(conn: sqlite3.Connection, user_id: int) -> None:
        """Update last login timestamp for an authenticated user."""
        with transaction(conn) as cur:
            cur.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?;",
                (user_id,),
            )

    @staticmethod
    def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> Optional[Dict[str, Any]]:
        """Fetch user by ID excluding sensitive password hash."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, username, email, role, status, faculty_id, student_id, last_login, created_at
            FROM users
            WHERE id = ?;
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        return row_to_dict(row)

    @staticmethod
    def get_user_by_username(conn: sqlite3.Connection, username: str) -> Optional[Dict[str, Any]]:
        """Fetch user by unique username excluding password hash."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, username, email, role, status, faculty_id, student_id, last_login, created_at
            FROM users
            WHERE username = ?;
            """,
            (username,),
        )
        row = cursor.fetchone()
        cursor.close()
        return row_to_dict(row)

    @staticmethod
    def list_users(
        conn: sqlite3.Connection,
        role: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List user accounts with optional role and status filters."""
        query = """
            SELECT id, username, email, role, status, faculty_id, student_id, last_login, created_at
            FROM users
            WHERE 1=1
        """
        params: List[Any] = []
        if role:
            query += " AND role = ?"
            params.append(role)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY id DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        cursor.close()
        return rows_to_list(rows)

    @staticmethod
    def log_audit(
        conn: sqlite3.Connection,
        action: str,
        resource: str,
        resource_id: Optional[str] = None,
        details: Optional[str] = None,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record an immutable audit trail entry for institutional operations."""
        with transaction(conn) as cur:
            cur.execute(
                """
                INSERT INTO audit_logs (user_id, username, action, resource, resource_id, details, ip_address)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (user_id, username, action, resource, resource_id, details, ip_address),
            )
            audit_id = cur.lastrowid

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs WHERE id = ?;", (audit_id,))
        row = cursor.fetchone()
        cursor.close()
        result = row_to_dict(row)
        if not result:
            raise RuntimeError("Failed to fetch recorded audit log entry.")
        return result

    @staticmethod
    def list_audit_logs(
        conn: sqlite3.Connection,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Retrieve audit log records sorted descending by timestamp."""
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params: List[Any] = []

        if action:
            query += " AND action = ?"
            params.append(action)
        if resource:
            query += " AND resource = ?"
            params.append(resource)

        query += " ORDER BY id DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        cursor.close()
        return rows_to_list(rows)
