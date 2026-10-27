"""Department database service with in-memory TTL caching."""

import sqlite3
from typing import List, Optional

from src.core.cache import cache
from src.database.connection import transaction
from src.models.department import DepartmentCreate

DEPARTMENTS_CACHE_KEY = "departments:all"


class DepartmentService:
    @staticmethod
    def list_all(conn: sqlite3.Connection, force_refresh: bool = False) -> List[dict]:
        """Retrieve all institutional departments with in-memory TTL caching."""
        if not force_refresh:
            cached = cache.get(DEPARTMENTS_CACHE_KEY)
            if cached is not None:
                return cached

        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, code, name, description, created_at FROM departments ORDER BY code ASC;"
        )
        rows = cursor.fetchall()
        cursor.close()
        result = [dict(row) for row in rows]
        cache.set(DEPARTMENTS_CACHE_KEY, result, ttl_seconds=300.0)
        return result

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

        # Invalidate department and dependent dashboard caches
        cache.delete(DEPARTMENTS_CACHE_KEY)
        cache.invalidate_prefix("dashboard:")

        return DepartmentService.get_by_id(conn, dept_id)
