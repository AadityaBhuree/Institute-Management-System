"""Department database service."""

import sqlite3
from typing import List, Optional

from src.database.connection import transaction
from src.models.department import DepartmentCreate


class DepartmentService:
    @staticmethod
    def list_all(conn: sqlite3.Connection) -> List[dict]:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, code, name, description, created_at FROM departments ORDER BY code ASC;"
        )
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(conn: sqlite3.Connection, dept_id: int) -> Optional[dict]:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, code, name, description, created_at FROM departments WHERE id = ?;",
            (dept_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

    @staticmethod
    def create(conn: sqlite3.Connection, dept_in: DepartmentCreate) -> dict:
        with transaction(conn) as cursor:
            cursor.execute(
                """
                INSERT INTO departments (code, name, description)
                VALUES (?, ?, ?);
                """,
                (dept_in.code.upper(), dept_in.name, dept_in.description),
            )
            dept_id = cursor.lastrowid
        return DepartmentService.get_by_id(conn, dept_id)
