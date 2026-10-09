"""Academic Timetable and Lecture Scheduling Service."""

import sqlite3
from typing import Dict, List, Optional

from src.database.connection import transaction
from src.models.timetable import TimetableSlotCreate


class TimetableService:
    @staticmethod
    def list_slots(
        conn: sqlite3.Connection,
        day_of_week: Optional[str] = None,
        course_id: Optional[int] = None,
        room_number: Optional[str] = None,
        department_id: Optional[int] = None,
    ) -> List[dict]:
        """Query scheduled lecture slots with course and instructor metadata."""
        query = """
            SELECT
                ts.id, ts.course_id, ts.day_of_week, ts.start_time, ts.end_time,
                ts.room_number, ts.building, ts.created_at,
                c.code AS course_code, c.title AS course_title, c.department_id,
                d.name AS department_name,
                (f.first_name || ' ' || f.last_name) AS instructor_name
            FROM timetable_slots ts
            JOIN courses c ON ts.course_id = c.id
            JOIN departments d ON c.department_id = d.id
            LEFT JOIN faculty f ON c.instructor_id = f.id
            WHERE 1=1
        """
        params = []

        if day_of_week:
            query += " AND ts.day_of_week = ?"
            params.append(day_of_week)

        if course_id:
            query += " AND ts.course_id = ?"
            params.append(course_id)

        if room_number:
            query += " AND ts.room_number = ?"
            params.append(room_number)

        if department_id:
            query += " AND c.department_id = ?"
            params.append(department_id)

        query += """
            ORDER BY
                CASE ts.day_of_week
                    WHEN 'Monday' THEN 1
                    WHEN 'Tuesday' THEN 2
                    WHEN 'Wednesday' THEN 3
                    WHEN 'Thursday' THEN 4
                    WHEN 'Friday' THEN 5
                    WHEN 'Saturday' THEN 6
                    ELSE 7
                END,
                ts.start_time ASC;
        """

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(conn: sqlite3.Connection, slot_id: int) -> Optional[dict]:
        slots = TimetableService.list_slots(conn)
        for s in slots:
            if s["id"] == slot_id:
                return s
        return None

    @staticmethod
    def create_slot(conn: sqlite3.Connection, data: TimetableSlotCreate) -> dict:
        """Schedule a lecture slot with room and instructor collision avoidance."""
        if data.start_time >= data.end_time:
            raise ValueError(f"Lecture start time ({data.start_time}) must be earlier than end time ({data.end_time})")

        cursor = conn.cursor()

        # 1. Check Course validity and instructor ID
        cursor.execute("SELECT id, instructor_id, title FROM courses WHERE id = ?;", (data.course_id,))
        course = cursor.fetchone()
        if not course:
            cursor.close()
            raise ValueError(f"Course #{data.course_id} does not exist.")
        instructor_id = course["instructor_id"]

        # 2. Check Room Collision (overlapping start/end on same day)
        cursor.execute(
            """
            SELECT ts.id, ts.start_time, ts.end_time, c.code
            FROM timetable_slots ts
            JOIN courses c ON ts.course_id = c.id
            WHERE ts.day_of_week = ?
              AND ts.room_number = ?
              AND (ts.start_time < ? AND ts.end_time > ?);
            """,
            (data.day_of_week, data.room_number.strip(), data.end_time, data.start_time),
        )
        room_conflict = cursor.fetchone()
        if room_conflict:
            cursor.close()
            raise ValueError(
                f"Room collision: {data.room_number} is already booked on {data.day_of_week} "
                f"from {room_conflict['start_time']} to {room_conflict['end_time']} by {room_conflict['code']}."
            )

        # 3. Check Instructor Collision (if instructor assigned)
        if instructor_id:
            cursor.execute(
                """
                SELECT ts.id, ts.start_time, ts.end_time, c.code
                FROM timetable_slots ts
                JOIN courses c ON ts.course_id = c.id
                WHERE ts.day_of_week = ?
                  AND c.instructor_id = ?
                  AND (ts.start_time < ? AND ts.end_time > ?);
                """,
                (data.day_of_week, instructor_id, data.end_time, data.start_time),
            )
            instr_conflict = cursor.fetchone()
            if instr_conflict:
                cursor.close()
                raise ValueError(
                    f"Instructor collision: Course instructor is already assigned to {instr_conflict['code']} "
                    f"on {data.day_of_week} from {instr_conflict['start_time']} to {instr_conflict['end_time']}."
                )

        cursor.close()

        # 4. Insert slot
        with transaction(conn) as cur:
            cur.execute(
                """
                INSERT INTO timetable_slots (
                    course_id, day_of_week, start_time, end_time, room_number, building
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    data.course_id,
                    data.day_of_week,
                    data.start_time,
                    data.end_time,
                    data.room_number.strip(),
                    data.building.strip(),
                ),
            )
            slot_id = cur.lastrowid

        return TimetableService.get_by_id(conn, slot_id)

    @staticmethod
    def delete_slot(conn: sqlite3.Connection, slot_id: int) -> bool:
        with transaction(conn) as cursor:
            cursor.execute("DELETE FROM timetable_slots WHERE id = ?;", (slot_id,))
            deleted = cursor.rowcount > 0
        return deleted

    @staticmethod
    def get_weekly_matrix(conn: sqlite3.Connection, department_id: Optional[int] = None) -> Dict[str, List[dict]]:
        """Return timetable organized into a weekly day-by-day dictionary."""
        slots = TimetableService.list_slots(conn, department_id=department_id)
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        matrix = {day: [] for day in days}
        for slot in slots:
            if slot["day_of_week"] in matrix:
                matrix[slot["day_of_week"]].append(slot)
        return matrix
