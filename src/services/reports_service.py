"""Institutional Reports and Analytics service."""

import sqlite3
from typing import Any, Dict, List, Optional


class ReportsService:
    @staticmethod
    def get_analytics_summary(
        conn: sqlite3.Connection, department_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive institutional analytics, risk sentinel, and financial metrics."""
        cursor = conn.cursor()

        # 1. Total Students Count
        student_query = "SELECT COUNT(*) AS total FROM students WHERE status = 'ENROLLED'"
        dept_params: List[Any] = []
        if department_id:
            student_query += " AND department_id = ?"
            dept_params.append(department_id)

        cursor.execute(student_query, dept_params)
        total_students = cursor.fetchone()["total"]

        # 2. Overall Attendance Rate across institutions/department
        att_query = """
            SELECT
                COUNT(*) AS total_sessions,
                SUM(CASE WHEN ar.status IN ('PRESENT', 'LATE') THEN 1 ELSE 0 END) AS attended_sessions,
                SUM(CASE WHEN ar.status = 'ABSENT' THEN 1 ELSE 0 END) AS absent_sessions
            FROM attendance_records ar
            JOIN students s ON ar.student_id = s.id
            WHERE 1=1
        """
        att_params: List[Any] = []
        if department_id:
            att_query += " AND s.department_id = ?"
            att_params.append(department_id)

        cursor.execute(att_query, att_params)
        att_row = cursor.fetchone()
        total_sessions = att_row["total_sessions"] or 0
        attended_sessions = att_row["attended_sessions"] or 0
        overall_attendance_pct = (
            round((attended_sessions / total_sessions) * 100, 1) if total_sessions > 0 else 100.0
        )

        # 3. Low Attendance Risk Sentinel (< 75%)
        sentinel_query = """
            SELECT
                s.id AS student_id,
                s.enrollment_no,
                s.first_name,
                s.last_name,
                s.email,
                s.current_semester,
                d.name AS department_name,
                d.code AS department_code,
                COUNT(ar.id) AS total_sessions,
                SUM(CASE WHEN ar.status IN ('PRESENT', 'LATE') THEN 1 ELSE 0 END) AS attended_sessions,
                SUM(CASE WHEN ar.status = 'ABSENT' THEN 1 ELSE 0 END) AS absent_sessions,
                SUM(CASE WHEN ar.status = 'LATE' THEN 1 ELSE 0 END) AS late_sessions
            FROM students s
            JOIN departments d ON s.department_id = d.id
            JOIN attendance_records ar ON s.id = ar.student_id
            WHERE 1=1
        """
        sentinel_params: List[Any] = []
        if department_id:
            sentinel_query += " AND s.department_id = ?"
            sentinel_params.append(department_id)

        sentinel_query += """
            GROUP BY s.id
            HAVING total_sessions > 0 AND (CAST(attended_sessions AS REAL) / total_sessions * 100.0) < 75.0
            ORDER BY (CAST(attended_sessions AS REAL) / total_sessions * 100.0) ASC;
        """
        cursor.execute(sentinel_query, sentinel_params)
        raw_at_risk = cursor.fetchall()

        at_risk_scholars = []
        for r in raw_at_risk:
            t_sess = r["total_sessions"]
            att_sess = r["attended_sessions"]
            pct = round((att_sess / t_sess) * 100, 1) if t_sess > 0 else 0.0
            at_risk_scholars.append(
                {
                    "student_id": r["student_id"],
                    "enrollment_no": r["enrollment_no"],
                    "first_name": r["first_name"],
                    "last_name": r["last_name"],
                    "email": r["email"],
                    "current_semester": r["current_semester"],
                    "department_name": r["department_name"],
                    "department_code": r["department_code"],
                    "total_sessions": t_sess,
                    "attended_sessions": att_sess,
                    "absent_sessions": r["absent_sessions"],
                    "late_sessions": r["late_sessions"],
                    "attendance_pct": pct,
                    "risk_level": "CRITICAL" if pct < 60.0 else "WARNING",
                }
            )

        # 4. Institutional Grade Distribution
        grades_query = """
            SELECT
                er.grade_letter,
                COUNT(*) AS count
            FROM exam_results er
            JOIN students s ON er.student_id = s.id
            WHERE 1=1
        """
        grades_params: List[Any] = []
        if department_id:
            grades_query += " AND s.department_id = ?"
            grades_params.append(department_id)

        grades_query += " GROUP BY er.grade_letter ORDER BY er.grade_letter ASC;"
        cursor.execute(grades_query, grades_params)
        grade_rows = cursor.fetchall()
        grade_distribution = {row["grade_letter"]: row["count"] for row in grade_rows}

        # Calculate average marks percentage
        avg_query = """
            SELECT
                COUNT(er.id) AS total_evaluations,
                AVG(CAST(er.marks_obtained AS REAL) / e.max_marks * 100.0) AS avg_score_pct
            FROM exam_results er
            JOIN examinations e ON er.exam_id = e.id
            JOIN students s ON er.student_id = s.id
            WHERE 1=1
        """
        avg_params: List[Any] = []
        if department_id:
            avg_query += " AND s.department_id = ?"
            avg_params.append(department_id)

        cursor.execute(avg_query, avg_params)
        avg_row = cursor.fetchone()
        total_evaluations = avg_row["total_evaluations"] or 0
        avg_score_pct = round(avg_row["avg_score_pct"] or 0.0, 1)

        # 5. Financial Ledger & Recovery Metrics
        fin_query = """
            SELECT
                COUNT(fi.id) AS total_invoices,
                COALESCE(SUM(fi.total_amount), 0.0) AS total_invoiced,
                COALESCE(SUM(fi.paid_amount), 0.0) AS total_collected,
                COALESCE(SUM(fi.balance_amount), 0.0) AS total_outstanding,
                SUM(CASE WHEN fi.status = 'OVERDUE' OR (fi.balance_amount > 0 AND fi.due_date < DATE('now')) THEN 1 ELSE 0 END) AS overdue_count
            FROM fee_invoices fi
            JOIN students s ON fi.student_id = s.id
            WHERE 1=1
        """
        fin_params: List[Any] = []
        if department_id:
            fin_query += " AND s.department_id = ?"
            fin_params.append(department_id)

        cursor.execute(fin_query, fin_params)
        fin_row = cursor.fetchone()
        total_invoiced = fin_row["total_invoiced"] or 0.0
        total_collected = fin_row["total_collected"] or 0.0
        total_outstanding = fin_row["total_outstanding"] or 0.0
        overdue_invoices_count = fin_row["overdue_count"] or 0
        collection_rate_pct = (
            round((total_collected / total_invoiced) * 100, 1) if total_invoiced > 0 else 0.0
        )

        # 6. Departmental Breakdown Matrix
        dept_matrix_query = """
            SELECT
                d.id AS department_id,
                d.code AS department_code,
                d.name AS department_name,
                (SELECT COUNT(*) FROM students s WHERE s.department_id = d.id AND s.status = 'ENROLLED') AS students_count,
                (SELECT COUNT(*) FROM courses c WHERE c.department_id = d.id) AS courses_count,
                (SELECT COUNT(*) FROM faculty f WHERE f.department_id = d.id) AS faculty_count,
                COALESCE((
                    SELECT SUM(fi.total_amount)
                    FROM fee_invoices fi
                    JOIN students s ON fi.student_id = s.id
                    WHERE s.department_id = d.id
                ), 0.0) AS dept_invoiced,
                COALESCE((
                    SELECT SUM(fi.paid_amount)
                    FROM fee_invoices fi
                    JOIN students s ON fi.student_id = s.id
                    WHERE s.department_id = d.id
                ), 0.0) AS dept_collected,
                COALESCE((
                    SELECT SUM(fi.balance_amount)
                    FROM fee_invoices fi
                    JOIN students s ON fi.student_id = s.id
                    WHERE s.department_id = d.id
                ), 0.0) AS dept_balance
            FROM departments d
            ORDER BY d.code ASC;
        """
        cursor.execute(dept_matrix_query)
        dept_rows = cursor.fetchall()
        department_metrics = []
        for d in dept_rows:
            inv = d["dept_invoiced"] or 0.0
            col = d["dept_collected"] or 0.0
            recovery = round((col / inv) * 100, 1) if inv > 0 else 0.0
            department_metrics.append(
                {
                    "department_id": d["department_id"],
                    "department_code": d["department_code"],
                    "department_name": d["department_name"],
                    "students_count": d["students_count"],
                    "courses_count": d["courses_count"],
                    "faculty_count": d["faculty_count"],
                    "invoiced": inv,
                    "collected": col,
                    "balance": d["dept_balance"] or 0.0,
                    "recovery_rate_pct": recovery,
                }
            )

        # 7. Examination Assessment Catalog with pass rate
        exam_perf_query = """
            SELECT
                e.id, e.title, e.exam_type, e.exam_date, e.max_marks, e.passing_marks,
                c.code AS course_code, c.title AS course_title,
                COUNT(er.id) AS evaluated_count,
                AVG(er.marks_obtained) AS avg_marks,
                SUM(CASE WHEN er.marks_obtained >= e.passing_marks THEN 1 ELSE 0 END) AS passed_count
            FROM examinations e
            JOIN courses c ON e.course_id = c.id
            LEFT JOIN exam_results er ON e.id = er.exam_id
            WHERE 1=1
        """
        exam_perf_params: List[Any] = []
        if department_id:
            exam_perf_query += " AND c.department_id = ?"
            exam_perf_params.append(department_id)

        exam_perf_query += """
            GROUP BY e.id
            ORDER BY e.exam_date DESC
            LIMIT 20;
        """
        cursor.execute(exam_perf_query, exam_perf_params)
        exam_rows = cursor.fetchall()
        exam_performance = []
        for er in exam_rows:
            eval_cnt = er["evaluated_count"]
            passed_cnt = er["passed_count"] or 0
            pass_rate = round((passed_cnt / eval_cnt) * 100, 1) if eval_cnt > 0 else 0.0
            exam_performance.append(
                {
                    "id": er["id"],
                    "title": er["title"],
                    "exam_type": er["exam_type"],
                    "exam_date": er["exam_date"],
                    "max_marks": er["max_marks"],
                    "passing_marks": er["passing_marks"],
                    "course_code": er["course_code"],
                    "course_title": er["course_title"],
                    "evaluated_count": eval_cnt,
                    "avg_marks": round(er["avg_marks"] or 0.0, 1),
                    "passed_count": passed_cnt,
                    "pass_rate_pct": pass_rate,
                }
            )

        cursor.close()

        return {
            "total_students": total_students,
            "overall_attendance_pct": overall_attendance_pct,
            "total_attendance_sessions": total_sessions,
            "at_risk_students_count": len(at_risk_scholars),
            "at_risk_scholars": at_risk_scholars,
            "grade_distribution": grade_distribution,
            "total_evaluations": total_evaluations,
            "avg_score_pct": avg_score_pct,
            "total_invoiced": total_invoiced,
            "total_collected": total_collected,
            "total_outstanding": total_outstanding,
            "collection_rate_pct": collection_rate_pct,
            "overdue_invoices_count": overdue_invoices_count,
            "department_metrics": department_metrics,
            "exam_performance": exam_performance,
        }
