"""Test suite for Phase 10: Database Schema Migrations and Institutional Notifications Engine."""

import sqlite3
from fastapi.testclient import TestClient

from src.database.connection import get_connection, release_connection
from src.database.migration_manager import MigrationManager
from src.models.notification import NotificationCreate
from src.services.notification_service import NotificationService


def test_migration_manager_lifecycle(setup_test_db):
    """Verify MigrationManager initializes tables, tracks versions, and executes migrations."""
    conn = get_connection(setup_test_db)
    try:
        # Table init
        MigrationManager.init_migration_table(conn)
        status = MigrationManager.get_status(conn)
        assert "current_version" in status
        assert "applied_count" in status
        assert "pending_count" in status

        # Run any pending migrations
        applied = MigrationManager.run_pending_migrations(conn)
        assert isinstance(applied, list)

        # Re-check status
        new_status = MigrationManager.get_status(conn)
        assert new_status["pending_count"] == 0
    finally:
        release_connection(conn, setup_test_db)


def test_api_system_migrations_endpoints(client: TestClient):
    """Verify GET and POST migration endpoints with admin authentication."""
    # Status endpoint
    res_status = client.get("/api/system/migrations")
    assert res_status.status_code == 200
    data = res_status.json()
    assert "current_version" in data
    assert "applied_count" in data

    # Migrate endpoint
    res_migrate = client.post("/api/system/migrate")
    assert res_migrate.status_code == 200
    migrate_data = res_migrate.json()
    assert "applied" in migrate_data
    assert "total_applied" in migrate_data


def test_notification_service_crud_and_lifecycle(setup_test_db):
    """Verify creating, listing, unread-counting, and marking notifications as read."""
    conn = get_connection(setup_test_db)
    try:
        # Create broadcast notification
        notif_in = NotificationCreate(
            recipient_role="ALL",
            title="Campus-wide Announcement",
            message="Library will remain open until midnight during final exam week.",
            category="ACADEMIC",
            priority="NORMAL",
            action_url="/library",
        )
        created = NotificationService.create(conn, notif_in)
        assert created["id"] > 0
        assert created["is_read"] == 0
        assert created["title"] == "Campus-wide Announcement"

        # List notifications
        all_notifs = NotificationService.list_notifications(conn, recipient_role="ALL")
        assert any(n["id"] == created["id"] for n in all_notifs)

        # Unread count
        unread = NotificationService.get_unread_count(conn, recipient_role="ALL")
        assert unread >= 1

        # Mark single as read
        marked = NotificationService.mark_as_read(conn, created["id"])
        assert marked is True

        # Verify read state
        notifs_after = NotificationService.list_notifications(conn, recipient_role="ALL", unread_only=True)
        assert not any(n["id"] == created["id"] for n in notifs_after)
    finally:
        release_connection(conn, setup_test_db)


def test_notification_auto_dispatch_triggers(setup_test_db):
    """Verify automated trigger dispatchers for low attendance sentinel and overdue fee notices."""
    conn = get_connection(setup_test_db)
    try:
        # Attendance trigger
        att_alert = NotificationService.dispatch_attendance_risk_alert(
            conn, student_id=1, student_name="Alice Smith", attendance_pct=68.5
        )
        assert att_alert["recipient_role"] == "STUDENT"
        assert att_alert["recipient_id"] == 1
        assert "Attendance Risk Sentinel Alert" in att_alert["title"]
        assert att_alert["priority"] == "HIGH"

        # Overdue fee trigger
        fee_alert = NotificationService.dispatch_overdue_invoice_alert(
            conn, student_id=1, invoice_no="INV-2026-0042", balance=1250.00
        )
        assert fee_alert["recipient_role"] == "STUDENT"
        assert fee_alert["recipient_id"] == 1
        assert "Bursar Fee Notice" in fee_alert["title"]
        assert fee_alert["priority"] == "HIGH"
    finally:
        release_connection(conn, setup_test_db)


def test_notifications_rest_api_flows(client: TestClient):
    """Verify REST API listing, unread count, mark-read, mark-all-read, and creation."""
    # List notifications
    res_list = client.get("/api/notifications")
    assert res_list.status_code == 200
    assert isinstance(res_list.json(), list)

    # Unread count
    res_count = client.get("/api/notifications/unread-count")
    assert res_count.status_code == 200
    assert "unread_count" in res_count.json()

    # Create new notification via API
    payload = {
        "recipient_role": "STUDENT",
        "title": "Semester Registration Deadline",
        "message": "Final date for semester course add/drop is Friday 5 PM.",
        "category": "ACADEMIC",
        "priority": "HIGH",
        "action_url": "/courses",
    }
    res_create = client.post("/api/notifications", json=payload)
    assert res_create.status_code == 201
    created_item = res_create.json()
    notif_id = created_item["id"]

    # Mark as read
    res_read = client.put(f"/api/notifications/{notif_id}/read")
    assert res_read.status_code == 200
    assert res_read.json()["is_read"] is True

    # Mark all read
    res_all_read = client.put("/api/notifications/read-all")
    assert res_all_read.status_code == 200
    assert res_all_read.json()["status"] == "SUCCESS"


def test_notifications_html_page_view(client: TestClient):
    """Verify HTML rendering of institutional notifications alert center."""
    res_html = client.get("/notifications", headers={"Accept": "text/html"})
    assert res_html.status_code == 200
    assert "text/html" in res_html.headers["content-type"]
    html = res_html.text
    assert "Notifications & Alert Dispatch Center" in html
    assert "Target Audience" in html
    assert "Broadcast Alert" in html
