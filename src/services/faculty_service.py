"""Faculty database service."""

import sqlite3
from datetime import date
from typing import Any, Dict, List, Optional

from src.database.connection import transaction
from src.models.faculty import FacultyCreate, FacultyUpdate


class FacultyService:
    @staticmethod
    def _generate_faculty_id(conn: sqlite3.Connection, dept_code: str) -> str:
        """Generate a sequential institutional faculty ID."""
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM faculty;")
        count = cursor.fetchone()["total"] + 1
        cursor.close()
        return f"FAC-{dept_code}-{count:03d}"

    @staticmethod
    def list_faculty(
        conn: sqlite3.Connection,
        department_id: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        query = """
            SELECT
                f.id, f.faculty_id, f.first_name, f.last_name, f.email, f.phone,
                f.department_id, f.designation, f.qualification, f.hire_date,
                f.status, f.created_at,
                d.name AS department_name, d.code AS department_code
            FROM faculty f
            JOIN departments d ON f.department_id = d.id
            WHERE 1=1
        """
        params: List[Any] = []

        if department_id:
            query += " AND f.department_id = ?"
            params.append(department_id)

        if status:
            query += " AND f.status = ?"
            params.append(status.upper())

        if search:
            query += """ AND (
                f.first_name LIKE ? OR
                f.last_name LIKE ? OR
                f.email LIKE ? OR
                f.faculty_id LIKE ? OR
                f.designation LIKE ?
            )"""
            term = f"%{search}%"
            params.extend([term, term, term, term, term])

        query += " ORDER BY f.id DESC;"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(conn: sqlite3.Connection, faculty_id: int) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                f.id, f.faculty_id, f.first_name, f.last_name, f.email, f.phone,
                f.department_id, f.designation, f.qualification, f.hire_date,
                f.status, f.created_at,
                d.name AS department_name, d.code AS department_code
            FROM faculty f
            JOIN departments d ON f.department_id = d.id
            WHERE f.id = ?;
            """,
            (faculty_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

    @staticmethod
    def create(conn: sqlite3.Connection, faculty_in: FacultyCreate) -> Dict[str, Any]:
        cursor = conn.cursor()
        cursor.execute("SELECT code FROM departments WHERE id = ?;", (faculty_in.department_id,))
        dept_row = cursor.fetchone()
        if not dept_row:
            cursor.close()
            raise ValueError(f"Department with ID {faculty_in.department_id} does not exist.")

        dept_code = dept_row["code"]
        faculty_id_code = FacultyService._generate_faculty_id(conn, dept_code)
        hire_date = faculty_in.hire_date or str(date.today())

        cursor.execute("SELECT id FROM faculty WHERE email = ?;", (faculty_in.email,))
        if cursor.fetchone():
            cursor.close()
            raise ValueError(f"Faculty with email '{faculty_in.email}' already exists.")

        with transaction(conn) as t_cursor:
            t_cursor.execute(
                """
                INSERT INTO faculty (
                    faculty_id, first_name, last_name, email, phone, department_id,
                    designation, qualification, hire_date, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    faculty_id_code,
                    faculty_in.first_name.strip(),
                    faculty_in.last_name.strip(),
                    faculty_in.email.strip().lower(),
                    faculty_in.phone,
                    faculty_in.department_id,
                    faculty_in.designation.strip(),
                    faculty_in.qualification,
                    hire_date,
                    faculty_in.status.upper(),
                ),
            )
            created_id = t_cursor.lastrowid

        return FacultyService.get_by_id(conn, created_id)

    @staticmethod
    def update(
        conn: sqlite3.Connection, faculty_id: int, faculty_up: FacultyUpdate
    ) -> Optional[Dict[str, Any]]:
        existing = FacultyService.get_by_id(conn, faculty_id)
        if not existing:
            return None

        update_dict = faculty_up.model_dump(exclude_unset=True)
        if not update_dict:
            return existing

        fields: List[str] = []
        values: List[Any] = []
        for key, val in update_dict.items():
            fields.append(f"{key} = ?")
            values.append(val)

        values.append(faculty_id)
        sql = f"UPDATE faculty SET {', '.join(fields)} WHERE id = ?;"

        with transaction(conn) as cursor:
            cursor.execute(sql, values)

        return FacultyService.get_by_id(conn, faculty_id)

    @staticmethod
    def delete(conn: sqlite3.Connection, faculty_id: int) -> bool:
        with transaction(conn) as cursor:
            cursor.execute("DELETE FROM faculty WHERE id = ?;", (faculty_id,))
            deleted = cursor.rowcount > 0
        return deleted

    @staticmethod
    def get_faculty_portal_data(
        conn: sqlite3.Connection, faculty_id: int
    ) -> Optional[Dict[str, Any]]:
        """Compile comprehensive workbench data for a faculty instructor."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                f.id, f.faculty_id, f.first_name, f.last_name, f.email, f.phone,
                f.department_id, f.designation, f.qualification, f.hire_date,
                f.status, f.created_at,
                d.name AS department_name, d.code AS department_code
            FROM faculty f
            JOIN departments d ON f.department_id = d.id
            WHERE f.id = ?;
            """,
            (faculty_id,),
        )
        faculty_row = cursor.fetchone()
        if not faculty_row:
            cursor.close()
            return None

        faculty_profile = dict(faculty_row)

        cursor.execute(
            """
            SELECT
                c.id, c.code, c.title, c.credits, c.semester, c.capacity,
                c.syllabus_summary, d.name AS department_name, d.code AS department_code,
                COUNT(ce.id) AS enrolled_count
            FROM courses c
            JOIN departments d ON c.department_id = d.id
            LEFT JOIN course_enrollments ce ON c.id = ce.course_id AND ce.status = 'ACTIVE'
            WHERE c.instructor_id = ?
            GROUP BY c.id
            ORDER BY c.semester ASC, c.code ASC;
            """,
            (faculty_id,),
        )
        courses = [dict(r) for r in cursor.fetchall()]

        course_ids = [c["id"] for c in courses]
        students: List[Dict[str, Any]] = []
        exams: List[Dict[str, Any]] = []
        attendance_logs: List[Dict[str, Any]] = []

        if course_ids:
            placeholders = ",".join("?" for _ in course_ids)

            cursor.execute(
                f"""
                SELECT
                    ce.id AS enrollment_id, ce.course_id, ce.academic_year, ce.semester AS enrollment_semester,
                    ce.status AS enrollment_status, ce.enrolled_at,
                    c.code AS course_code, c.title AS course_title,
                    s.id AS student_id, s.enrollment_no, s.first_name, s.last_name,
                    s.email, s.phone, s.current_semester,
                    d.name AS department_name
                FROM course_enrollments ce
                JOIN courses c ON ce.course_id = c.id
                JOIN students s ON ce.student_id = s.id
                JOIN departments d ON s.department_id = d.id
                WHERE ce.course_id IN ({placeholders})
                ORDER BY c.code ASC, s.last_name ASC, s.first_name ASC;
                """,
                course_ids,
            )
            students = [dict(r) for r in cursor.fetchall()]

            cursor.execute(
                f"""
                SELECT
                    e.id, e.course_id, e.title, e.exam_type, e.exam_date,
                    e.max_marks, e.passing_marks, e.weightage_percent,
                    c.code AS course_code, c.title AS course_title,
                    COUNT(er.id) AS evaluated_count
                FROM examinations e
                JOIN courses c ON e.course_id = c.id
                LEFT JOIN exam_results er ON e.id = er.exam_id
                WHERE e.course_id IN ({placeholders})
                GROUP BY e.id
                ORDER BY e.exam_date DESC;
                """,
                course_ids,
            )
            exams = [dict(r) for r in cursor.fetchall()]

            cursor.execute(
                f"""
                SELECT
                    ar.id, ar.course_id, ar.student_id, ar.attendance_date, ar.status, ar.remarks,
                    c.code AS course_code, c.title AS course_title,
                    s.enrollment_no, s.first_name, s.last_name
                FROM attendance_records ar
                JOIN courses c ON ar.course_id = c.id
                JOIN students s ON ar.student_id = s.id
                WHERE ar.course_id IN ({placeholders})
                ORDER BY ar.attendance_date DESC, ar.id DESC
                LIMIT 50;
                """,
                course_ids,
            )
            attendance_logs = [dict(r) for r in cursor.fetchall()]

        cursor.close()

        total_unique_students = len({s["student_id"] for s in students})

        return {
            "faculty": faculty_profile,
            "courses": courses,
            "students": students,
            "exams": exams,
            "attendance_logs": attendance_logs,
            "total_courses": len(courses),
            "total_students": total_unique_students,
            "total_exams": len(exams),
            "total_attendance_records": len(attendance_logs),
        }

