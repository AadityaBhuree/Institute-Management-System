"""Campus Placements & Corporate Recruitment Service."""

import sqlite3
from typing import Dict, List, Optional

from src.database.connection import transaction
from src.models.placement import (
    PlacementApplicationCreate,
    PlacementDriveCreate,
    PlacementStatusUpdate,
)


class PlacementService:
    @staticmethod
    def list_drives(
        conn: sqlite3.Connection,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[dict]:
        """List placement drives with total applicants count."""
        query = """
            SELECT d.id, d.company_name, d.industry, d.job_title, d.job_location,
                   d.package_lpa, d.min_gpa_required, d.eligible_departments,
                   d.drive_date, d.registration_deadline, d.status, d.created_at,
                   COUNT(a.id) AS applications_count
            FROM placement_drives d
            LEFT JOIN placement_applications a ON d.id = a.drive_id
            WHERE 1=1
        """
        params = []
        if status:
            query += " AND d.status = ?"
            params.append(status)
        if search:
            term = f"%{search.strip()}%"
            query += " AND (d.company_name LIKE ? OR d.job_title LIKE ? OR d.industry LIKE ?)"
            params.extend([term, term, term])

        query += " GROUP BY d.id ORDER BY d.drive_date ASC;"

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_drive_by_id(conn: sqlite3.Connection, drive_id: int) -> Optional[dict]:
        """Retrieve a specific drive by ID."""
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM placement_drives WHERE id = ?;", (drive_id,))
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

    @staticmethod
    def create_drive(conn: sqlite3.Connection, data: PlacementDriveCreate) -> dict:
        """Create a new corporate recruitment drive."""
        with transaction(conn) as cur:
            cur.execute(
                """
                INSERT INTO placement_drives (
                    company_name, industry, job_title, job_location, package_lpa,
                    min_gpa_required, eligible_departments, drive_date,
                    registration_deadline, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    data.company_name.strip(),
                    data.industry.strip(),
                    data.job_title.strip(),
                    data.job_location.strip(),
                    data.package_lpa,
                    data.min_gpa_required,
                    data.eligible_departments.strip(),
                    data.drive_date,
                    data.registration_deadline,
                    data.status,
                ),
            )
            drive_id = cur.lastrowid

        return PlacementService.get_drive_by_id(conn, drive_id)  # type: ignore

    @staticmethod
    def apply_for_drive(conn: sqlite3.Connection, data: PlacementApplicationCreate) -> dict:
        """Submit student placement application with GPA eligibility check."""
        drive = PlacementService.get_drive_by_id(conn, data.drive_id)
        if not drive:
            raise ValueError(f"Placement drive ID {data.drive_id} not found.")

        if drive["status"] == "CLOSED":
            raise ValueError(f"Recruitment drive for {drive['company_name']} is currently closed.")

        if data.current_gpa < drive["min_gpa_required"]:
            raise ValueError(
                f"Eligibility requirement not met: minimum GPA required is "
                f"{drive['min_gpa_required']:.2f}, but candidate GPA is {data.current_gpa:.2f}."
            )

        # Validate student
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, first_name, last_name FROM students WHERE id = ?;", (data.student_id,)
        )
        student = cursor.fetchone()
        if not student:
            cursor.close()
            raise ValueError(f"Student ID {data.student_id} not found.")

        # Check existing application
        cursor.execute(
            "SELECT id FROM placement_applications WHERE drive_id = ? AND student_id = ?;",
            (data.drive_id, data.student_id),
        )
        if cursor.fetchone():
            cursor.close()
            raise ValueError(
                f"Candidate has already submitted an application for {drive['company_name']}."
            )
        cursor.close()

        with transaction(conn) as cur:
            cur.execute(
                """
                INSERT INTO placement_applications (
                    drive_id, student_id, current_gpa, resume_link, status, remarks
                ) VALUES (?, ?, ?, ?, 'APPLIED', ?);
                """,
                (
                    data.drive_id,
                    data.student_id,
                    data.current_gpa,
                    data.resume_link,
                    data.remarks,
                ),
            )
            app_id = cur.lastrowid

        apps = PlacementService.list_applications(conn)
        for a in apps:
            if a["id"] == app_id:
                return a
        return {"id": app_id, "status": "APPLIED"}

    @staticmethod
    def update_application_status(
        conn: sqlite3.Connection,
        app_id: int,
        data: PlacementStatusUpdate,
    ) -> dict:
        """Update candidate interview stage or issue job offer."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT a.*, d.package_lpa
            FROM placement_applications a
            JOIN placement_drives d ON a.drive_id = d.id
            WHERE a.id = ?;
            """,
            (app_id,),
        )
        application = cursor.fetchone()
        cursor.close()

        if not application:
            raise ValueError(f"Placement application ID {app_id} not found.")

        offer = data.offer_package_lpa
        if data.status == "SELECTED" and offer is None:
            offer = application["package_lpa"]

        with transaction(conn) as cur:
            cur.execute(
                """
                UPDATE placement_applications
                SET status = ?, interview_date = ?, offer_package_lpa = ?, remarks = ?
                WHERE id = ?;
                """,
                (
                    data.status,
                    data.interview_date or application["interview_date"],
                    offer,
                    data.remarks or application["remarks"],
                    app_id,
                ),
            )

        apps = PlacementService.list_applications(conn)
        for a in apps:
            if a["id"] == app_id:
                return a
        return {"id": app_id, "status": data.status}

    @staticmethod
    def list_applications(
        conn: sqlite3.Connection,
        drive_id: Optional[int] = None,
        student_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[dict]:
        """List applications enriched with drive and student details."""
        query = """
            SELECT a.id, a.drive_id, a.student_id, a.current_gpa, a.resume_link,
                   a.status, a.interview_date, a.offer_package_lpa, a.remarks, a.created_at,
                   d.company_name, d.job_title, d.package_lpa,
                   (s.first_name || ' ' || s.last_name) AS student_name, s.enrollment_no,
                   dept.code AS department_code
            FROM placement_applications a
            JOIN placement_drives d ON a.drive_id = d.id
            JOIN students s ON a.student_id = s.id
            JOIN departments dept ON s.department_id = dept.id
            WHERE 1=1
        """
        params = []
        if drive_id:
            query += " AND a.drive_id = ?"
            params.append(drive_id)
        if student_id:
            query += " AND a.student_id = ?"
            params.append(student_id)
        if status:
            query += " AND a.status = ?"
            params.append(status)

        query += " ORDER BY a.id DESC;"

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_stats(conn: sqlite3.Connection) -> Dict[str, float]:
        """Aggregate career placement and corporate recruitment metrics."""
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM placement_drives;")
        total_drives = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM placement_drives WHERE status = 'ACTIVE';")
        active_drives = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM placement_applications;")
        total_applications = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM placement_applications WHERE status = 'SELECTED';")
        selected_offers = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COALESCE(AVG(offer_package_lpa), 0.0),
                   COALESCE(MAX(offer_package_lpa), 0.0)
            FROM placement_applications
            WHERE status = 'SELECTED';
            """
        )
        avg_pkg, max_pkg = cursor.fetchone()
        cursor.close()

        return {
            "total_drives": total_drives,
            "active_drives": active_drives,
            "total_applications": total_applications,
            "selected_offers": selected_offers,
            "average_package_lpa": round(float(avg_pkg), 2),
            "highest_package_lpa": round(float(max_pkg), 2),
        }
