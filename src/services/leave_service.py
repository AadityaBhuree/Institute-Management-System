"""Institutional Leave Management Service."""

import logging
import sqlite3
from typing import Dict, List, Optional

from src.database.connection import transaction
from src.models.leave import LeaveRequestCreate, LeaveStatusUpdate


class LeaveService:
    @staticmethod
    def list_leaves(
        conn: sqlite3.Connection,
        applicant_type: Optional[str] = None,
        status: Optional[str] = None,
        applicant_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[dict]:
        """Retrieve leave applications matching criteria."""
        query = """
            SELECT id, applicant_type, applicant_id, applicant_name, leave_type,
                   start_date, end_date, reason, status, review_remarks, reviewed_by, created_at
            FROM leave_requests
            WHERE 1=1
        """
        params = []

        if applicant_type:
            query += " AND applicant_type = ?"
            params.append(applicant_type)

        if status:
            query += " AND status = ?"
            params.append(status)

        if applicant_id:
            query += " AND applicant_id = ?"
            params.append(applicant_id)

        if search:
            query += " AND (applicant_name LIKE ? OR reason LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term])

        # Pending first, then newest
        query += """
            ORDER BY
                CASE status
                    WHEN 'PENDING' THEN 1
                    WHEN 'APPROVED' THEN 2
                    ELSE 3
                END,
                created_at DESC;
        """

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(conn: sqlite3.Connection, leave_id: int) -> Optional[dict]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, applicant_type, applicant_id, applicant_name, leave_type,
                   start_date, end_date, reason, status, review_remarks, reviewed_by, created_at
            FROM leave_requests
            WHERE id = ?;
            """,
            (leave_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

    @staticmethod
    def submit_leave(conn: sqlite3.Connection, data: LeaveRequestCreate) -> dict:
        with transaction(conn) as cursor:
            cursor.execute(
                """
                INSERT INTO leave_requests (
                    applicant_type, applicant_id, applicant_name, leave_type,
                    start_date, end_date, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    data.applicant_type,
                    data.applicant_id,
                    data.applicant_name.strip(),
                    data.leave_type,
                    data.start_date,
                    data.end_date,
                    data.reason.strip(),
                ),
            )
            leave_id = cursor.lastrowid
        return LeaveService.get_by_id(conn, leave_id)

    @staticmethod
    def update_status(
        conn: sqlite3.Connection, leave_id: int, data: LeaveStatusUpdate
    ) -> Optional[dict]:
        with transaction(conn) as cursor:
            cursor.execute(
                """
                UPDATE leave_requests
                SET status = ?, review_remarks = ?, reviewed_by = ?
                WHERE id = ?;
                """,
                (
                    data.status,
                    data.review_remarks.strip() if data.review_remarks else None,
                    data.reviewed_by.strip() if data.reviewed_by else "Admin",
                    leave_id,
                ),
            )
        updated_leave = LeaveService.get_by_id(conn, leave_id)
        if updated_leave:
            try:
                from src.services.email_service import EmailService

                applicant_type = updated_leave.get("applicant_type", "STUDENT")
                applicant_id = updated_leave.get("applicant_id")
                recipient_email = None

                cur = conn.cursor()
                if applicant_type == "STUDENT":
                    cur.execute("SELECT email FROM students WHERE id = ?;", (applicant_id,))
                    row = cur.fetchone()
                    if row:
                        recipient_email = row["email"]
                elif applicant_type == "FACULTY":
                    cur.execute("SELECT email FROM faculty WHERE id = ?;", (applicant_id,))
                    row = cur.fetchone()
                    if row:
                        recipient_email = row["email"]
                cur.close()

                if not recipient_email:
                    clean_name = updated_leave["applicant_name"].lower().replace(" ", ".")
                    recipient_email = f"{clean_name}@institute.edu"

                EmailService.send_leave_decision_email(
                    recipient=recipient_email,
                    applicant_name=updated_leave["applicant_name"],
                    leave_dict=updated_leave,
                    async_send=True,
                )
            except Exception as e:
                logging.getLogger("ims").warning("Failed to queue leave decision email: %s", e)

        return updated_leave

    @staticmethod
    def get_leave_stats(conn: sqlite3.Connection) -> Dict[str, int]:
        """Aggregate leave requests counts."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) AS approved,
                SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) AS rejected,
                SUM(CASE WHEN applicant_type = 'STUDENT' THEN 1 ELSE 0 END) AS students,
                SUM(CASE WHEN applicant_type = 'FACULTY' THEN 1 ELSE 0 END) AS faculty
            FROM leave_requests;
        """)
        row = cursor.fetchone()
        cursor.close()
        return {
            "total": row["total"] or 0,
            "pending": row["pending"] or 0,
            "approved": row["approved"] or 0,
            "rejected": row["rejected"] or 0,
            "students": row["students"] or 0,
            "faculty": row["faculty"] or 0,
        }
