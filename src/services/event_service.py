"""Campus Events, Seminars & Symposium Hub Service."""

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.database.connection import transaction
from src.models.event import (
    EventCreate,
    EventRegistrationCreate,
)


class EventService:
    @staticmethod
    def _generate_event_code(conn: sqlite3.Connection, event_date: str) -> str:
        """Generate unique event code: EVT-YYYY-XXXX."""
        try:
            year = datetime.strptime(event_date, "%Y-%m-%d").year
        except ValueError:
            year = datetime.now().year

        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM events WHERE event_code LIKE ?;",
            (f"EVT-{year}-%",),
        )
        count = cursor.fetchone()["cnt"] + 1
        cursor.close()

        code = f"EVT-{year}-{count:04d}"
        # Ensure uniqueness
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM events WHERE event_code = ?;", (code,))
        while cursor.fetchone():
            count += 1
            code = f"EVT-{year}-{count:04d}"
            cursor.execute("SELECT id FROM events WHERE event_code = ?;", (code,))
        cursor.close()
        return code

    @staticmethod
    def _generate_reg_number(conn: sqlite3.Connection, event_id: int) -> str:
        """Generate unique registration number: REG-EVT-XXXX-YYYY."""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM event_registrations WHERE event_id = ?;",
            (event_id,),
        )
        count = cursor.fetchone()["cnt"] + 1
        cursor.close()

        reg_num = f"REG-EVT-{event_id:03d}-{count:04d}"
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM event_registrations WHERE registration_number = ?;",
            (reg_num,),
        )
        while cursor.fetchone():
            count += 1
            reg_num = f"REG-EVT-{event_id:03d}-{count:04d}"
            cursor.execute(
                "SELECT id FROM event_registrations WHERE registration_number = ?;",
                (reg_num,),
            )
        cursor.close()
        return reg_num

    @staticmethod
    def list_events(
        conn: sqlite3.Connection,
        category: Optional[str] = None,
        status: Optional[str] = None,
        department_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List campus events with registration count, attended count, and available seats."""
        query = """
            SELECT e.id, e.event_code, e.title, e.category, e.department_id,
                   e.organizer_faculty_id, e.venue, e.event_date, e.start_time, e.end_time,
                   e.max_capacity, e.registration_fee, e.status, e.description, e.created_at,
                   d.name AS department_name,
                   (f.first_name || ' ' || f.last_name) AS organizer_name,
                   COALESCE(r.reg_cnt, 0) AS registered_count,
                   COALESCE(r.att_cnt, 0) AS attended_count,
                   MAX(0, e.max_capacity - COALESCE(r.reg_cnt, 0)) AS available_seats
            FROM events e
            LEFT JOIN departments d ON e.department_id = d.id
            LEFT JOIN faculty f ON e.organizer_faculty_id = f.id
            LEFT JOIN (
                SELECT event_id,
                       COUNT(CASE WHEN status != 'CANCELLED' THEN 1 END) AS reg_cnt,
                       COUNT(CASE WHEN status = 'ATTENDED' THEN 1 END) AS att_cnt
                FROM event_registrations
                GROUP BY event_id
            ) r ON e.id = r.event_id
            WHERE 1=1
        """
        params: List[Any] = []
        if category:
            query += " AND e.category = ?"
            params.append(category)
        if status:
            query += " AND e.status = ?"
            params.append(status)
        if department_id:
            query += " AND e.department_id = ?"
            params.append(department_id)
        if search:
            query += " AND (e.title LIKE ? OR e.venue LIKE ? OR e.event_code LIKE ?)"
            s = f"%{search.strip()}%"
            params.extend([s, s, s])

        query += " ORDER BY e.event_date ASC, e.start_time ASC;"
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_event_by_id(conn: sqlite3.Connection, event_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve single event details with organizer and registration stats."""
        query = """
            SELECT e.id, e.event_code, e.title, e.category, e.department_id,
                   e.organizer_faculty_id, e.venue, e.event_date, e.start_time, e.end_time,
                   e.max_capacity, e.registration_fee, e.status, e.description, e.created_at,
                   d.name AS department_name,
                   (f.first_name || ' ' || f.last_name) AS organizer_name,
                   COALESCE(r.reg_cnt, 0) AS registered_count,
                   COALESCE(r.att_cnt, 0) AS attended_count,
                   MAX(0, e.max_capacity - COALESCE(r.reg_cnt, 0)) AS available_seats
            FROM events e
            LEFT JOIN departments d ON e.department_id = d.id
            LEFT JOIN faculty f ON e.organizer_faculty_id = f.id
            LEFT JOIN (
                SELECT event_id,
                       COUNT(CASE WHEN status != 'CANCELLED' THEN 1 END) AS reg_cnt,
                       COUNT(CASE WHEN status = 'ATTENDED' THEN 1 END) AS att_cnt
                FROM event_registrations
                WHERE event_id = ?
                GROUP BY event_id
            ) r ON e.id = r.event_id
            WHERE e.id = ?;
        """
        cursor = conn.cursor()
        cursor.execute(query, (event_id, event_id))
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

    @staticmethod
    def create_event(conn: sqlite3.Connection, data: EventCreate) -> Dict[str, Any]:
        """Create a new institutional event."""
        # Validate time ordering
        if data.start_time >= data.end_time:
            raise ValueError(
                f"Start time ({data.start_time}) must be earlier than end time ({data.end_time})."
            )

        # Validate department if provided
        cursor = conn.cursor()
        if data.department_id:
            cursor.execute("SELECT id FROM departments WHERE id = ?;", (data.department_id,))
            if not cursor.fetchone():
                cursor.close()
                raise ValueError(f"Department #{data.department_id} not found.")

        # Validate faculty organizer if provided
        if data.organizer_faculty_id:
            cursor.execute("SELECT id FROM faculty WHERE id = ?;", (data.organizer_faculty_id,))
            if not cursor.fetchone():
                cursor.close()
                raise ValueError(f"Faculty #{data.organizer_faculty_id} not found.")
        cursor.close()

        event_code = EventService._generate_event_code(conn, data.event_date)

        with transaction(conn) as cur:
            cur.execute(
                """
                INSERT INTO events (
                    event_code, title, category, department_id, organizer_faculty_id,
                    venue, event_date, start_time, end_time, max_capacity,
                    registration_fee, status, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    event_code,
                    data.title.strip(),
                    data.category,
                    data.department_id,
                    data.organizer_faculty_id,
                    data.venue.strip(),
                    data.event_date,
                    data.start_time,
                    data.end_time,
                    data.max_capacity,
                    data.registration_fee,
                    data.status,
                    data.description.strip() if data.description else None,
                ),
            )
            event_id = cur.lastrowid

        return EventService.get_event_by_id(conn, event_id)  # type: ignore

    @staticmethod
    def update_event_status(
        conn: sqlite3.Connection, event_id: int, new_status: str
    ) -> Dict[str, Any]:
        """Update event status (UPCOMING, ACTIVE, COMPLETED, CANCELLED)."""
        valid_statuses = ("UPCOMING", "ACTIVE", "COMPLETED", "CANCELLED")
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of {valid_statuses}.")

        event = EventService.get_event_by_id(conn, event_id)
        if not event:
            raise ValueError(f"Event #{event_id} not found.")

        with transaction(conn) as cur:
            cur.execute("UPDATE events SET status = ? WHERE id = ?;", (new_status, event_id))

        return EventService.get_event_by_id(conn, event_id)  # type: ignore

    @staticmethod
    def register_for_event(
        conn: sqlite3.Connection, data: EventRegistrationCreate
    ) -> Dict[str, Any]:
        """Register a student for a campus event with capacity and duplicate check."""
        event = EventService.get_event_by_id(conn, data.event_id)
        if not event:
            raise ValueError(f"Event #{data.event_id} not found.")

        if event["status"] in ("COMPLETED", "CANCELLED"):
            raise ValueError(f"Cannot register for an event with status '{event['status']}'.")

        cursor = conn.cursor()
        cursor.execute("SELECT id, status FROM students WHERE id = ?;", (data.student_id,))
        student = cursor.fetchone()
        if not student:
            cursor.close()
            raise ValueError(f"Student #{data.student_id} not found.")

        if student["status"] in ("WITHDRAWN", "SUSPENDED"):
            cursor.close()
            raise ValueError(
                f"Student status is '{student['status']}'; inactive students cannot register."
            )

        # Check existing registration
        cursor.execute(
            """
            SELECT id, status FROM event_registrations
            WHERE event_id = ? AND student_id = ?;
            """,
            (data.event_id, data.student_id),
        )
        existing = cursor.fetchone()
        if existing:
            cursor.close()
            if existing["status"] == "CANCELLED":
                # Reactivate registration
                with transaction(conn) as cur:
                    cur.execute(
                        "UPDATE event_registrations SET status = 'REGISTERED' WHERE id = ?;",
                        (existing["id"],),
                    )
                return EventService.get_registration_by_id(conn, existing["id"])  # type: ignore
            raise ValueError(f"Student #{data.student_id} is already registered for this event.")

        # Check capacity
        cursor.execute(
            """
            SELECT COUNT(*) AS cnt FROM event_registrations
            WHERE event_id = ? AND status != 'CANCELLED';
            """,
            (data.event_id,),
        )
        active_count = cursor.fetchone()["cnt"]
        cursor.close()

        if active_count >= event["max_capacity"]:
            raise ValueError(
                f"Event '{event['title']}' has reached its maximum capacity of {event['max_capacity']} attendees."
            )

        reg_number = EventService._generate_reg_number(conn, data.event_id)

        with transaction(conn) as cur:
            cur.execute(
                """
                INSERT INTO event_registrations (
                    event_id, student_id, registration_number, status, certificate_issued
                ) VALUES (?, ?, ?, 'REGISTERED', 0);
                """,
                (data.event_id, data.student_id, reg_number),
            )
            reg_id = cur.lastrowid

        return EventService.get_registration_by_id(conn, reg_id)  # type: ignore

    @staticmethod
    def get_registration_by_id(conn: sqlite3.Connection, reg_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve single registration details with event and student joins."""
        query = """
            SELECT r.id, r.event_id, r.student_id, r.registration_number,
                   r.status, r.certificate_issued, r.attendance_marked_at, r.created_at,
                   e.title AS event_title, e.event_code,
                   (s.first_name || ' ' || s.last_name) AS student_name,
                   s.enrollment_no, d.code AS department_code
            FROM event_registrations r
            JOIN events e ON r.event_id = e.id
            JOIN students s ON r.student_id = s.id
            JOIN departments d ON s.department_id = d.id
            WHERE r.id = ?;
        """
        cursor = conn.cursor()
        cursor.execute(query, (reg_id,))
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

    @staticmethod
    def update_registration_status(
        conn: sqlite3.Connection,
        reg_id: int,
        status: Optional[str] = None,
        certificate_issued: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Update attendance status and/or certificate issuance for a registration."""
        reg = EventService.get_registration_by_id(conn, reg_id)
        if not reg:
            raise ValueError(f"Registration #{reg_id} not found.")

        updates: List[str] = []
        params: List[Any] = []

        if status:
            valid_statuses = ("REGISTERED", "ATTENDED", "CANCELLED")
            if status not in valid_statuses:
                raise ValueError(f"Invalid status '{status}'. Must be one of {valid_statuses}.")
            updates.append("status = ?")
            params.append(status)
            if status == "ATTENDED":
                updates.append("attendance_marked_at = CURRENT_TIMESTAMP")

        if certificate_issued is not None:
            if certificate_issued not in (0, 1):
                raise ValueError("certificate_issued must be 0 or 1.")
            updates.append("certificate_issued = ?")
            params.append(certificate_issued)

        if not updates:
            return reg

        params.append(reg_id)
        sql = f"UPDATE event_registrations SET {', '.join(updates)} WHERE id = ?;"

        with transaction(conn) as cur:
            cur.execute(sql, params)

        return EventService.get_registration_by_id(conn, reg_id)  # type: ignore

    @staticmethod
    def list_registrations(
        conn: sqlite3.Connection,
        event_id: Optional[int] = None,
        student_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List event registrations with student and event metadata."""
        query = """
            SELECT r.id, r.event_id, r.student_id, r.registration_number,
                   r.status, r.certificate_issued, r.attendance_marked_at, r.created_at,
                   e.title AS event_title, e.event_code,
                   (s.first_name || ' ' || s.last_name) AS student_name,
                   s.enrollment_no, d.code AS department_code
            FROM event_registrations r
            JOIN events e ON r.event_id = e.id
            JOIN students s ON r.student_id = s.id
            JOIN departments d ON s.department_id = d.id
            WHERE 1=1
        """
        params: List[Any] = []
        if event_id:
            query += " AND r.event_id = ?"
            params.append(event_id)
        if student_id:
            query += " AND r.student_id = ?"
            params.append(student_id)
        if status:
            query += " AND r.status = ?"
            params.append(status)

        query += " ORDER BY r.created_at DESC LIMIT ?;"
        params.append(limit)

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_stats(conn: sqlite3.Connection) -> Dict[str, Any]:
        """Aggregate campus event statistics and registration counts."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_events,
                COUNT(CASE WHEN status = 'UPCOMING' THEN 1 END) AS upcoming_events,
                COUNT(CASE WHEN status IN ('ACTIVE', 'COMPLETED') THEN 1 END) AS active_or_completed_events
            FROM events;
            """
        )
        evt_stats = cursor.fetchone()

        cursor.execute(
            """
            SELECT
                COUNT(CASE WHEN status != 'CANCELLED' THEN 1 END) AS total_registrations,
                COUNT(CASE WHEN status = 'ATTENDED' THEN 1 END) AS total_attended,
                COUNT(CASE WHEN certificate_issued = 1 THEN 1 END) AS total_certificates_issued
            FROM event_registrations;
            """
        )
        reg_stats = cursor.fetchone()
        cursor.close()

        return {
            "total_events": evt_stats["total_events"] if evt_stats else 0,
            "upcoming_events": evt_stats["upcoming_events"] if evt_stats else 0,
            "active_or_completed_events": (
                evt_stats["active_or_completed_events"] if evt_stats else 0
            ),
            "total_registrations": reg_stats["total_registrations"] if reg_stats else 0,
            "total_attended": reg_stats["total_attended"] if reg_stats else 0,
            "total_certificates_issued": (
                reg_stats["total_certificates_issued"] if reg_stats else 0
            ),
        }
