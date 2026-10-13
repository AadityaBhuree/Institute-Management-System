"""Academics database service for attendance tracking and examination evaluations."""

import sqlite3
from typing import Any, Dict, List, Optional

from src.database.connection import transaction
from src.models.academics import AttendanceBatchMark, ExamCreate, ExamGradeBatchSubmit


def calculate_grade_letter(marks_obtained: float, max_marks: float) -> str:
    """Calculate standard academic letter grade from percentage."""
    if max_marks <= 0:
        return "F"
    percentage = (marks_obtained / max_marks) * 100.0
    if percentage >= 90.0:
        return "A+"
    if percentage >= 80.0:
        return "A"
    if percentage >= 70.0:
        return "B"
    if percentage >= 60.0:
        return "C"
    if percentage >= 50.0:
        return "D"
    return "F"


class AcademicsService:
    @staticmethod
    def mark_attendance_batch(
        conn: sqlite3.Connection, batch_in: AttendanceBatchMark
    ) -> Dict[str, Any]:
        cursor = conn.cursor()
        # Verify course exists
        cursor.execute("SELECT code FROM courses WHERE id = ?;", (batch_in.course_id,))
        course_row = cursor.fetchone()
        if not course_row:
            cursor.close()
            raise ValueError(f"Course ID {batch_in.course_id} does not exist.")

        recorded_count = 0
        with transaction(conn) as t_cursor:
            for rec in batch_in.records:
                # Upsert attendance on duplicate (student_id, course_id, attendance_date)
                t_cursor.execute(
                    """
                    INSERT INTO attendance_records (
                        student_id, course_id, attendance_date, status, remarks, recorded_by
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(student_id, course_id, attendance_date) DO UPDATE
                    SET status = excluded.status,
                        remarks = excluded.remarks,
                        recorded_by = excluded.recorded_by;
                    """,
                    (
                        rec.student_id,
                        batch_in.course_id,
                        batch_in.attendance_date,
                        rec.status.upper(),
                        rec.remarks,
                        batch_in.recorded_by,
                    ),
                )
                recorded_count += 1

        return {
            "course_id": batch_in.course_id,
            "course_code": course_row["code"],
            "attendance_date": batch_in.attendance_date,
            "records_marked": recorded_count,
        }

    @staticmethod
    def get_attendance_records(
        conn: sqlite3.Connection,
        course_id: int,
        attendance_date: Optional[str] = None,
        student_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        query = """
            SELECT
                a.id, a.student_id, a.course_id, a.attendance_date, a.status, a.remarks,
                (s.first_name || ' ' || s.last_name) AS student_name, s.enrollment_no,
                c.code AS course_code, c.title AS course_title
            FROM attendance_records a
            JOIN students s ON a.student_id = s.id
            JOIN courses c ON a.course_id = c.id
            WHERE a.course_id = ?
        """
        params: List[Any] = [course_id]

        if attendance_date:
            query += " AND a.attendance_date = ?"
            params.append(attendance_date)

        if student_id:
            query += " AND a.student_id = ?"
            params.append(student_id)

        query += " ORDER BY s.last_name ASC, a.attendance_date DESC;"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_student_attendance_summary(
        conn: sqlite3.Connection, student_id: int
    ) -> Dict[str, Any]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_classes,
                SUM(CASE WHEN status = 'PRESENT' THEN 1 ELSE 0 END) AS present_count,
                SUM(CASE WHEN status = 'ABSENT' THEN 1 ELSE 0 END) AS absent_count,
                SUM(CASE WHEN status = 'LATE' THEN 1 ELSE 0 END) AS late_count,
                SUM(CASE WHEN status = 'EXCUSED' THEN 1 ELSE 0 END) AS excused_count
            FROM attendance_records
            WHERE student_id = ?;
            """,
            (student_id,),
        )
        row = cursor.fetchone()
        cursor.close()

        total = row["total_classes"] or 0
        present = row["present_count"] or 0
        percentage = round((present / total * 100), 1) if total > 0 else 100.0

        return {
            "student_id": student_id,
            "total_classes": total,
            "present_count": present,
            "absent_count": row["absent_count"] or 0,
            "late_count": row["late_count"] or 0,
            "excused_count": row["excused_count"] or 0,
            "attendance_percentage": percentage,
            "is_short_attendance": percentage < 75.0,
        }

    @staticmethod
    def create_examination(conn: sqlite3.Connection, exam_in: ExamCreate) -> Dict[str, Any]:
        cursor = conn.cursor()
        cursor.execute("SELECT code, title FROM courses WHERE id = ?;", (exam_in.course_id,))
        course = cursor.fetchone()
        if not course:
            cursor.close()
            raise ValueError(f"Course ID {exam_in.course_id} does not exist.")

        with transaction(conn) as t_cursor:
            t_cursor.execute(
                """
                INSERT INTO examinations (
                    course_id, title, exam_type, exam_date,
                    max_marks, passing_marks, weightage_percent
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    exam_in.course_id,
                    exam_in.title.strip(),
                    exam_in.exam_type.upper(),
                    exam_in.exam_date,
                    exam_in.max_marks,
                    exam_in.passing_marks,
                    exam_in.weightage_percent,
                ),
            )
            exam_id = t_cursor.lastrowid

        return AcademicsService.get_exam_by_id(conn, exam_id)

    @staticmethod
    def get_exam_by_id(conn: sqlite3.Connection, exam_id: int) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                e.id, e.course_id, e.title, e.exam_type, e.exam_date, e.max_marks,
                e.passing_marks, e.weightage_percent, e.created_at,
                c.code AS course_code, c.title AS course_title,
                (SELECT COUNT(*) FROM exam_results r WHERE r.exam_id = e.id) AS graded_count
            FROM examinations e
            JOIN courses c ON e.course_id = c.id
            WHERE e.id = ?;
            """,
            (exam_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

    @staticmethod
    def list_examinations(
        conn: sqlite3.Connection,
        course_id: Optional[int] = None,
        exam_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        query = """
            SELECT
                e.id, e.course_id, e.title, e.exam_type, e.exam_date, e.max_marks,
                e.passing_marks, e.weightage_percent, e.created_at,
                c.code AS course_code, c.title AS course_title,
                (SELECT COUNT(*) FROM exam_results r WHERE r.exam_id = e.id) AS graded_count
            FROM examinations e
            JOIN courses c ON e.course_id = c.id
            WHERE 1=1
        """
        params: List[Any] = []

        if course_id:
            query += " AND e.course_id = ?"
            params.append(course_id)

        if exam_type:
            query += " AND e.exam_type = ?"
            params.append(exam_type.upper())

        query += " ORDER BY e.exam_date DESC, e.id DESC;"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def submit_exam_grades_batch(
        conn: sqlite3.Connection, exam_id: int, grade_in: ExamGradeBatchSubmit
    ) -> Dict[str, Any]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, max_marks FROM examinations WHERE id = ?;", (exam_id,))
        exam = cursor.fetchone()
        if not exam:
            cursor.close()
            raise ValueError(f"Examination ID {exam_id} not found.")

        max_marks = float(exam["max_marks"])
        graded_count = 0

        with transaction(conn) as t_cursor:
            for g in grade_in.grades:
                if g.marks_obtained > max_marks:
                    raise ValueError(
                        f"Marks {g.marks_obtained} cannot exceed maximum marks ({max_marks})."
                    )

                grade_letter = calculate_grade_letter(g.marks_obtained, max_marks)

                t_cursor.execute(
                    """
                    INSERT INTO exam_results (
                        exam_id, student_id, marks_obtained, grade_letter, remarks
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(exam_id, student_id) DO UPDATE
                    SET marks_obtained = excluded.marks_obtained,
                        grade_letter = excluded.grade_letter,
                        remarks = excluded.remarks,
                        evaluated_at = CURRENT_TIMESTAMP;
                    """,
                    (exam_id, g.student_id, g.marks_obtained, grade_letter, g.remarks),
                )
                graded_count += 1

        return {
            "exam_id": exam_id,
            "graded_count": graded_count,
            "status": "COMPLETED",
        }

    @staticmethod
    def get_exam_results(conn: sqlite3.Connection, exam_id: int) -> Dict[str, Any]:
        exam = AcademicsService.get_exam_by_id(conn, exam_id)
        if not exam:
            return None

        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                r.id, r.exam_id, r.student_id, r.marks_obtained, r.grade_letter,
                r.remarks, r.evaluated_at,
                (s.first_name || ' ' || s.last_name) AS student_name, s.enrollment_no,
                e.max_marks
            FROM exam_results r
            JOIN students s ON r.student_id = s.id
            JOIN examinations e ON r.exam_id = e.id
            WHERE r.exam_id = ?
            ORDER BY r.marks_obtained DESC;
            """,
            (exam_id,),
        )
        results = [dict(row) for row in cursor.fetchall()]

        # Analytics
        if results:
            marks = [r["marks_obtained"] for r in results]
            passing = float(exam["passing_marks"])
            passed_count = sum(1 for m in marks if m >= passing)
            stats = {
                "total_candidates": len(results),
                "average_marks": round(sum(marks) / len(marks), 2),
                "highest_marks": max(marks),
                "lowest_marks": min(marks),
                "pass_rate": round((passed_count / len(results) * 100), 1),
            }
        else:
            stats = {
                "total_candidates": 0,
                "average_marks": 0.0,
                "highest_marks": 0.0,
                "lowest_marks": 0.0,
                "pass_rate": 0.0,
            }

        cursor.close()
        return {
            "examination": exam,
            "statistics": stats,
            "roster": results,
        }
