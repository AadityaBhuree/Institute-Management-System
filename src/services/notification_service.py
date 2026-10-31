"""Notification and Alert Dispatch Domain Service."""

import sqlite3
from typing import Any, Dict, List, Optional

from src.database.connection import transaction
from src.models.notification import NotificationCreate


class NotificationService:
    """Manages creation, query filtering, auto-dispatch triggers, and read lifecycle of notifications."""

    @staticmethod
    def create(conn: sqlite3.Connection, data: NotificationCreate) -> Dict[str, Any]:
        """Create and persist a new notification broadcast or targeted alert."""
        with transaction(conn) as cur:
            cur.execute(
                """
                INSERT INTO notifications (
                    recipient_role, recipient_id, title, message, category, priority, action_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    data.recipient_role,
                    data.recipient_id,
                    data.title,
                    data.message,
                    data.category,
                    data.priority,
                    data.action_url,
                ),
            )
            nid = cur.lastrowid
            cur.execute("SELECT * FROM notifications WHERE id = ?;", (nid,))
            row = cur.fetchone()
        return dict(row)

    @staticmethod
    def list_notifications(
        conn: sqlite3.Connection,
        recipient_role: Optional[str] = None,
        recipient_id: Optional[int] = None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List notifications matching target recipient role, ID, or general broadcasts."""
        query = "SELECT * FROM notifications WHERE 1=1"
        params: List[Any] = []

        if recipient_role:
            if recipient_id is not None:
                query += " AND (recipient_role = 'ALL' OR (recipient_role = ? AND (recipient_id IS NULL OR recipient_id = ?)))"
                params.extend([recipient_role, recipient_id])
            else:
                query += " AND (recipient_role = 'ALL' OR recipient_role = ?)"
                params.append(recipient_role)

        if unread_only:
            query += " AND is_read = 0"

        query += " ORDER BY created_at DESC LIMIT ?;"
        params.append(limit)

        cur = conn.cursor()
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]

    @staticmethod
    def mark_as_read(conn: sqlite3.Connection, notification_id: int) -> bool:
        """Mark an individual notification as read."""
        with transaction(conn) as cur:
            cur.execute(
                "UPDATE notifications SET is_read = 1 WHERE id = ?;",
                (notification_id,),
            )
            affected = cur.rowcount
        return affected > 0

    @staticmethod
    def mark_all_as_read(
        conn: sqlite3.Connection,
        recipient_role: Optional[str] = None,
        recipient_id: Optional[int] = None,
    ) -> int:
        """Mark all matching notifications as read."""
        query = "UPDATE notifications SET is_read = 1 WHERE is_read = 0"
        params: List[Any] = []

        if recipient_role:
            if recipient_id is not None:
                query += " AND (recipient_role = 'ALL' OR (recipient_role = ? AND (recipient_id IS NULL OR recipient_id = ?)))"
                params.extend([recipient_role, recipient_id])
            else:
                query += " AND (recipient_role = 'ALL' OR recipient_role = ?)"
                params.append(recipient_role)

        with transaction(conn) as cur:
            cur.execute(query, tuple(params))
            count = cur.rowcount
        return count

    @staticmethod
    def get_unread_count(
        conn: sqlite3.Connection,
        recipient_role: Optional[str] = None,
        recipient_id: Optional[int] = None,
    ) -> int:
        """Retrieve total count of unread notifications for a role/user."""
        query = "SELECT COUNT(*) AS total FROM notifications WHERE is_read = 0"
        params: List[Any] = []

        if recipient_role:
            if recipient_id is not None:
                query += " AND (recipient_role = 'ALL' OR (recipient_role = ? AND (recipient_id IS NULL OR recipient_id = ?)))"
                params.extend([recipient_role, recipient_id])
            else:
                query += " AND (recipient_role = 'ALL' OR recipient_role = ?)"
                params.append(recipient_role)

        cur = conn.cursor()
        cur.execute(query, tuple(params))
        row = cur.fetchone()
        cur.close()
        return row["total"] if row else 0

    # Auto-alert trigger helpers
    @staticmethod
    def dispatch_attendance_risk_alert(
        conn: sqlite3.Connection, student_id: int, student_name: str, attendance_pct: float
    ) -> Dict[str, Any]:
        """Dispatch attendance risk alert to student dossier."""
        payload = NotificationCreate(
            recipient_role="STUDENT",
            recipient_id=student_id,
            title="Attendance Risk Sentinel Alert",
            message=f"Urgent: Your institutional attendance has dropped to {attendance_pct:.1f}%, below the required 75% threshold.",
            category="ACADEMIC",
            priority="HIGH" if attendance_pct >= 65.0 else "URGENT",
            action_url=f"/portal?student_id={student_id}",
        )
        return NotificationService.create(conn, payload)

    @staticmethod
    def dispatch_overdue_invoice_alert(
        conn: sqlite3.Connection, student_id: int, invoice_no: str, balance: float
    ) -> Dict[str, Any]:
        """Dispatch overdue fee bursar notice."""
        payload = NotificationCreate(
            recipient_role="STUDENT",
            recipient_id=student_id,
            title="Bursar Fee Notice: Overdue Balance",
            message=f"Invoice {invoice_no} has an overdue outstanding balance of ${balance:,.2f}. Please clear dues to prevent registration hold.",
            category="FINANCE",
            priority="HIGH",
            action_url="/finance",
        )
        return NotificationService.create(conn, payload)
