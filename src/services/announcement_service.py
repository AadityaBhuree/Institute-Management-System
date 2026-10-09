"""Campus announcements service."""

import sqlite3
from typing import List, Optional

from src.database.connection import transaction
from src.models.announcement import AnnouncementCreate


class AnnouncementService:
    @staticmethod
    def list_announcements(
        conn: sqlite3.Connection,
        category: Optional[str] = None,
        target_audience: Optional[str] = None,
        is_active: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[dict]:
        """Query announcements with optional category, audience, active status and search."""
        query = """
            SELECT id, title, content, category, target_audience, priority, author_name,
                   is_active, created_at, expires_at
            FROM announcements
            WHERE 1=1
        """
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)

        if target_audience and target_audience != "ALL":
            query += " AND (target_audience = ? OR target_audience = 'ALL')"
            params.append(target_audience)
        elif target_audience == "ALL":
            query += " AND target_audience = 'ALL'"

        if is_active is not None:
            query += " AND is_active = ?"
            params.append(is_active)

        if search:
            query += " AND (title LIKE ? OR content LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term])

        # Priority ordering: HIGH first, then NORMAL, then LOW, then newest
        query += """
            ORDER BY
                CASE priority
                    WHEN 'HIGH' THEN 1
                    WHEN 'NORMAL' THEN 2
                    WHEN 'LOW' THEN 3
                    ELSE 4
                END,
                created_at DESC;
        """

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(conn: sqlite3.Connection, announcement_id: int) -> Optional[dict]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, title, content, category, target_audience, priority, author_name,
                   is_active, created_at, expires_at
            FROM announcements
            WHERE id = ?;
            """,
            (announcement_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

    @staticmethod
    def create(conn: sqlite3.Connection, data: AnnouncementCreate) -> dict:
        with transaction(conn) as cursor:
            cursor.execute(
                """
                INSERT INTO announcements (
                    title, content, category, target_audience, priority, author_name, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    data.title.strip(),
                    data.content.strip(),
                    data.category,
                    data.target_audience,
                    data.priority,
                    data.author_name.strip(),
                    data.expires_at,
                ),
            )
            announcement_id = cursor.lastrowid
        return AnnouncementService.get_by_id(conn, announcement_id)

    @staticmethod
    def toggle_active(conn: sqlite3.Connection, announcement_id: int, is_active: int) -> Optional[dict]:
        with transaction(conn) as cursor:
            cursor.execute(
                "UPDATE announcements SET is_active = ? WHERE id = ?;",
                (1 if is_active else 0, announcement_id),
            )
        return AnnouncementService.get_by_id(conn, announcement_id)

    @staticmethod
    def delete(conn: sqlite3.Connection, announcement_id: int) -> bool:
        with transaction(conn) as cursor:
            cursor.execute("DELETE FROM announcements WHERE id = ?;", (announcement_id,))
            deleted = cursor.rowcount > 0
        return deleted
