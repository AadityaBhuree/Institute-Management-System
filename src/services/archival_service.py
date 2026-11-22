"""Scholar Cohort Archival & Cold Storage Lifecycle Manager.
Policy-driven archival workflow moving graduated and alumni scholar records into
cold storage tables with cryptographic SHA-256 integrity hashes and audit verification.
"""

import hashlib
import json
import logging
import sqlite3
from typing import Any, Dict, List, Optional

from src.database.connection import transaction
from src.services.auth_service import AuthService
from src.services.student_service import StudentService

logger = logging.getLogger("ims")


class ArchivalService:
    """Enterprise policy-driven scholar cohort archival engine."""

    @staticmethod
    def archive_cohort(
        conn: sqlite3.Connection,
        graduation_year: int,
        archived_by: str,
        department_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute atomic cohort archival snapshot with SHA-256 integrity sealing."""
        cursor = conn.cursor()
        query = """
            SELECT s.id, s.enrollment_no, s.first_name, s.last_name, s.email,
                   d.code AS department_code, s.admission_date, s.status
            FROM students s
            JOIN departments d ON s.department_id = d.id
            WHERE (
                s.status IN ('GRADUATED', 'ALUMNI')
                OR CAST(strftime('%Y', s.admission_date) AS INTEGER) <= ? - 3
                OR s.current_semester >= 8
            )
        """
        params: List[Any] = [graduation_year]
        if department_id:
            query += " AND s.department_id = ?"
            params.append(department_id)

        query += " ORDER BY s.enrollment_no ASC;"
        cursor.execute(query, params)
        eligible_students = cursor.fetchall()
        cursor.close()

        if not eligible_students:
            return {
                "status": "COMPLETED",
                "graduation_year": graduation_year,
                "archived_count": 0,
                "archived_records": [],
                "message": f"No eligible graduated scholars found for graduation year {graduation_year}",
            }

        archived_items: List[Dict[str, Any]] = []

        with transaction(conn) as cur:
            for s in eligible_students:
                student_id = s["id"]
                enrollment_no = s["enrollment_no"]
                full_name = f"{s['first_name']} {s['last_name']}".strip()
                email = s["email"]
                dept_code = s["department_code"]

                # 1. Compile complete canonical student portal dossier
                dossier = StudentService.get_student_portal_dossier(conn, student_id)
                if not dossier:
                    continue

                # 2. Extract metrics (CGPA, credits)
                exam_results = dossier.get("exam_results", [])
                enrollments = dossier.get("enrollments", [])
                total_creds = sum(e.get("credits", 0) for e in enrollments)

                tot_marks = sum(float(r.get("marks_obtained", 0)) for r in exam_results)
                tot_max = sum(float(r.get("max_marks", 0)) for r in exam_results)
                avg_pct = round((tot_marks / tot_max) * 100.0, 2) if tot_max > 0 else 0.0
                cgpa = round(avg_pct / 10.0, 2)

                # 3. Create deterministic canonical JSON snapshot
                payload_json = json.dumps(dossier, sort_keys=True, default=str)
                integrity_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

                # 4. Insert into cold storage
                cur.execute(
                    """
                    INSERT INTO archived_students (
                        original_student_id, enrollment_no, full_name, email,
                        department_code, graduation_year, final_cgpa, total_credits,
                        archive_payload_json, integrity_hash, archived_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(enrollment_no) DO UPDATE SET
                        graduation_year = excluded.graduation_year,
                        final_cgpa = excluded.final_cgpa,
                        total_credits = excluded.total_credits,
                        archive_payload_json = excluded.archive_payload_json,
                        integrity_hash = excluded.integrity_hash,
                        archived_by = excluded.archived_by,
                        archived_at = CURRENT_TIMESTAMP;
                    """,
                    (
                        student_id,
                        enrollment_no,
                        full_name,
                        email,
                        dept_code,
                        graduation_year,
                        cgpa,
                        total_creds,
                        payload_json,
                        integrity_hash,
                        archived_by,
                    ),
                )

                # 5. Fetch inserted/updated record ID
                cur.execute(
                    "SELECT id, archived_at FROM archived_students WHERE enrollment_no = ?;",
                    (enrollment_no,),
                )
                rec = cur.fetchone()
                archive_id = rec["id"]
                archived_at = str(rec["archived_at"])

                # 6. Mark student status as GRADUATED in active registry
                cur.execute(
                    "UPDATE students SET status = 'GRADUATED' WHERE id = ?;",
                    (student_id,),
                )

                archived_items.append(
                    {
                        "id": archive_id,
                        "original_student_id": student_id,
                        "enrollment_no": enrollment_no,
                        "full_name": full_name,
                        "email": email,
                        "department_code": dept_code,
                        "graduation_year": graduation_year,
                        "final_cgpa": cgpa,
                        "total_credits": total_creds,
                        "integrity_hash": integrity_hash,
                        "archived_by": archived_by,
                        "archived_at": archived_at,
                    }
                )

        # Record immutable audit trail after transaction commits
        AuthService.log_audit(
            conn,
            action="COHORT_ARCHIVE",
            resource="archived_students",
            details=f"Archived {len(archived_items)} scholars for cohort {graduation_year}. Notes: {notes or 'Standard graduation cycle'}",
            username=archived_by,
        )

        logger.info(
            "Successfully archived cohort year %d (%d scholars) by %s",
            graduation_year,
            len(archived_items),
            archived_by,
        )

        return {
            "status": "COMPLETED",
            "graduation_year": graduation_year,
            "archived_count": len(archived_items),
            "archived_records": archived_items,
        }

    @staticmethod
    def list_archived_records(
        conn: sqlite3.Connection, graduation_year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve index of all cold-storage archived scholar records."""
        cursor = conn.cursor()
        query = """
            SELECT id, original_student_id, enrollment_no, full_name, email,
                   department_code, graduation_year, final_cgpa, total_credits,
                   integrity_hash, archived_by, archived_at
            FROM archived_students
            WHERE 1=1
        """
        params: List[Any] = []
        if graduation_year:
            query += " AND graduation_year = ?"
            params.append(graduation_year)

        query += " ORDER BY graduation_year DESC, enrollment_no ASC;"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_archived_record(conn: sqlite3.Connection, archive_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve full archived scholar record including decoded payload snapshot."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, original_student_id, enrollment_no, full_name, email,
                   department_code, graduation_year, final_cgpa, total_credits,
                   archive_payload_json, integrity_hash, archived_by, archived_at
            FROM archived_students
            WHERE id = ?;
            """,
            (archive_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        if not row:
            return None

        data = dict(row)
        try:
            data["snapshot"] = json.loads(data.pop("archive_payload_json"))
        except Exception:
            data["snapshot"] = {}
        return data

    @staticmethod
    def verify_archive_integrity(conn: sqlite3.Connection, archive_id: int) -> Dict[str, Any]:
        """Cryptographically verify the SHA-256 seal of an archived scholar snapshot."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, enrollment_no, archive_payload_json, integrity_hash, archived_at
            FROM archived_students
            WHERE id = ?;
            """,
            (archive_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        if not row:
            raise KeyError(f"Archived record #{archive_id} not found")

        stored_hash = row["integrity_hash"]
        payload_str = row["archive_payload_json"]
        computed_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        is_valid = stored_hash == computed_hash

        return {
            "archive_id": archive_id,
            "enrollment_no": row["enrollment_no"],
            "is_valid": is_valid,
            "stored_hash": stored_hash,
            "computed_hash": computed_hash,
            "archived_at": str(row["archived_at"]),
        }
