"""Institute Management System - Role-Based Access Control (RBAC) API Endpoints.
Provides institutional permission matrix inspection, staff role assignment, custom permission overrides,
and access simulation.
"""

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.core.security import get_current_user, require_any_permission, require_role
from src.database.connection import get_db
from src.models.rbac import (
    PermissionEvaluationRequest,
    PermissionEvaluationResult,
    PermissionItem,
    RBACMatrixOut,
    RoleInfo,
    UserPermissionsUpdate,
    UserRoleUpdate,
    UserStaffOut,
)
from src.services.rbac_service import RBACService

router = APIRouter(prefix="/api/rbac", tags=["Role-Based Access Control (RBAC)"])


@router.get(
    "/matrix",
    response_model=RBACMatrixOut,
    summary="Get institutional RBAC matrix & permissions catalog",
)
def get_rbac_matrix(
    current_user: dict = Depends(get_current_user),
):
    """Retrieve full matrix of institutional staff roles and permissions catalog."""
    return RBACService.get_matrix()


@router.get(
    "/roles",
    response_model=List[RoleInfo],
    summary="List institutional roles and capabilities",
)
def list_roles(
    current_user: dict = Depends(get_current_user),
):
    """Retrieve list of institutional staff roles with default permission sets."""
    return RBACService.list_roles()


@router.get(
    "/permissions",
    response_model=List[PermissionItem],
    summary="List institutional system permissions catalog",
)
def list_permissions(
    current_user: dict = Depends(get_current_user),
):
    """Retrieve all system permission definitions organized by domain category."""
    return RBACService.list_permissions()


@router.get(
    "/users",
    response_model=List[UserStaffOut],
    summary="List staff accounts with resolved effective permissions",
)
def list_staff_users(
    role: Optional[str] = Query(None, description="Filter by institutional role"),
    search: Optional[str] = Query(None, description="Search by username or email"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(require_any_permission("rbac:manage", "system:admin")),
):
    """List registered users with their assigned roles and computed effective capabilities."""
    users = RBACService.list_staff_users(
        conn,
        role=role,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [UserStaffOut(**u) for u in users]


@router.get(
    "/users/{user_id}",
    response_model=UserStaffOut,
    summary="Get detailed permissions profile for a user",
)
def get_user_permissions_profile(
    user_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(require_any_permission("rbac:manage", "system:admin")),
):
    """Retrieve user details and computed effective permissions."""
    users = RBACService.list_staff_users(conn, limit=1, offset=0)
    for u in users:
        if u["id"] == user_id:
            return UserStaffOut(**u)
    # If not found in limit=1, query specifically
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, username, email, role, status, faculty_id, student_id, custom_permissions, last_login, created_at
        FROM users WHERE id = ?;
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} does not exist.",
        )
    user_dict = dict(row)
    from src.core.security import get_user_permissions

    user_dict["effective_permissions"] = get_user_permissions(user_dict)
    return UserStaffOut(**user_dict)


@router.put(
    "/users/{user_id}/role",
    response_model=UserStaffOut,
    summary="Reassign user institutional role (Admin only)",
)
def update_user_role(
    user_id: int,
    data: UserRoleUpdate,
    conn: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(require_role("admin")),
):
    """Update a user's institutional role with security validation and audit trail."""
    try:
        user = RBACService.update_user_role(conn, user_id, data.role, admin_user)
        return UserStaffOut(**user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.put(
    "/users/{user_id}/permissions",
    response_model=UserStaffOut,
    summary="Customize user-level permissions (Admin only)",
)
def update_user_permissions(
    user_id: int,
    data: UserPermissionsUpdate,
    conn: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(require_role("admin")),
):
    """Assign or revoke specific functional permissions for an individual staff member."""
    try:
        user = RBACService.update_user_permissions(
            conn, user_id, data.custom_permissions, admin_user
        )
        return UserStaffOut(**user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/evaluate",
    response_model=PermissionEvaluationResult,
    summary="Simulate and test permission evaluation for a user",
)
def evaluate_user_permission(
    data: PermissionEvaluationRequest,
    conn: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(require_role("admin")),
):
    """Inspect and simulate whether a specific user is authorized to perform an action."""
    try:
        res = RBACService.evaluate_access(conn, data.user_id, data.permission)
        return PermissionEvaluationResult(**res)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
