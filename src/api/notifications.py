"""Notification and Institutional Alert Broadcasts API Router."""

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.core.security import get_current_user, require_role
from src.database.connection import get_db
from src.models.notification import NotificationCreate, NotificationOut
from src.services.auth_service import AuthService
from src.services.notification_service import NotificationService

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationOut])
def list_notifications(
    role: Optional[str] = Query(None, description="Filter by recipient role (ALL, STUDENT, etc.)"),
    recipient_id: Optional[int] = Query(None, description="Filter by recipient ID"),
    unread_only: bool = Query(False, description="Filter unread notifications only"),
    limit: int = Query(50, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Retrieve notifications filtered by target audience or recipient."""
    # Default to current user's role if not explicitly specified
    target_role = role or current_user.get("role", "ALL").upper()
    return NotificationService.list_notifications(
        conn,
        recipient_role=target_role,
        recipient_id=recipient_id,
        unread_only=unread_only,
        limit=limit,
    )


@router.get("/unread-count")
def get_unread_count(
    role: Optional[str] = Query(None),
    recipient_id: Optional[int] = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get the current count of unread notifications."""
    target_role = role or current_user.get("role", "ALL").upper()
    count = NotificationService.get_unread_count(
        conn, recipient_role=target_role, recipient_id=recipient_id
    )
    return {"unread_count": count}


@router.post("", response_model=NotificationOut, status_code=status.HTTP_201_CREATED)
def create_notification(
    data: NotificationCreate,
    conn: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(require_role("admin")),
):
    """Broadcast a new notification or directed alert (Admin only)."""
    result = NotificationService.create(conn, data)
    AuthService.log_audit(
        conn,
        action="NOTIFICATION_BROADCAST",
        resource="notifications",
        resource_id=str(result.get("id")),
        user_id=admin_user.get("id"),
        username=admin_user.get("username"),
        details=f"Dispatched {data.category} notification: {data.title}",
    )
    return result


@router.put("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Mark a notification as read."""
    success = NotificationService.mark_as_read(conn, notification_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )
    return {"status": "SUCCESS", "notification_id": notification_id, "is_read": True}


@router.put("/read-all")
def mark_all_read(
    role: Optional[str] = Query(None),
    recipient_id: Optional[int] = Query(None),
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Mark all notifications matching recipient as read."""
    target_role = role or current_user.get("role", "ALL").upper()
    affected = NotificationService.mark_all_as_read(
        conn, recipient_role=target_role, recipient_id=recipient_id
    )
    return {"status": "SUCCESS", "marked_read_count": affected}
