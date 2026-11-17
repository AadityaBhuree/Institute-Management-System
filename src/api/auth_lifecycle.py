"""Identity Lifecycle, Password Self-Service, and Two-Factor Authentication REST API."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.core.security import get_current_user
from src.database.connection import get_db
from src.models.auth_lifecycle import (
    ActiveSessionsResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    RevokeSessionRequest,
    TOTPSetupResponse,
    TOTPStatusResponse,
    TOTPVerifyRequest,
)
from src.models.common import MessageResponse
from src.services.auth_lifecycle_service import AuthLifecycleService

router = APIRouter(tags=["Identity Lifecycle & 2FA"])


@router.post(
    "/api/auth/forgot-password",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_200_OK,
)
def forgot_password(
    payload: ForgotPasswordRequest,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Initiate self-service password recovery by email."""
    raw_token = AuthLifecycleService.request_password_reset(conn, payload.email)
    return ForgotPasswordResponse(
        message="If this email is registered, password recovery instructions have been dispatched.",
        reset_token=raw_token,
    )


@router.post(
    "/api/auth/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
def reset_password(
    payload: ResetPasswordRequest,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Confirm password change using a cryptographic reset token."""
    try:
        AuthLifecycleService.reset_password(conn, payload.token, payload.new_password)
        return MessageResponse(message="Password successfully updated. You may now sign in with your new credentials.")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/api/auth/2fa/setup",
    response_model=TOTPSetupResponse,
    status_code=status.HTTP_200_OK,
)
def setup_two_factor(
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Generate RFC 6238 TOTP key, provisioning URI, and backup recovery codes."""
    setup_data = AuthLifecycleService.setup_totp(
        conn,
        user_id=current_user["id"],
        username=current_user["username"],
    )
    return TOTPSetupResponse(**setup_data)


@router.post(
    "/api/auth/2fa/verify",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
def verify_two_factor(
    payload: TOTPVerifyRequest,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Verify initial TOTP token to activate two-factor authentication."""
    try:
        success = AuthLifecycleService.verify_and_enable_totp(conn, current_user["id"], payload.code)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid 6-digit TOTP authentication code. Please check your authenticator clock.",
            )
        return MessageResponse(message="Two-factor authentication successfully activated.")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "/api/auth/2fa/disable",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
def disable_two_factor(
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Deactivate two-factor authentication for current account."""
    AuthLifecycleService.disable_totp(conn, current_user["id"])
    return MessageResponse(message="Two-factor authentication has been disabled.")


@router.get(
    "/api/auth/2fa/status",
    response_model=TOTPStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_two_factor_status(
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Check whether two-factor authentication is active on current account."""
    status_dict = AuthLifecycleService.get_totp_status(conn, current_user["id"])
    return TOTPStatusResponse(**status_dict)


@router.get(
    "/api/auth/sessions",
    response_model=ActiveSessionsResponse,
    status_code=status.HTTP_200_OK,
)
def list_active_sessions(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all registered device sessions for current account."""
    current_cookie = request.cookies.get("ims_session")
    sessions = AuthLifecycleService.list_sessions(conn, current_user["id"], current_cookie)
    return ActiveSessionsResponse(total=len(sessions), sessions=sessions)


@router.post(
    "/api/auth/sessions/revoke",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
def revoke_session(
    payload: RevokeSessionRequest,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Terminate an active remote device session."""
    AuthLifecycleService.revoke_session(conn, current_user["id"], payload.session_id)
    return MessageResponse(message="Session successfully terminated.")
