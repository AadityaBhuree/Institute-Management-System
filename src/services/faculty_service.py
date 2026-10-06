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
