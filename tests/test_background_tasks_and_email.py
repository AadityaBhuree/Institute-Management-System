"""Automated Test Suite for Institutional Email Dispatcher & Background Task Queue.
Tests worker thread execution, telemetry metrics, mock email backends,
Jinja2 transactional email rendering, domain event triggers, and RBAC endpoints.
"""

from unittest.mock import MagicMock

import pytest

from src.core.tasks import (
    enqueue_background_task,
    get_task_telemetry,
)
from src.database.connection import get_connection, release_connection
from src.models.leave import LeaveStatusUpdate
from src.services.email_service import (
    ConsoleEmailBackend,
    EmailService,
    MockEmailBackend,
)
from src.services.finance_service import FinanceService
from src.services.leave_service import LeaveService


@pytest.fixture(autouse=True)
def reset_mock_outbox():
    """Ensure mock email outbox is pristine before and after every test."""
    MockEmailBackend.clear_outbox()
    yield
    MockEmailBackend.clear_outbox()


def test_background_task_worker_execution():
    """Verify asynchronous task submission, worker execution, and telemetry tracking."""

    def sample_work(x: int, y: int) -> int:
        return x + y

    future = enqueue_background_task(sample_work, 15, 27)
    result = future.result(timeout=3.0)
    assert result == 42

    telemetry = get_task_telemetry()
    assert telemetry["queued_total"] >= 1
    assert telemetry["completed_total"] >= 1
    assert "active_pending" in telemetry
    assert telemetry["max_workers"] >= 1


def test_background_task_worker_handles_failure():
    """Verify background worker pool gracefully captures task exceptions in telemetry."""

    def failing_task():
        raise ValueError("Simulated catastrophic background task failure")

    future = enqueue_background_task(failing_task)
    with pytest.raises(ValueError, match="Simulated catastrophic"):
        future.result(timeout=3.0)

    telemetry = get_task_telemetry()
    assert telemetry["failed_total"] >= 1


def test_mock_and_console_email_backends():
    """Verify mock email backend registers outbox entries and console backend outputs."""
    backend = MockEmailBackend()
    res = backend.send(
        {
            "recipient": "dean@institute.edu",
            "subject": "Council Meeting",
            "body_text": "Agenda for tomorrow.",
        }
    )
    assert res["status"] == "SENT"
    assert len(MockEmailBackend.get_outbox()) == 1
    msg = MockEmailBackend.get_outbox()[0]
    assert msg["recipient"] == "dean@institute.edu"
    assert msg["subject"] == "Council Meeting"

    console_backend = ConsoleEmailBackend()
    c_res = console_backend.send(
        {
            "recipient": "provost@institute.edu",
            "sender": "ims@institute.edu",
            "subject": "Campus Protocol",
            "body_text": "All clear.",
        }
    )
    assert c_res["status"] == "SENT"


def test_email_service_send_email_and_db_logging():
    """Verify EmailService delivers message via backend and records audit row in database."""
    conn = get_connection()
    try:
        result = EmailService.send_email(
            recipient="scholar@institute.edu",
            subject="Academic Honors Nomination",
            body_text="Congratulations on your semester nomination.",
            body_html="<p>Congratulations on your semester nomination.</p>",
            template_name="honors_notice",
            conn=conn,
        )
        assert result["status"] == "SENT"
        assert result["recipient"] == "scholar@institute.edu"

        logs_resp = EmailService.list_email_logs(conn, recipient="scholar@institute.edu")
        assert logs_resp["total"] >= 1
        found = any(log["recipient"] == "scholar@institute.edu" for log in logs_resp["logs"])
        assert found is True
    finally:
        release_connection(conn)


def test_fee_receipt_email_template_rendering():
    """Verify Jinja2 fee receipt template renders with correct financial breakdown."""
    payment_data = {
        "receipt_number": "INV-2026-TEST",
        "invoice_id": 101,
        "invoice_number": "INV-2026-101",
        "amount_paid": 45000.0,
        "balance_after": 0.0,
        "payment_method": "ONLINE",
        "payment_date": "2026-11-05 10:00:00",
    }
    result = EmailService.send_fee_receipt_email(
        recipient="bursar_test@institute.edu",
        student_name="Aarav Sharma",
        payment_dict=payment_data,
        async_send=False,
    )
    assert result["status"] == "SENT"
    outbox = MockEmailBackend.get_outbox()
    assert len(outbox) >= 1
    sent = outbox[-1]
    assert "Aarav Sharma" in sent["body_html"]
    assert "INV-2026-101" in sent["body_html"] or "INV-2026-TEST" in sent["body_html"]
    assert "45000" in sent["body_html"] or "45,000" in sent["body_html"]


def test_leave_decision_email_template_rendering():
    """Verify Jinja2 leave petition determination template renders approved and rejected states."""
    # Test Approved
    leave_approved = {
        "id": 101,
        "leave_type": "MEDICAL",
        "status": "APPROVED",
        "start_date": "2026-11-10",
        "end_date": "2026-11-12",
        "review_remarks": "Approved upon medical slip verification.",
    }
    result_approved = EmailService.send_leave_decision_email(
        recipient="applicant_test@institute.edu",
        applicant_name="Priya Patel",
        leave_dict=leave_approved,
        async_send=False,
    )
    assert result_approved["status"] == "SENT"
    sent_appr = MockEmailBackend.get_outbox()[-1]
    assert "APPROVED" in sent_appr["body_html"]
    assert "Priya Patel" in sent_appr["body_html"]
    assert "Approved upon medical slip verification." in sent_appr["body_html"]

    # Test Rejected
    leave_rejected = {
        "id": 102,
        "leave_type": "CASUAL",
        "status": "REJECTED",
        "start_date": "2026-11-15",
        "end_date": "2026-11-16",
        "review_remarks": "Quota exhausted for current term.",
    }
    result_rejected = EmailService.send_leave_decision_email(
        recipient="applicant_test@institute.edu",
        applicant_name="Priya Patel",
        leave_dict=leave_rejected,
        async_send=False,
    )
    assert result_rejected["status"] == "SENT"
    sent_rej = MockEmailBackend.get_outbox()[-1]
    assert "REJECTED" in sent_rej["body_html"]
    assert "Quota exhausted for current term." in sent_rej["body_html"]


def test_attendance_alert_email_template_rendering():
    """Verify Jinja2 attendance sentinel alert renders low percentage threshold warning."""
    result = EmailService.send_attendance_alert_email(
        recipient="attendance_warn@institute.edu",
        student_name="Karan Verma",
        course_code="CS-401",
        course_title="Distributed Cloud Architectures",
        attended_sessions=14,
        total_sessions=20,
        attendance_percentage=70.0,
        async_send=False,
    )
    assert result["status"] == "SENT"
    sent = MockEmailBackend.get_outbox()[-1]
    assert "70.0%" in sent["body_html"]
    assert "Distributed Cloud Architectures" in sent["body_html"]
    assert "75%" in sent["body_html"] or "75.0%" in sent["body_html"]


def test_api_send_test_email_admin_success(client):
    """Verify POST /api/email/test allows admin to dispatch diagnostics email."""
    payload = {
        "recipient": "diagnostics@institute.edu",
        "subject": "System Health Check",
        "body_text": "Email dispatch subsystem operational.",
    }
    res = client.post("/api/email/test", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SENT"
    assert data["recipient"] == "diagnostics@institute.edu"


def test_api_send_test_email_student_forbidden(student_client):
    """Verify POST /api/email/test denies student access with HTTP 403."""
    payload = {"recipient": "hack@institute.edu", "subject": "Forbidden", "body_text": "Spam"}
    res = student_client.post("/api/email/test", json=payload)
    assert res.status_code == 403


def test_api_send_test_email_anon_unauthorized(anon_client):
    """Verify POST /api/email/test denies unauthenticated access with HTTP 401."""
    res = anon_client.post("/api/email/test", json={})
    assert res.status_code == 401


def test_api_email_logs_admin_and_filters(client):
    """Verify GET /api/email/logs allows admin to inspect delivery logs and pagination."""
    res = client.get("/api/email/logs?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "logs" in data
    assert isinstance(data["logs"], list)


def test_api_email_logs_student_forbidden(student_client):
    """Verify GET /api/email/logs denies student access with HTTP 403."""
    res = student_client.get("/api/email/logs")
    assert res.status_code == 403


def test_api_system_tasks_telemetry(client):
    """Verify GET /api/system/tasks returns worker queue telemetry metrics."""
    res = client.get("/api/system/tasks")
    assert res.status_code == 200
    telemetry = res.json()
    assert "max_workers" in telemetry
    assert "queued_total" in telemetry
    assert "completed_total" in telemetry
    assert "failed_total" in telemetry
    assert "active_pending" in telemetry


def test_finance_payment_dispatches_email_trigger():
    """Verify recording a fee payment queries student email and triggers receipt dispatch."""
    conn = get_connection()
    try:
        # Mock EmailService.send_fee_receipt_email to verify invocation
        original_send = EmailService.send_fee_receipt_email
        mock_dispatch = MagicMock(return_value={"status": "QUEUED"})
        EmailService.send_fee_receipt_email = mock_dispatch

        try:
            # Find an existing unpaid or partial invoice
            cur = conn.cursor()
            cur.execute("SELECT id FROM fee_invoices WHERE status != 'PAID' LIMIT 1")
            row = cur.fetchone()
            if row:
                inv_id = row[0]
                payment_data = {
                    "invoice_id": inv_id,
                    "amount": 500.0,
                    "payment_method": "ONLINE",
                    "transaction_reference": "TXN_TRIGGER_TEST_101",
                }
                FinanceService.record_payment(conn, payment_data)
                assert mock_dispatch.called
                args, kwargs = mock_dispatch.call_args
                assert kwargs.get("payment_dict") is not None
                assert kwargs.get("payment_dict")["amount_paid"] == 500.0
                assert kwargs.get("async_send") is True
        finally:
            EmailService.send_fee_receipt_email = original_send
    finally:
        release_connection(conn)


def test_leave_status_update_dispatches_email_trigger():
    """Verify approving or rejecting a leave petition queries applicant email and triggers dispatch."""
    conn = get_connection()
    try:
        original_send = EmailService.send_leave_decision_email
        mock_dispatch = MagicMock(return_value={"status": "QUEUED"})
        EmailService.send_leave_decision_email = mock_dispatch

        try:
            # Ensure a pending leave request exists
            cur = conn.cursor()
            cur.execute("SELECT id FROM leave_requests WHERE status = 'PENDING' LIMIT 1")
            row = cur.fetchone()
            if not row:
                cur.execute(
                    """
                    INSERT INTO leave_requests (applicant_type, applicant_id, applicant_name, leave_type, start_date, end_date, reason, status)
                    VALUES ('STUDENT', 1, 'John Doe', 'SICK', '2026-11-10', '2026-11-12', 'Viral Fever', 'PENDING')
                    """
                )
                conn.commit()
                leave_id = cur.lastrowid
            else:
                leave_id = row[0]

            update_payload = LeaveStatusUpdate(
                status="APPROVED",
                review_remarks="Approved after medical documentation verified.",
                reviewed_by="Dean",
            )
            LeaveService.update_status(
                conn,
                leave_id=leave_id,
                data=update_payload,
            )
            assert mock_dispatch.called
            args, kwargs = mock_dispatch.call_args
            assert kwargs.get("leave_dict") is not None
            assert kwargs.get("leave_dict")["id"] == leave_id
            assert kwargs.get("async_send") is True
        finally:
            EmailService.send_leave_decision_email = original_send
    finally:
        release_connection(conn)
