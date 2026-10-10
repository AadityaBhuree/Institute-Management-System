"""Hostel & Residential Hall Management Service."""

import sqlite3
from typing import Dict, List, Optional

from src.database.connection import transaction
from src.models.hostel import (
    HostelBlockCreate,
    HostelRoomCreate,
    RoomAllocationCreate,
    RoomCheckoutRequest,
)


class HostelService:
    @staticmethod
    def list_blocks(conn: sqlite3.Connection) -> List[dict]:
        """List all residential blocks."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, block_name, gender_type, total_rooms, warden_name,
                   warden_contact, created_at
            FROM hostel_blocks
            ORDER BY block_name ASC;
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_block_by_id(conn: sqlite3.Connection, block_id: int) -> Optional[dict]:
        """Retrieve block by ID."""
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM hostel_blocks WHERE id = ?;", (block_id,))
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

    @staticmethod
    def create_block(conn: sqlite3.Connection, data: HostelBlockCreate) -> dict:
        """Create a new residential block."""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM hostel_blocks WHERE block_name = ?;",
            (data.block_name.strip(),),
        )
        if cursor.fetchone():
            cursor.close()
            raise ValueError(f"Block '{data.block_name}' already exists.")
        cursor.close()

        with transaction(conn) as cur:
            cur.execute(
                """
                INSERT INTO hostel_blocks (
                    block_name, gender_type, total_rooms, warden_name, warden_contact
                ) VALUES (?, ?, ?, ?, ?);
                """,
                (
                    data.block_name.strip(),
                    data.gender_type,
                    data.total_rooms,
                    data.warden_name.strip(),
                    data.warden_contact.strip() if data.warden_contact else None,
                ),
            )
            block_id = cur.lastrowid

        return HostelService.get_block_by_id(conn, block_id)  # type: ignore

    @staticmethod
    def list_rooms(
        conn: sqlite3.Connection,
        block_id: Optional[int] = None,
        room_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[dict]:
        """List rooms with associated block details."""
        query = """
            SELECT r.id, r.block_id, r.room_number, r.room_type, r.capacity,
                   r.current_occupancy, r.floor, r.fee_per_semester, r.status,
                   r.created_at, b.block_name
            FROM hostel_rooms r
            JOIN hostel_blocks b ON r.block_id = b.id
            WHERE 1=1
        """
        params = []
        if block_id:
            query += " AND r.block_id = ?"
            params.append(block_id)
        if room_type:
            query += " AND r.room_type = ?"
            params.append(room_type)
        if status:
            query += " AND r.status = ?"
            params.append(status)

        query += " ORDER BY b.block_name ASC, r.floor ASC, r.room_number ASC;"

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_room_by_id(conn: sqlite3.Connection, room_id: int) -> Optional[dict]:
        """Retrieve a specific room by ID."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT r.*, b.block_name
            FROM hostel_rooms r
            JOIN hostel_blocks b ON r.block_id = b.id
            WHERE r.id = ?;
            """,
            (room_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

    @staticmethod
    def create_room(conn: sqlite3.Connection, data: HostelRoomCreate) -> dict:
        """Add a room to a hostel block."""
        block = HostelService.get_block_by_id(conn, data.block_id)
        if not block:
            raise ValueError(f"Block ID {data.block_id} does not exist.")

        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM hostel_rooms WHERE block_id = ? AND room_number = ?;",
            (data.block_id, data.room_number.strip()),
        )
        if cursor.fetchone():
            cursor.close()
            raise ValueError(
                f"Room {data.room_number} already exists in {block['block_name']}."
            )
        cursor.close()

        with transaction(conn) as cur:
            cur.execute(
                """
                INSERT INTO hostel_rooms (
                    block_id, room_number, room_type, capacity, current_occupancy,
                    floor, fee_per_semester, status
                ) VALUES (?, ?, ?, ?, 0, ?, ?, 'AVAILABLE');
                """,
                (
                    data.block_id,
                    data.room_number.strip(),
                    data.room_type,
                    data.capacity,
                    data.floor,
                    data.fee_per_semester,
                ),
            )
            room_id = cur.lastrowid

        return HostelService.get_room_by_id(conn, room_id)  # type: ignore

    @staticmethod
    def allocate_room(conn: sqlite3.Connection, data: RoomAllocationCreate) -> dict:
        """Assign a student to a room with capacity and duplicate check."""
        room = HostelService.get_room_by_id(conn, data.room_id)
        if not room:
            raise ValueError(f"Room ID {data.room_id} not found.")

        if room["status"] == "MAINTENANCE":
            raise ValueError(f"Room {room['room_number']} is currently under maintenance.")

        if room["current_occupancy"] >= room["capacity"]:
            raise ValueError(
                f"Room {room['room_number']} is already at full capacity ({room['capacity']} beds)."
            )

        # Validate student
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, first_name, last_name FROM students WHERE id = ?;",
            (data.student_id,),
        )
        student = cursor.fetchone()
        if not student:
            cursor.close()
            raise ValueError(f"Student ID {data.student_id} not found.")

        # Check existing active allocation
        cursor.execute(
            """
            SELECT id FROM room_allocations
            WHERE student_id = ? AND academic_year = ? AND status = 'ACTIVE';
            """,
            (data.student_id, data.academic_year),
        )
        if cursor.fetchone():
            cursor.close()
            raise ValueError(
                f"Student already has an active allocation for {data.academic_year}."
            )
        cursor.close()

        with transaction(conn) as cur:
            cur.execute(
                """
                INSERT INTO room_allocations (
                    room_id, student_id, academic_year, check_in_date, status, remarks
                ) VALUES (?, ?, ?, ?, 'ACTIVE', ?);
                """,
                (
                    data.room_id,
                    data.student_id,
                    data.academic_year,
                    data.check_in_date,
                    data.remarks,
                ),
            )
            alloc_id = cur.lastrowid

            new_occupancy = room["current_occupancy"] + 1
            new_status = "FULL" if new_occupancy >= room["capacity"] else "AVAILABLE"
            cur.execute(
                """
                UPDATE hostel_rooms
                SET current_occupancy = ?, status = ?
                WHERE id = ?;
                """,
                (new_occupancy, new_status, data.room_id),
            )

        allocations = HostelService.list_allocations(conn, status="ACTIVE")
        for a in allocations:
            if a["id"] == alloc_id:
                return a
        return {
            "id": alloc_id,
            "status": "ACTIVE",
            "room_id": data.room_id,
            "student_id": data.student_id,
        }

    @staticmethod
    def checkout_room(
        conn: sqlite3.Connection,
        allocation_id: int,
        data: RoomCheckoutRequest,
    ) -> dict:
        """Process check-out and free up bed in room."""
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM room_allocations WHERE id = ?;", (allocation_id,))
        allocation = cursor.fetchone()
        cursor.close()

        if not allocation:
            raise ValueError(f"Room allocation ID {allocation_id} not found.")

        if allocation["status"] != "ACTIVE":
            raise ValueError("Allocation is not active.")

        room_id = allocation["room_id"]

        with transaction(conn) as cur:
            cur.execute(
                """
                UPDATE room_allocations
                SET check_out_date = ?, status = 'CHECKED_OUT', remarks = ?
                WHERE id = ?;
                """,
                (data.check_out_date, data.remarks or allocation["remarks"], allocation_id),
            )

            cur.execute(
                """
                UPDATE hostel_rooms
                SET current_occupancy = MAX(0, current_occupancy - 1),
                    status = 'AVAILABLE'
                WHERE id = ?;
                """,
                (room_id,),
            )

        allocations = HostelService.list_allocations(conn)
        for a in allocations:
            if a["id"] == allocation_id:
                return a
        return {"id": allocation_id, "status": "CHECKED_OUT"}

    @staticmethod
    def list_allocations(
        conn: sqlite3.Connection,
        status: Optional[str] = None,
        block_id: Optional[int] = None,
        student_id: Optional[int] = None,
    ) -> List[dict]:
        """List allocations enriched with student, room, and block details."""
        query = """
            SELECT a.id, a.room_id, a.student_id, a.academic_year, a.check_in_date,
                   a.check_out_date, a.status, a.remarks, a.created_at,
                   r.room_number, b.block_name,
                   (s.first_name || ' ' || s.last_name) AS student_name, s.enrollment_no
            FROM room_allocations a
            JOIN hostel_rooms r ON a.room_id = r.id
            JOIN hostel_blocks b ON r.block_id = b.id
            JOIN students s ON a.student_id = s.id
            WHERE 1=1
        """
        params = []
        if status:
            query += " AND a.status = ?"
            params.append(status)
        if block_id:
            query += " AND r.block_id = ?"
            params.append(block_id)
        if student_id:
            query += " AND a.student_id = ?"
            params.append(student_id)

        query += " ORDER BY a.id DESC;"

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_stats(conn: sqlite3.Connection) -> Dict[str, int]:
        """Aggregate residential hall telemetry."""
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM hostel_blocks;")
        total_blocks = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*),
                   COALESCE(SUM(capacity), 0),
                   COALESCE(SUM(current_occupancy), 0)
            FROM hostel_rooms;
            """
        )
        total_rooms, total_beds, occupied_beds = cursor.fetchone()
        available_beds = max(0, total_beds - occupied_beds)

        cursor.execute("SELECT COUNT(*) FROM room_allocations WHERE status = 'ACTIVE';")
        active_residents = cursor.fetchone()[0]

        cursor.close()
        return {
            "total_blocks": total_blocks,
            "total_rooms": total_rooms,
            "total_beds": total_beds,
            "occupied_beds": occupied_beds,
            "available_beds": available_beds,
            "active_residents": active_residents,
        }
