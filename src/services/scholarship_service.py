"""Scholarships, Grants & Financial Aid Management Service."""

import sqlite3
from typing import Any, Dict, List, Optional

from src.database.connection import transaction
from src.models.scholarship import (
    ScholarshipApplicationCreate,
    ScholarshipReviewUpdate,
    ScholarshipSchemeCreate,
)


class ScholarshipService:
    @staticmethod
    def list_schemes(conn: sqlite3.Connection, status: Optional[str] = None) -> List[dict]:
        query = """
            SELECT s.id, s.scheme_name, s.sponsor_type, s.award_amount,
                   s.min_gpa_required, s.max_family_income, s.eligible_category,
                   s.status, s.created_at,
                   COUNT(a.id) AS applications_count
            FROM scholarship_schemes s
            LEFT JOIN scholarship_applications a ON s.id = a.scheme_id
            WHERE 1=1
        """
        params = []
        if status:
            query += " AND s.status = ?"
            params.append(status)

        query += " GROUP BY s.id ORDER BY s.award_amount DESC;"
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_scheme_by_id(conn: sqlite3.Connection, scheme_id: int) -> Optional[dict]:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scholarship_schemes WHERE id = ?;", (scheme_id,))
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

    @staticmethod
    def create_scheme(conn: sqlite3.Connection, data: ScholarshipSchemeCreate) -> dict:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM scholarship_schemes WHERE scheme_name = ?;",
            (data.scheme_name.strip(),),
        )
        if cursor.fetchone():
            cursor.close()
            raise ValueError(f"Scholarship scheme '{data.scheme_name}' already exists.")
        cursor.close()

        with transaction(conn) as cur:
            cur.execute(
                """
                INSERT INTO scholarship_schemes (
                    scheme_name, sponsor_type, award_amount, min_gpa_required,
                    max_family_income, eligible_category, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    data.scheme_name.strip(),
                    data.sponsor_type,
                    data.award_amount,
                    data.min_gpa_required,
                    data.max_family_income,
                    data.eligible_category.strip(),
                    data.status,
                ),
            )
            scheme_id = cur.lastrowid

        return ScholarshipService.get_scheme_by_id(conn, scheme_id)  # type: ignore

    @staticmethod
    def apply_for_scholarship(conn: sqlite3.Connection, data: ScholarshipApplicationCreate) -> dict:
        scheme = ScholarshipService.get_scheme_by_id(conn, data.scheme_id)
        if not scheme:
            raise ValueError(f"Scholarship scheme ID {data.scheme_id} not found.")

        if scheme["status"] != "ACTIVE":
            raise ValueError(f"Scholarship scheme '{scheme['scheme_name']}' is currently closed.")

        if data.current_gpa < scheme["min_gpa_required"]:
            raise ValueError(
                f"Academic criteria not satisfied: minimum GPA required is "
                f"{scheme['min_gpa_required']:.2f}, candidate has {data.current_gpa:.2f}."
            )

        if scheme["max_family_income"] and data.annual_family_income > scheme["max_family_income"]:
            raise ValueError(
                f"Financial criteria not satisfied: maximum family income threshold is "
                f"₹{scheme['max_family_income']:,.0f}, reported is ₹{data.annual_family_income:,.0f}."
            )

        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, first_name, last_name FROM students WHERE id = ?;", (data.student_id,)
        )
        student = cursor.fetchone()
        if not student:
            cursor.close()
            raise ValueError(f"Student ID {data.student_id} not found.")

        cursor.execute(
            "SELECT id FROM scholarship_applications WHERE scheme_id = ? AND student_id = ?;",
            (data.scheme_id, data.student_id),
        )
        if cursor.fetchone():
            cursor.close()
            raise ValueError(
                f"Candidate has already submitted an application for '{scheme['scheme_name']}'."
            )
        cursor.close()

        with transaction(conn) as cur:
            cur.execute(
                """
                INSERT INTO scholarship_applications (
                    scheme_id, student_id, current_gpa, annual_family_income,
                    disbursed_amount, status
                ) VALUES (?, ?, ?, ?, 0.0, 'PENDING');
                """,
                (
                    data.scheme_id,
                    data.student_id,
                    data.current_gpa,
                    data.annual_family_income,
                ),
            )
            app_id = cur.lastrowid

        apps = ScholarshipService.list_applications(conn)
        for a in apps:
            if a["id"] == app_id:
                return a
        return {"id": app_id, "status": "PENDING"}

    @staticmethod
    def review_application(
        conn: sqlite3.Connection,
        app_id: int,
        data: ScholarshipReviewUpdate,
    ) -> dict:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT a.*, s.award_amount, s.scheme_name
            FROM scholarship_applications a
            JOIN scholarship_schemes s ON a.scheme_id = s.id
            WHERE a.id = ?;
            """,
            (app_id,),
        )
        application = cursor.fetchone()
        cursor.close()

        if not application:
            raise ValueError(f"Scholarship application ID {app_id} not found.")

        disbursed = data.disbursed_amount
        if data.status == "DISBURSED" and disbursed is None:
            disbursed = application["award_amount"]
        elif data.status in ("PENDING", "REJECTED"):
            disbursed = 0.0

        with transaction(conn) as cur:
            cur.execute(
                """
                UPDATE scholarship_applications
                SET status = ?, review_remarks = ?, disbursed_amount = ?
                WHERE id = ?;
                """,
                (
                    data.status,
                    data.review_remarks,
                    disbursed or 0.0,
                    app_id,
                ),
            )

        apps = ScholarshipService.list_applications(conn)
        for a in apps:
            if a["id"] == app_id:
                return a
        return {"id": app_id, "status": data.status}

    @staticmethod
    def list_applications(
        conn: sqlite3.Connection,
        scheme_id: Optional[int] = None,
        student_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[dict]:
        query = """
            SELECT a.id, a.scheme_id, a.student_id, a.current_gpa, a.annual_family_income,
                   a.disbursed_amount, a.status, a.review_remarks, a.created_at,
                   s.scheme_name, s.award_amount,
                   st.first_name || ' ' || st.last_name AS student_name,
                   st.enrollment_no, d.code AS department_code
            FROM scholarship_applications a
            JOIN scholarship_schemes s ON a.scheme_id = s.id
            JOIN students st ON a.student_id = st.id
            JOIN departments d ON st.department_id = d.id
            WHERE 1=1
        """
        params = []
        if scheme_id:
            query += " AND a.scheme_id = ?"
            params.append(scheme_id)
        if student_id:
            query += " AND a.student_id = ?"
            params.append(student_id)
        if status:
            query += " AND a.status = ?"
            params.append(status)

        query += " ORDER BY a.created_at DESC;"
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_stats(conn: sqlite3.Connection) -> Dict[str, Any]:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(id) FROM scholarship_schemes;")
        total_schemes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(id) FROM scholarship_schemes WHERE status = 'ACTIVE';")
        active_schemes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(id) FROM scholarship_applications;")
        total_apps = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(id), COALESCE(SUM(disbursed_amount), 0.0), COALESCE(AVG(disbursed_amount), 0.0)
            FROM scholarship_applications
            WHERE status IN ('APPROVED', 'DISBURSED');
            """
        )
        awarded_row = cursor.fetchone()
        awarded_count = awarded_row[0]
        total_disbursed = round(awarded_row[1], 2)
        avg_award = round(awarded_row[2], 2)
        cursor.close()

        return {
            "total_schemes": total_schemes,
            "active_schemes": active_schemes,
            "total_applications": total_apps,
            "awarded_count": awarded_count,
            "total_funds_disbursed": total_disbursed,
            "average_award_amount": avg_award,
        }
