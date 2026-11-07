"""Institutional Email & Background Task Queue REST API Router."""

import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from src.core.security import require_role
from src.core.tasks import get_task_telemetry
from src.database.connection import get_db
from src.models.email import EmailDeliveryResult, EmailLogListResponse, EmailSendRequest
from src.services.auth_service import AuthService
from src.services.email_service import EmailService

router = APIRouter(tags=["Email & Tasks"])


@router.post(
    "/api/email/test",
    response_model=EmailDeliveryResult,
    status_code=status.HTTP_200_OK,
)
def send_test_email(
    payload: Optional[EmailSendRequest] = None,
    conn: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(require_role("admin")),
):
    """Dispatch a test email to verify active email transport backend (Admin only)."""
    recipient = payload.recipient if payload else "admin@institute.edu"
    subject = payload.subject if payload else "IMS System Diagnostics: Email Dispatch Verification"
    body_text = (
        payload.body_text
        if payload
        else "This is an automated test message dispatched by the IMS Email & Background Task Engine."
    )

    result = EmailService.send_email(
        recipient=recipient,
        subject=subject,
        body_text=body_text,
        body_html=payload.body_html if payload else None,
        template_name="system_test",
        conn=conn,
    )

    AuthService.log_audit(
        conn,
        action="EMAIL_TEST_DISPATCH",
        resource="email",
        resource_id=result.get("message_id"),
        user_id=admin_user.get("id"),
        username=admin_user.get("username"),
        details=f"Dispatched test email to {recipient} (status={result.get('status')})",
    )
    return result


@router.get(
    "/api/email/logs",
    response_model=EmailLogListResponse,
)
def list_email_logs(
    recipient: Optional[str] = Query(default=None, description="Filter by recipient email"),
    delivery_status: Optional[str] = Query(
        default=None, alias="status", description="Filter by status (SENT, MOCKED, FAILED)"
    ),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    conn: sqlite3.Connection = Depends(get_db),
    admin_user: dict = Depends(require_role("admin")),
):
    """Retrieve paginated institutional email dispatch audit logs (Admin only)."""
    return EmailService.list_email_logs(
        conn=conn,
        recipient=recipient,
        status=delivery_status,
        limit=limit,
        offset=offset,
    )


@router.get("/api/system/tasks")
def get_background_task_telemetry(
    admin_user: dict = Depends(require_role("admin")),
):
    """Inspect background worker queue execution telemetry and thread metrics (Admin only)."""
    return get_task_telemetry()
