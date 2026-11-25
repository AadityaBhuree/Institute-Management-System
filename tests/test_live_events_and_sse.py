"""Automated test suite for Real-Time Server-Sent Events (SSE) & Pub/Sub Event Broker.
Validates stream protocols, audience role/user filtering, cross-thread dispatches,
RBAC authentication boundaries, and automated domain service dispatches.
"""

import threading

import pytest

from src.core.event_broker import EventBroker, event_broker
from src.core.security import create_session_token
from src.database.connection import get_connection, release_connection
from src.models.finance import PaymentCreate
from src.models.leave import LeaveRequestCreate, LeaveStatusUpdate
from src.models.notification import NotificationCreate
from src.services.finance_service import FinanceService
from src.services.leave_service import LeaveService
from src.services.notification_service import NotificationService


@pytest.fixture(autouse=True)
def clean_broker():
    """Ensure event broker is pristine before and after each test."""
    event_broker.clear()
    yield
    event_broker.clear()


# ============================================================================
# 1. Unit Tests for EventBroker Core Primitives
# ============================================================================


def test_event_broker_subscribe_and_unsubscribe():
    """Verify subscription registration and graceful unsubscribe cleanup."""
    broker = EventBroker()
    sub = broker.subscribe(channel="notifications", role="STUDENT", user_id=42)

    assert sub.id in broker._subscribers
    assert sub.channel == "notifications"
    assert sub.role == "STUDENT"
    assert sub.user_id == 42
    assert sub.queue.empty()

    telemetry = broker.get_telemetry()
    assert telemetry["active_subscribers"] == 1
    assert telemetry["channels"]["notifications"] == 1

    broker.unsubscribe(sub.id)
    assert sub.id not in broker._subscribers
    assert broker.get_telemetry()["active_subscribers"] == 0


def test_event_broker_format_sse_message():
    """Verify strict W3C Server-Sent Events (SSE) protocol serialization."""
    payload = {"alert": "Registration deadline", "code": 101}
    msg = EventBroker.format_sse_message(
        event="announcement",
        data=payload,
        event_id="evt-12345",
        retry_ms=3000,
    )

    assert "id: evt-12345\n" in msg
    assert "event: announcement\n" in msg
    assert "retry: 3000\n" in msg
    assert 'data: {"alert":"Registration deadline","code":101}\n\n' in msg


def test_event_broker_role_filtering():
    """Verify event routing delivers to appropriate recipient roles."""
    broker = EventBroker()
    admin_sub = broker.subscribe(channel="alerts", role="ADMIN", user_id=1)
    student_sub = broker.subscribe(channel="alerts", role="STUDENT", user_id=10)
    faculty_sub = broker.subscribe(channel="alerts", role="FACULTY", user_id=20)

    # 1. Target STUDENT specifically
    delivered = broker.publish(
        channel="alerts",
        event_type="exam_alert",
        data={"title": "Midterm Schedule"},
        target_role="STUDENT",
    )
    # Admin and Student both receive it, Faculty does not
    assert delivered == 2
    assert not student_sub.queue.empty()
    assert not admin_sub.queue.empty()
    assert faculty_sub.queue.empty()

    # Drain queues
    student_sub.queue.get_nowait()
    admin_sub.queue.get_nowait()

    # 2. Target ALL
    delivered = broker.publish(
        channel="alerts",
        event_type="campus_closure",
        data={"title": "Weather Alert"},
        target_role="ALL",
    )
    assert delivered == 3
    assert not student_sub.queue.empty()
    assert not admin_sub.queue.empty()
    assert not faculty_sub.queue.empty()


def test_event_broker_user_id_filtering():
    """Verify user-directed events are only delivered to the targeted user and administrators."""
    broker = EventBroker()
    admin_sub = broker.subscribe(channel="notifs", role="ADMIN", user_id=1)
    user_a_sub = broker.subscribe(channel="notifs", role="STUDENT", user_id=101)
    user_b_sub = broker.subscribe(channel="notifs", role="STUDENT", user_id=102)

    delivered = broker.publish(
        channel="notifs",
        event_type="grade_posted",
        data={"score": 95},
        target_role="STUDENT",
        target_user_id=101,
    )

    assert delivered == 2
    assert not user_a_sub.queue.empty()
    assert not admin_sub.queue.empty()
    assert user_b_sub.queue.empty()


def test_event_broker_queue_overflow_protection():
    """Verify queue drops oldest event when maxsize is exceeded without blocking or failing."""
    broker = EventBroker()
    sub = broker.subscribe(channel="test_chan", maxsize=2)

    broker.publish("test_chan", "msg1", {"seq": 1})
    broker.publish("test_chan", "msg2", {"seq": 2})
    broker.publish("test_chan", "msg3", {"seq": 3})

    assert sub.queue.qsize() == 2
    item1 = sub.queue.get_nowait()
    item2 = sub.queue.get_nowait()

    # Oldest (seq: 1) was evicted, only seq: 2 and seq: 3 remain
    assert "seq: 2" in item1 or '"seq":2' in item1
    assert "seq: 3" in item2 or '"seq":3' in item2


def test_event_broker_cross_thread_dispatch():
    """Verify publishing safely across secondary threads."""
    broker = EventBroker()
    sub = broker.subscribe(channel="threads")

    def worker_job():
        broker.publish(
            channel="threads",
            event_type="thread_ping",
            data={"status": "ok"},
        )

    t = threading.Thread(target=worker_job)
    t.start()
    t.join(timeout=2.0)

    assert not sub.queue.empty()
    item = sub.queue.get_nowait()
    assert "event: thread_ping" in item


# ============================================================================
# 2. REST & Server-Sent Events Endpoint Integration Tests
# ============================================================================


def test_notifications_stream_unauthorized(anon_client):
    """Verify connecting to notification stream without credentials returns 401."""
    response = anon_client.get("/api/notifications/stream")
    assert response.status_code == 401
    assert "Authentication required" in response.text


def test_notifications_stream_headers_and_handshake(student_client):
    """Verify SSE streaming headers and initial connected handshake event."""
    with student_client.stream("GET", "/api/notifications/stream?limit=1") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        assert "no-cache" in response.headers.get("cache-control", "")
        assert response.headers.get("x-accel-buffering") == "no"

        received = []
        for line in response.iter_lines():
            if line:
                received.append(line)

        full_text = "\n".join(received)
        assert "event: connected" in full_text
        assert "connected" in full_text
        assert "student" in full_text


def test_notifications_stream_query_token_auth(anon_client):
    """Verify EventSource client can authenticate via query parameter 'token'."""
    token = create_session_token(user_id=1, username="admin", role="admin")
    with anon_client.stream("GET", f"/api/notifications/stream?token={token}&limit=1") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        received = []
        for line in response.iter_lines():
            if line:
                received.append(line)

        full_text = "\n".join(received)
        assert "event: connected" in full_text
        assert "admin" in full_text


def test_system_telemetry_stream_forbidden_for_student(student_client):
    """Verify non-admin users cannot access system telemetry SSE stream."""
    response = student_client.get("/api/system/telemetry/stream")
    assert response.status_code == 403
    assert "Forbidden" in response.text


def test_system_telemetry_stream_admin_snapshot(client):
    """Verify administrators receive telemetry snapshot with DB, task, and broker stats."""
    with client.stream("GET", "/api/system/telemetry/stream?limit=1") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        received = []
        for line in response.iter_lines():
            if line:
                received.append(line)

        full_text = "\n".join(received)
        assert "event: telemetry_snapshot" in full_text
        assert "tasks" in full_text
        assert "broker" in full_text


# ============================================================================
# 3. Domain Event Dispatches & End-to-End Notification Integration
# ============================================================================


def test_domain_notification_dispatch_emits_sse_event():
    """Verify NotificationService.create triggers real-time SSE event emission."""
    sub = event_broker.subscribe(channel="notifications", role="STUDENT", user_id=99)
    conn = get_connection()
    try:
        payload = NotificationCreate(
            recipient_role="STUDENT",
            recipient_id=99,
            title="Dean's Honors List",
            message="Congratulations on securing a semester GPA of 3.92.",
            category="ACADEMIC",
            priority="HIGH",
            action_url="/portal",
        )
        notif = NotificationService.create(conn, payload)
        assert notif["id"] is not None

        # Verify event was queued to subscriber
        assert not sub.queue.empty()
        event_str = sub.queue.get_nowait()
        assert "event: notification" in event_str
        assert "Dean's Honors List" in event_str
        assert "portal" in event_str
    finally:
        release_connection(conn)


def test_leave_approval_dispatches_sse_and_inapp_notification():
    """Verify approving a leave application dispatches in-app notification & SSE event."""
    sub = event_broker.subscribe(channel="notifications", role="STUDENT", user_id=1)
    conn = get_connection()
    try:
        # Submit leave
        leave = LeaveService.submit_leave(
            conn,
            LeaveRequestCreate(
                applicant_type="STUDENT",
                applicant_id=1,
                applicant_name="Aditya Sharma",
                leave_type="SICK",
                start_date="2026-11-25",
                end_date="2026-11-27",
                reason="Viral fever recovery",
            ),
        )
        leave_id = leave["id"]

        # Approve leave
        updated = LeaveService.update_status(
            conn,
            leave_id,
            LeaveStatusUpdate(
                status="APPROVED",
                review_remarks="Approved by Medical Officer",
                reviewed_by="Dr. Verma",
            ),
        )
        assert updated["status"] == "APPROVED"

        # Check subscriber queue
        assert not sub.queue.empty()
        event_str = sub.queue.get_nowait()
        assert "event: notification" in event_str
        assert "Leave Request Approved" in event_str
        assert "Dr. Verma" in event_str
    finally:
        release_connection(conn)


def test_finance_payment_dispatches_sse_and_inapp_notification():
    """Verify recording fee payment generates receipt notification & real-time SSE event."""
    conn = get_connection()
    try:
        # Find an existing student and invoice
        cur = conn.cursor()
        cur.execute(
            "SELECT id, student_id, balance_amount FROM fee_invoices WHERE balance_amount > 0 LIMIT 1;"
        )
        row = cur.fetchone()
        cur.close()

        if row:
            invoice_id = row["id"]
            student_id = row["student_id"]
            pay_amount = min(50.0, float(row["balance_amount"]))

            sub = event_broker.subscribe(
                channel="notifications", role="STUDENT", user_id=student_id
            )

            payment = FinanceService.record_payment(
                conn,
                PaymentCreate(
                    invoice_id=invoice_id,
                    amount=pay_amount,
                    payment_method="CASH",
                    transaction_ref="TEST-TXN-SSE-01",
                    notes="Test SSE payment receipt dispatch",
                ),
            )
            assert payment["payment_no"] is not None

            assert not sub.queue.empty()
            event_str = sub.queue.get_nowait()
            assert "event: notification" in event_str
            assert "Payment Confirmed" in event_str
            assert f"${pay_amount:,.2f}" in event_str
    finally:
        release_connection(conn)
