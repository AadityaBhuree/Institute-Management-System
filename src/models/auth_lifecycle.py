"""Pydantic Models for Identity Lifecycle, Password Self-Service, and 2FA."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ForgotPasswordRequest(BaseModel):
    """Payload to initiate a password recovery workflow."""

    email: str = Field(..., description="Registered account email address")


class ForgotPasswordResponse(BaseModel):
    """Result of password recovery request."""

    message: str
    reset_token: Optional[str] = Field(default=None, description="Reset token (populated in staging/test environments)")


class ResetPasswordRequest(BaseModel):
    """Payload to confirm password reset with cryptographic token."""

    token: str = Field(..., min_length=16, description="Cryptographic single-use reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New secret password")


class TOTPSetupResponse(BaseModel):
    """Two-factor authentication enrollment packet."""

    secret: str = Field(..., description="Base32 TOTP secret key")
    provisioning_uri: str = Field(..., description="otpauth:// URI for authenticator QR code rendering")
    backup_codes: List[str] = Field(..., description="One-time emergency recovery codes")


class TOTPVerifyRequest(BaseModel):
    """Payload to verify 6-digit TOTP code or recovery code."""

    code: str = Field(..., min_length=6, max_length=12, description="6-digit TOTP token or backup recovery code")


class TOTPStatusResponse(BaseModel):
    """Account two-factor authentication configuration status."""

    is_enabled: bool
    has_backup_codes: bool


class SessionInfo(BaseModel):
    """Active user authentication session profile."""

    session_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    last_active: str
    is_current: bool = False


class ActiveSessionsResponse(BaseModel):
    """List of active device sessions for current user."""

    total: int
    sessions: List[SessionInfo]


class RevokeSessionRequest(BaseModel):
    """Payload to revoke an active remote session."""

    session_id: str = Field(..., min_length=1, description="Target session identifier to terminate")
