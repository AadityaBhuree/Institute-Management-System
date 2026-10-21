"""Course catalog and enrollment database service."""

import sqlite3
from typing import Any, Dict, List, Optional

from src.database.connection import transaction
from src.models.course import CourseCreate, CourseUpdate, EnrollmentCreate


class CourseService:
    @staticmethod
    def list_courses(
        conn: sqlite3.Connection,
        department_id: Optional[int] = None,
        semester: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        query = """
            SELECT
                c.id, c.code, c.title, c.department_id, c.credits, c.semester,
                c.capacity, c.syllabus_summary, c.instructor_id, c.created_at,
                d.name AS department_name, d.code AS department_code,
                (f.first_name || ' ' || f.last_name) AS instructor_name,
                (SELECT COUNT(*) FROM course_enrollments e
                 WHERE e.course_id = c.id AND e.status = 'ACTIVE') AS enrolled_count
            FROM courses c
            JOIN departments d ON c.department_id = d.id
            LEFT JOIN faculty f ON c.instructor_id = f.id
            WHERE 1=1
        """
        params: List[Any] = []

        if department_id:
            query += " AND c.department_id = ?"
            params.append(department_id)

        if semester:
            query += " AND c.semester = ?"
            params.append(semester)

        if search:
            query += " AND (c.code LIKE ? OR c.title LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term])

        query += " ORDER BY c.semester ASC, c.code ASC;"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(conn: sqlite3.Connection, course_id: int) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                c.id, c.code, c.title, c.department_id, c.credits, c.semester,
                c.capacity, c.syllabus_summary, c.instructor_id, c.created_at,
                d.name AS department_name, d.code AS department_code,
                (f.first_name || ' ' || f.last_name) AS instructor_name,
                (SELECT COUNT(*) FROM course_enrollments e
                 WHERE e.course_id = c.id AND e.status = 'ACTIVE') AS enrolled_count
            FROM courses c
            JOIN departments d ON c.department_id = d.id
            LEFT JOIN faculty f ON c.instructor_id = f.id
            WHERE c.id = ?;
            """,
            (course_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

    @staticmethod
    def create(conn: sqlite3.Connection, course_in: CourseCreate) -> Dict[str, Any]:
        cursor = conn.cursor()
        # Verify unique course code
        cursor.execute("SELECT id FROM courses WHERE code = ?;", (course_in.code.upper(),))
        if cursor.fetchone():
            cursor.close()
            raise ValueError(f"Course code '{course_in.code.upper()}' is already in use.")

        # Verify department exists
        cursor.execute("SELECT id FROM departments WHERE id = ?;", (course_in.department_id,))
        if not cursor.fetchone():
            cursor.close()
            raise ValueError(f"Department ID {course_in.department_id} does not exist.")

        # Verify instructor exists if provided
        if course_in.instructor_id:
            cursor.execute("SELECT id FROM faculty WHERE id = ?;", (course_in.instructor_id,))
            if not cursor.fetchone():
                cursor.close()
                raise ValueError(f"Instructor ID {course_in.instructor_id} does not exist.")

        with transaction(conn) as t_cursor:
            t_cursor.execute(
                """
                INSERT INTO courses (
                    code, title, department_id, credits, semester, capacity,
                    syllabus_summary, instructor_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    course_in.code.upper().strip(),
                    course_in.title.strip(),
                    course_in.department_id,
                    course_in.credits,
                    course_in.semester,
                    course_in.capacity,
                    course_in.syllabus_summary,
                    course_in.instructor_id,
                ),
            )
            created_id = t_cursor.lastrowid

        return CourseService.get_by_id(conn, created_id)

    @staticmethod
    def update(
        conn: sqlite3.Connection, course_id: int, course_up: CourseUpdate
    ) -> Optional[Dict[str, Any]]:
        existing = CourseService.get_by_id(conn, course_id)
        if not existing:
            return None

        update_dict = course_up.model_dump(exclude_unset=True)
        if not update_dict:
            return existing

        fields: List[str] = []
        values: List[Any] = []
        for key, val in update_dict.items():
            if key == "code" and val:
                val = val.upper().strip()
            fields.append(f"{key} = ?")
            values.append(val)

        values.append(course_id)
        sql = f"UPDATE courses SET {', '.join(fields)} WHERE id = ?;"

        with transaction(conn) as cursor:
            cursor.execute(sql, values)

        return CourseService.get_by_id(conn, course_id)

    @staticmethod
    def assign_instructor(
        conn: sqlite3.Connection, course_id: int, instructor_id: Optional[int]
    ) -> Optional[Dict[str, Any]]:
        if instructor_id:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM faculty WHERE id = ?;", (instructor_id,))
            if not cursor.fetchone():
                cursor.close()
                raise ValueError(f"Faculty ID {instructor_id} not found.")
            cursor.close()

        with transaction(conn) as cursor:
            cursor.execute(
                "UPDATE courses SET instructor_id = ? WHERE id = ?;",
                (instructor_id, course_id),
            )

        return CourseService.get_by_id(conn, course_id)

    @staticmethod
    def enroll_student(conn: sqlite3.Connection, en_in: EnrollmentCreate) -> Dict[str, Any]:
        cursor = conn.cursor()
        # Verify student exists
        cursor.execute(
            "SELECT id, first_name, last_name FROM students WHERE id = ?;", (en_in.student_id,)
        )
        student = cursor.fetchone()
        if not student:
            cursor.close()
            raise ValueError(f"Student ID {en_in.student_id} not found.")

        # Verify course exists & check capacity
        cursor.execute(
            """
            SELECT c.id, c.code, c.capacity,
                (SELECT COUNT(*) FROM course_enrollments
                 WHERE course_id = c.id AND status = 'ACTIVE') AS enrolled
            FROM courses c WHERE c.id = ?;
            """,
            (en_in.course_id,),
        )
        course = cursor.fetchone()
        if not course:
            cursor.close()
            raise ValueError(f"Course ID {en_in.course_id} not found.")

        if course["enrolled"] >= course["capacity"]:
            cursor.close()
            code = course["code"]
            cap = course["capacity"]
            raise ValueError(f"Course {code} has reached maximum capacity ({cap} seats).")

        # Check existing enrollment
        cursor.execute(
            """
            SELECT id FROM course_enrollments
            WHERE student_id = ? AND course_id = ? AND academic_year = ? AND semester = ?;
            """,
            (en_in.student_id, en_in.course_id, en_in.academic_year, en_in.semester),
        )
        if cursor.fetchone():
            cursor.close()
            raise ValueError("Student is already enrolled in this course for the selected term.")

        with transaction(conn) as t_cursor:
            t_cursor.execute(
                """
                INSERT INTO course_enrollments (
                    student_id, course_id, academic_year, semester, status
                ) VALUES (?, ?, ?, ?, 'ACTIVE');
                """,
                (en_in.student_id, en_in.course_id, en_in.academic_year, en_in.semester),
            )
            en_id = t_cursor.lastrowid

        return {
            "id": en_id,
            "student_id": en_in.student_id,
            "student_name": f"{student['first_name']} {student['last_name']}",
            "course_id": en_in.course_id,
            "course_code": course["code"],
            "academic_year": en_in.academic_year,
            "semester": en_in.semester,
            "status": "ACTIVE",
        }

    @staticmethod
    def list_course_students(conn: sqlite3.Connection, course_id: int) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                s.id, s.enrollment_no, s.first_name, s.last_name, s.email,
                e.enrolled_at, e.status
            FROM course_enrollments e
            JOIN students s ON e.student_id = s.id
            WHERE e.course_id = ?
            ORDER BY s.last_name ASC, s.first_name ASC;
            """,
            (course_id,),
        )
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def delete(conn: sqlite3.Connection, course_id: int) -> bool:
        with transaction(conn) as cursor:
            cursor.execute("DELETE FROM courses WHERE id = ?;", (course_id,))
            deleted = cursor.rowcount > 0
        return deleted
