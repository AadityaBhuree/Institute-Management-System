"""Institute Management System - Authentication & Access Control REST API.
Provides endpoints for login, session termination, profile introspection, and audit trail.
"""

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from src.core.security import (
    DEFAULT_SESSION_MAX_AGE,
    SESSION_COOKIE_NAME,
    create_session_token,
    get_current_user,
    get_current_user_optional,
    require_role,
)
from src.database.connection import get_db
from src.models.auth import (
    AuditLogResponse,
    LoginRequest,
    LoginResponse,
    UserCreate,
    UserResponse,
)
from src.models.common import MessageResponse
from src.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Authentication & Identity"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Authenticate and obtain session token",
)
def login(
    credentials: LoginRequest,
    request: Request,
    response: Response,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Authenticate user with username/email and password, returning signed session token and setting HTTP-only cookie."""
    ip_addr = request.client.host if request.client else None
    user = AuthService.authenticate(conn, credentials.username, credentials.password)

    if not user:
        AuthService.log_audit(
            conn,
            action="LOGIN_FAILED",
            resource="auth",
            details=f"Failed login attempt for identifier '{credentials.username}'.",
            ip_address=ip_addr,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login timestamp
    AuthService.update_last_login(conn, user["id"])

    # Generate tamper-proof token
    token = create_session_token(
        user_id=user["id"],
        username=user["username"],
        role=user["role"],
    )

    # Set secure HTTP-only session cookie
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=DEFAULT_SESSION_MAX_AGE,
        path="/",
    )

    # Log successful login
    AuthService.log_audit(
        conn,
        action="LOGIN_SUCCESS",
        resource="auth",
        resource_id=str(user["id"]),
        user_id=user["id"],
        username=user["username"],
        details=f"User '{user['username']}' logged in successfully.",
        ip_address=ip_addr,
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(**user),
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Terminate authenticated session",
)
def logout(
    request: Request,
    response: Response,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """Clear session cookie and log logout event."""
    ip_addr = request.client.host if request.client else None
    if current_user:
        AuthService.log_audit(
            conn,
            action="LOGOUT",
            resource="auth",
            resource_id=str(current_user["id"]),
            user_id=current_user["id"],
            username=current_user["username"],
            details=f"User '{current_user['username']}' logged out.",
            ip_address=ip_addr,
        )

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
    )
    return MessageResponse(message="Session successfully terminated.")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
def get_current_user_profile(
    current_user: dict = Depends(get_current_user),
):
    """Retrieve identity and permissions for the currently authenticated user."""
    return UserResponse(**current_user)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new institutional user (Admin only)",
)
def register_user(
    data: UserCreate,
    conn: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(require_role("admin")),
):
    """Provision a new user account with specified RBAC role (Admin only)."""
    try:
        user = AuthService.create_user(conn, data)
        return UserResponse(**user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List institutional user directory (Admin only)",
)
def list_users(
    role: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    conn: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(require_role("admin")),
):
    """List registered users with optional role and status filters."""
    users = AuthService.list_users(conn, role=role, status=status, limit=limit, offset=offset)
    return [UserResponse(**u) for u in users]


@router.get(
    "/audit-logs",
    response_model=List[AuditLogResponse],
    summary="Inspect security and operational audit trail (Admin only)",
)
def list_audit_logs(
    action: Optional[str] = None,
    resource: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    conn: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(require_role("admin")),
):
    """Retrieve immutable chronological audit records for institutional compliance."""
    logs = AuthService.list_audit_logs(
        conn, action=action, resource=resource, limit=limit, offset=offset
    )
    return [AuditLogResponse(**log) for log in logs]
