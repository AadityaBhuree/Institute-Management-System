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

    @staticmethod
    def get_student_portal_dossier(
        conn: sqlite3.Connection, student_id: int
    ) -> Optional[Dict[str, Any]]:
        """Aggregate comprehensive scholar self-service portal dossier."""
        student = StudentService.get_by_id(conn, student_id)
        if not student:
            return None

        cursor = conn.cursor()

        # 1. Enrolled Courses
        cursor.execute(
            """
            SELECT
                ce.id AS enrollment_id, ce.enrolled_at AS enrollment_date, ce.status AS enrollment_status,
                c.id AS course_id, c.code AS course_code, c.title AS course_title,
                c.credits, c.semester,
                f.first_name AS instructor_first, f.last_name AS instructor_last,
                f.designation AS instructor_role
            FROM course_enrollments ce
            JOIN courses c ON ce.course_id = c.id
            LEFT JOIN faculty f ON c.instructor_id = f.id
            WHERE ce.student_id = ?
            ORDER BY c.semester ASC, c.code ASC;
            """,
            (student_id,),
        )
        enrollments = [dict(r) for r in cursor.fetchall()]
        total_credits = sum(e["credits"] for e in enrollments)

        # 2. Attendance Summary & Recent Logs
        cursor.execute(
            """
            SELECT
                status, COUNT(*) AS count
            FROM attendance_records
            WHERE student_id = ?
            GROUP BY status;
            """,
            (student_id,),
        )
        att_counts = {r["status"]: r["count"] for r in cursor.fetchall()}
        total_sessions = sum(att_counts.values())
        present_count = att_counts.get("PRESENT", 0)
        late_count = att_counts.get("LATE", 0)
        absent_count = att_counts.get("ABSENT", 0)
        excused_count = att_counts.get("EXCUSED", 0)

        effective_present = present_count + late_count
        attendance_pct = (
            round((effective_present / total_sessions) * 100, 1)
            if total_sessions > 0
            else 100.0
        )

        cursor.execute(
            """
            SELECT
                ar.id, ar.attendance_date AS date, ar.status, ar.remarks,
                c.code AS course_code, c.title AS course_title
            FROM attendance_records ar
            JOIN courses c ON ar.course_id = c.id
            WHERE ar.student_id = ?
            ORDER BY ar.attendance_date DESC
            LIMIT 10;
            """,
            (student_id,),
        )
        recent_attendance = [dict(r) for r in cursor.fetchall()]

        # 3. Examination Results & Grades
        cursor.execute(
            """
            SELECT
                er.id, er.marks_obtained, er.grade_letter AS letter_grade, er.remarks,
                e.title AS exam_title, e.exam_type, e.max_marks, e.exam_date AS exam_date,
                c.code AS course_code, c.title AS course_title
            FROM exam_results er
            JOIN examinations e ON er.exam_id = e.id
            JOIN courses c ON e.course_id = c.id
            WHERE er.student_id = ?
            ORDER BY e.exam_date DESC;
            """,
            (student_id,),
        )
        exam_results = []
        total_marks_obtained = 0.0
        total_max_marks = 0.0
        for r in cursor.fetchall():
            res_dict = dict(r)
            marks_ob = float(res_dict["marks_obtained"])
            max_m = float(res_dict["max_marks"])
            pct = round((marks_ob / max_m) * 100, 1) if max_m > 0 else 0.0
            res_dict["percentage"] = pct
            total_marks_obtained += marks_ob
            total_max_marks += max_m
            exam_results.append(res_dict)

        average_grade_pct = (
            round((total_marks_obtained / total_max_marks) * 100, 1)
            if total_max_marks > 0
            else 0.0
        )

        # 4. Fee Account & Payments
        cursor.execute(
            """
            SELECT
                id, invoice_no, title, term_name, total_amount, paid_amount, balance_amount,
                due_date, status, created_at
            FROM fee_invoices
            WHERE student_id = ?
            ORDER BY created_at DESC;
            """,
            (student_id,),
        )
        invoices = [dict(r) for r in cursor.fetchall()]
        total_invoiced = sum(float(i["total_amount"]) for i in invoices)
        total_paid = sum(float(i["paid_amount"]) for i in invoices)
        balance_outstanding = sum(float(i["balance_amount"]) for i in invoices)

        cursor.execute(
            """
            SELECT
                fp.id, fp.payment_no AS receipt_no, fp.amount AS amount_paid, fp.payment_method,
                fp.transaction_ref AS transaction_reference, fp.payment_date,
                fi.invoice_no
            FROM fee_payments fp
            JOIN fee_invoices fi ON fp.invoice_id = fi.id
            WHERE fi.student_id = ?
            ORDER BY fp.payment_date DESC;
            """,
            (student_id,),
        )
        payments = [dict(r) for r in cursor.fetchall()]

        cursor.close()

        return {
            "student": student,
            "enrollments": enrollments,
            "total_credits": total_credits,
            "attendance": {
                "total_sessions": total_sessions,
                "present_count": present_count,
                "late_count": late_count,
                "absent_count": absent_count,
                "excused_count": excused_count,
                "attendance_pct": attendance_pct,
                "is_low_attendance": attendance_pct < 75.0,
                "recent_logs": recent_attendance,
            },
            "academics": {
                "exam_results": exam_results,
                "exams_taken": len(exam_results),
                "average_grade_pct": average_grade_pct,
            },
            "finance": {
                "invoices": invoices,
                "payments": payments,
                "total_invoiced": total_invoiced,
                "total_paid": total_paid,
                "balance_outstanding": balance_outstanding,
                "is_settled": balance_outstanding <= 0.0,
            },
        }

