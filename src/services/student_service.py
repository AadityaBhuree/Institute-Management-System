"""Student and admissions database service."""

import sqlite3
from datetime import date
from typing import Any, Dict, List, Optional

from src.database.connection import transaction
from src.models.student import StudentCreate, StudentUpdate


class StudentService:
    @staticmethod
    def _generate_enrollment_no(conn: sqlite3.Connection, dept_code: str) -> str:
        """Generate a sequential institutional enrollment number."""
        current_year = date.today().year
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM students;")
        count = cursor.fetchone()["total"] + 1
        cursor.close()
        return f"IMS-{current_year}-{dept_code}-{count:04d}"

    @staticmethod
    def list_students(
        conn: sqlite3.Connection,
        department_id: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        query = """
            SELECT
                s.id, s.enrollment_no, s.first_name, s.last_name, s.email, s.phone,
                s.dob, s.gender, s.blood_group, s.address, s.emergency_contact,
                s.department_id, s.current_semester, s.admission_date, s.status, s.created_at,
                d.name AS department_name, d.code AS department_code
            FROM students s
            JOIN departments d ON s.department_id = d.id
            WHERE 1=1
        """
        params: List[Any] = []

        if department_id:
            query += " AND s.department_id = ?"
            params.append(department_id)

        if status:
            query += " AND s.status = ?"
            params.append(status.upper())

        if search:
            query += """ AND (
                s.first_name LIKE ? OR
                s.last_name LIKE ? OR
                s.email LIKE ? OR
                s.enrollment_no LIKE ?
            )"""
            term = f"%{search}%"
            params.extend([term, term, term, term])

        query += " ORDER BY s.id DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(conn: sqlite3.Connection, student_id: int) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                s.id, s.enrollment_no, s.first_name, s.last_name, s.email, s.phone,
                s.dob, s.gender, s.blood_group, s.address, s.emergency_contact,
                s.department_id, s.current_semester, s.admission_date, s.status, s.created_at,
                d.name AS department_name, d.code AS department_code
            FROM students s
            JOIN departments d ON s.department_id = d.id
            WHERE s.id = ?;
            """,
            (student_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

    @staticmethod
    def create(conn: sqlite3.Connection, student_in: StudentCreate) -> Dict[str, Any]:
        cursor = conn.cursor()
        # Verify department exists
        cursor.execute("SELECT code FROM departments WHERE id = ?;", (student_in.department_id,))
        dept_row = cursor.fetchone()
        if not dept_row:
            cursor.close()
            raise ValueError(f"Department with ID {student_in.department_id} does not exist.")

        dept_code = dept_row["code"]
        enrollment_no = StudentService._generate_enrollment_no(conn, dept_code)
        admission_date = student_in.admission_date or str(date.today())

        # Check for unique email
        cursor.execute("SELECT id FROM students WHERE email = ?;", (student_in.email,))
        if cursor.fetchone():
            cursor.close()
            raise ValueError(f"Student with email '{student_in.email}' is already registered.")

        with transaction(conn) as t_cursor:
            t_cursor.execute(
                """
                INSERT INTO students (
                    enrollment_no, first_name, last_name, email, phone, dob, gender,
                    blood_group, address, emergency_contact, department_id,
                    current_semester, admission_date, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    enrollment_no,
                    student_in.first_name.strip(),
                    student_in.last_name.strip(),
                    student_in.email.strip().lower(),
                    student_in.phone,
                    student_in.dob,
                    student_in.gender,
                    student_in.blood_group,
                    student_in.address,
                    student_in.emergency_contact,
                    student_in.department_id,
                    student_in.current_semester,
                    admission_date,
                    student_in.status.upper(),
                ),
            )
            student_id = t_cursor.lastrowid

        return StudentService.get_by_id(conn, student_id)

    @staticmethod
    def update(
        conn: sqlite3.Connection, student_id: int, student_up: StudentUpdate
    ) -> Optional[Dict[str, Any]]:
        existing = StudentService.get_by_id(conn, student_id)
        if not existing:
            return None

        update_dict = student_up.model_dump(exclude_unset=True)
        if not update_dict:
            return existing

        fields: List[str] = []
        values: List[Any] = []
        for key, val in update_dict.items():
            fields.append(f"{key} = ?")
            values.append(val)

        values.append(student_id)
        sql = f"UPDATE students SET {', '.join(fields)} WHERE id = ?;"

        with transaction(conn) as cursor:
            cursor.execute(sql, values)

        return StudentService.get_by_id(conn, student_id)

    @staticmethod
    def delete(conn: sqlite3.Connection, student_id: int) -> bool:
        with transaction(conn) as cursor:
            cursor.execute("DELETE FROM students WHERE id = ?;", (student_id,))
            deleted = cursor.rowcount > 0
        return deleted

    @staticmethod
    def get_stats(conn: sqlite3.Connection) -> Dict[str, Any]:
        cursor = conn.cursor()
        cursor.execute("SELECT status, COUNT(*) AS count FROM students GROUP BY status;")
        status_counts = {r["status"]: r["count"] for r in cursor.fetchall()}
        cursor.close()
        return status_counts
