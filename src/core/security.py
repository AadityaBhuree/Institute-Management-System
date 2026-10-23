"""Institute Management System - Security & Authentication Primitives.
Provides password hashing, session token creation/verification, and RBAC FastAPI dependencies.
"""

import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from typing import Callable, Optional

from fastapi import Depends, HTTPException, Request, status

from src.core.config import SECRET_KEY
from src.database.connection import get_db

SESSION_COOKIE_NAME = "ims_session"
DEFAULT_SESSION_MAX_AGE = 7 * 24 * 3600  # 7 days


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
        SELECT id, username, email, role, status, faculty_id, student_id, last_login, created_at
        FROM users
        WHERE id = ? AND status = 'active';
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    cursor.close()

    if not row:
        return None

    return dict(row)


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
