"""Institute Management System - Role-Based Access Control (RBAC) Models.
Pydantic v2 schemas for permissions catalog, role definitions, and staff authorization.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.models.auth import UserRole, UserStatus


class PermissionItem(BaseModel):
    """Individual permission item in the institutional catalog."""

    code: str
    category: str
    name: str
    description: str


class RoleInfo(BaseModel):
    """Institutional staff role definition and default capabilities."""

    role: str
    title: str
    description: str
    permissions: List[str]


class RBACMatrixOut(BaseModel):
    """Comprehensive RBAC matrix containing role capabilities and permission catalog."""

    roles: List[RoleInfo]
    permissions: List[PermissionItem]
    total_permissions: int


class UserRoleUpdate(BaseModel):
    """Schema for updating a user's institutional role."""

    role: UserRole


class UserPermissionsUpdate(BaseModel):
    """Schema for assigning custom permission grants or revocations."""

    custom_permissions: List[str] = Field(
        default_factory=list,
        description="List of permission codes, optionally prefixed with '+' (grant) or '-' (revoke)",
    )


class UserStaffOut(BaseModel):
    """Detailed staff profile including role, status, and resolved effective permissions."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: UserRole
    status: UserStatus
    faculty_id: Optional[int] = None
    student_id: Optional[int] = None
    custom_permissions: Optional[str] = None
    effective_permissions: List[str]
    created_at: str


class PermissionEvaluationRequest(BaseModel):
    """Schema to simulate and test access rights evaluation."""

    user_id: int
    permission: str


class PermissionEvaluationResult(BaseModel):
    """Result of permission check simulation."""

    user_id: int
    username: str
    role: str
    permission: str
    granted: bool
    reason: str
