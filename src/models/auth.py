"""Institute Management System - Authentication & User Account Models.
Pydantic v2 schemas for authentication, role-based access control, and audit trail.
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

UserRole = Literal["admin", "faculty", "student"]
UserStatus = Literal["active", "inactive", "suspended"]


class UserCreate(BaseModel):
    """Schema for user account registration."""

    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_\-\.]+$")
    email: str = Field(..., max_length=120, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(..., min_length=6, max_length=128)
    role: UserRole = "student"
    faculty_id: Optional[int] = None
    student_id: Optional[int] = None


class UserResponse(BaseModel):
    """Schema for public user profile responses (omits password hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: UserRole
    status: UserStatus
    faculty_id: Optional[int] = None
    student_id: Optional[int] = None
    last_login: Optional[str] = None
    created_at: str


class LoginRequest(BaseModel):
    """Schema for user credential submission."""

    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """Schema for successful authentication response with signed session token."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AuditLogResponse(BaseModel):
    """Schema for system security and administrative audit log entries."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    action: str
    resource: str
    resource_id: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: str
