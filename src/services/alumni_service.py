"""Alumni Network & Career Mentorship Hub Service."""

import sqlite3
from typing import Any, Dict, List, Optional

from src.database.connection import transaction
from src.models.alumni import (
    AlumniMemberCreate,
    AlumniMentorshipRequestCreate,
    AlumniMentorshipStatusUpdate,
)


class AlumniService:
    @staticmethod
    def list_alumni(
        conn: sqlite3.Connection,
        department_id: Optional[int] = None,
        graduation_year: Optional[int] = None,
        mentorship_status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[dict]:
        query = """
            SELECT a.id, a.student_id, a.full_name, a.email, a.phone,
                   a.graduation_year, a.degree, a.department_id, a.current_company,
                   a.job_title, a.city, a.linkedin_url, a.mentorship_status, a.created_at,
                   d.name AS department_name, d.code AS department_code,
                   COUNT(m.id) AS mentorship_requests_count
            FROM alumni_members a
            JOIN departments d ON a.department_id = d.id
            LEFT JOIN alumni_mentorship_requests m ON a.id = m.alumni_id
            WHERE 1=1
        """
        params = []
        if department_id:
            query += " AND a.department_id = ?"
            params.append(department_id)
        if graduation_year:
            query += " AND a.graduation_year = ?"
            params.append(graduation_year)
        if mentorship_status:
            query += " AND a.mentorship_status = ?"
            params.append(mentorship_status)
        if search:
            term = f"%{search.strip()}%"
            query += " AND (a.full_name LIKE ? OR a.current_company LIKE ? OR a.job_title LIKE ? OR a.city LIKE ?)"
            params.extend([term, term, term, term])

        query += " GROUP BY a.id ORDER BY a.graduation_year DESC, a.full_name ASC;"
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_alumnus_by_id(conn: sqlite3.Connection, alumni_id: int) -> Optional[dict]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT a.*, d.name AS department_name, d.code AS department_code
            FROM alumni_members a
            JOIN departments d ON a.department_id = d.id
            WHERE a.id = ?;
            """,
            (alumni_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

    @staticmethod
    def register_alumnus(conn: sqlite3.Connection, data: AlumniMemberCreate) -> dict:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM alumni_members WHERE email = ?;",
            (data.email.strip().lower(),),
        )
        if cursor.fetchone():
            cursor.close()
            raise ValueError(f"Alumnus with email '{data.email}' is already registered.")

        cursor.execute("SELECT id FROM departments WHERE id = ?;", (data.department_id,))
        if not cursor.fetchone():
            cursor.close()
            raise ValueError(f"Department ID {data.department_id} not found.")
        cursor.close()

        with transaction(conn) as cur:
            cur.execute(
                """
                INSERT INTO alumni_members (
                    student_id, full_name, email, phone, graduation_year, degree,
                    department_id, current_company, job_title, city, linkedin_url,
                    mentorship_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    data.student_id,
                    data.full_name.strip(),
                    data.email.strip().lower(),
                    data.phone.strip() if data.phone else None,
                    data.graduation_year,
                    data.degree.strip(),
                    data.department_id,
                    data.current_company.strip(),
                    data.job_title.strip(),
                    data.city.strip(),
                    data.linkedin_url.strip() if data.linkedin_url else None,
                    data.mentorship_status,
                ),
            )
            alumni_id = cur.lastrowid

        return AlumniService.get_alumnus_by_id(conn, alumni_id)  # type: ignore

    @staticmethod
    def request_mentorship(conn: sqlite3.Connection, data: AlumniMentorshipRequestCreate) -> dict:
        alumnus = AlumniService.get_alumnus_by_id(conn, data.alumni_id)
        if not alumnus:
            raise ValueError(f"Alumnus ID {data.alumni_id} not found.")

        if alumnus["mentorship_status"] != "AVAILABLE":
            raise ValueError(
                f"Mentor '{alumnus['full_name']}' is currently not accepting mentorship requests ({alumnus['mentorship_status']})."
            )

        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, first_name, last_name FROM students WHERE id = ?;",
            (data.student_id,),
        )
        student = cursor.fetchone()
        if not student:
            cursor.close()
            raise ValueError(f"Student ID {data.student_id} not found.")

        cursor.execute(
            """
            SELECT id FROM alumni_mentorship_requests
            WHERE alumni_id = ? AND student_id = ? AND status IN ('REQUESTED', 'ACCEPTED');
            """,
            (data.alumni_id, data.student_id),
        )
        if cursor.fetchone():
            cursor.close()
            raise ValueError(
                f"Candidate already has an active mentorship request with {alumnus['full_name']}."
            )
        cursor.close()

        with transaction(conn) as cur:
            cur.execute(
                """
                INSERT INTO alumni_mentorship_requests (
                    alumni_id, student_id, mentorship_topic, status, notes
                ) VALUES (?, ?, ?, 'REQUESTED', ?);
                """,
                (
                    data.alumni_id,
                    data.student_id,
                    data.mentorship_topic.strip(),
                    data.notes.strip() if data.notes else None,
                ),
            )
            request_id = cur.lastrowid

        requests = AlumniService.list_mentorship_requests(conn)
        for r in requests:
            if r["id"] == request_id:
                return r
        return {"id": request_id, "status": "REQUESTED"}

    @staticmethod
    def update_mentorship_status(
        conn: sqlite3.Connection,
        request_id: int,
        data: AlumniMentorshipStatusUpdate,
    ) -> dict:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM alumni_mentorship_requests WHERE id = ?;",
            (request_id,),
        )
        if not cursor.fetchone():
            cursor.close()
            raise ValueError(f"Mentorship request ID {request_id} not found.")
        cursor.close()

        with transaction(conn) as cur:
            cur.execute(
                """
                UPDATE alumni_mentorship_requests
                SET status = ?, notes = COALESCE(?, notes)
                WHERE id = ?;
                """,
                (data.status, data.notes, request_id),
            )

        requests = AlumniService.list_mentorship_requests(conn)
        for r in requests:
            if r["id"] == request_id:
                return r
        return {"id": request_id, "status": data.status}

    @staticmethod
    def list_mentorship_requests(
        conn: sqlite3.Connection,
        alumni_id: Optional[int] = None,
        student_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[dict]:
        query = """
            SELECT m.id, m.alumni_id, m.student_id, m.mentorship_topic, m.status,
                   m.notes, m.created_at,
                   a.full_name AS alumni_name, a.current_company AS alumni_company, a.job_title AS alumni_job_title,
                   s.first_name || ' ' || s.last_name AS student_name, s.enrollment_no, d.code AS department_code
            FROM alumni_mentorship_requests m
            JOIN alumni_members a ON m.alumni_id = a.id
            JOIN students s ON m.student_id = s.id
            JOIN departments d ON s.department_id = d.id
            WHERE 1=1
        """
        params = []
        if alumni_id:
            query += " AND m.alumni_id = ?"
            params.append(alumni_id)
        if student_id:
            query += " AND m.student_id = ?"
            params.append(student_id)
        if status:
            query += " AND m.status = ?"
            params.append(status)

        query += " ORDER BY m.created_at DESC;"
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_stats(conn: sqlite3.Connection) -> Dict[str, Any]:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(id) FROM alumni_members;")
        total_alumni = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(id) FROM alumni_members WHERE mentorship_status = 'AVAILABLE';"
        )
        available_mentors = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT graduation_year) FROM alumni_members;")
        batches_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(id) FROM alumni_mentorship_requests WHERE status IN ('REQUESTED', 'ACCEPTED');"
        )
        active_mentorships = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(id) FROM alumni_mentorship_requests WHERE status = 'COMPLETED';"
        )
        completed_mentorships = cursor.fetchone()[0]
        cursor.close()

        return {
            "total_alumni": total_alumni,
            "available_mentors": available_mentors,
            "graduating_batches_count": batches_count,
            "active_mentorships": active_mentorships,
            "completed_mentorships": completed_mentorships,
        }
