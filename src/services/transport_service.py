"""Campus Transport Fleet & Transit Logistics Service."""

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.database.connection import transaction
from src.models.transport import (
    TransportPassCreate,
    TransportRouteCreate,
    TransportVehicleCreate,
)


class TransportService:
    @staticmethod
    def list_routes(conn: sqlite3.Connection, status: Optional[str] = None) -> List[dict]:
        """List transport routes with assigned vehicles and active passes count."""
        query = """
            SELECT r.id, r.route_name, r.source, r.destination, r.total_stops,
                   r.fare_per_semester, r.status, r.created_at,
                   COUNT(DISTINCT v.id) AS assigned_vehicles_count,
                   COUNT(DISTINCT p.id) AS active_passes_count
            FROM transport_routes r
            LEFT JOIN transport_vehicles v ON r.id = v.route_id
            LEFT JOIN transport_passes p ON r.id = p.route_id AND p.status = 'ACTIVE'
            WHERE 1=1
        """
        params = []
        if status:
            query += " AND r.status = ?"
            params.append(status)

        query += " GROUP BY r.id ORDER BY r.route_name ASC;"
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_route_by_id(conn: sqlite3.Connection, route_id: int) -> Optional[dict]:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transport_routes WHERE id = ?;", (route_id,))
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

    @staticmethod
    def create_route(conn: sqlite3.Connection, data: TransportRouteCreate) -> dict:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM transport_routes WHERE route_name = ?;",
            (data.route_name.strip(),),
        )
        if cursor.fetchone():
            cursor.close()
            raise ValueError(f"Route '{data.route_name}' already exists.")
        cursor.close()

        with transaction(conn) as cur:
            cur.execute(
                """
                INSERT INTO transport_routes (
                    route_name, source, destination, total_stops, fare_per_semester, status
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    data.route_name.strip(),
                    data.source.strip(),
                    data.destination.strip(),
                    data.total_stops,
                    data.fare_per_semester,
                    data.status,
                ),
            )
            route_id = cur.lastrowid

        return TransportService.get_route_by_id(conn, route_id)  # type: ignore

    @staticmethod
    def list_vehicles(
        conn: sqlite3.Connection,
        route_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[dict]:
        query = """
            SELECT v.id, v.route_id, v.vehicle_number, v.driver_name, v.driver_phone,
                   v.capacity, v.status, v.created_at, r.route_name
            FROM transport_vehicles v
            LEFT JOIN transport_routes r ON v.route_id = r.id
            WHERE 1=1
        """
        params = []
        if route_id:
            query += " AND v.route_id = ?"
            params.append(route_id)
        if status:
            query += " AND v.status = ?"
            params.append(status)

        query += " ORDER BY v.vehicle_number ASC;"
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_vehicle_by_id(conn: sqlite3.Connection, vehicle_id: int) -> Optional[dict]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT v.*, r.route_name
            FROM transport_vehicles v
            LEFT JOIN transport_routes r ON v.route_id = r.id
            WHERE v.id = ?;
            """,
            (vehicle_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

    @staticmethod
    def create_vehicle(conn: sqlite3.Connection, data: TransportVehicleCreate) -> dict:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM transport_vehicles WHERE vehicle_number = ?;",
            (data.vehicle_number.strip().upper(),),
        )
        if cursor.fetchone():
            cursor.close()
            raise ValueError(f"Vehicle '{data.vehicle_number}' is already registered in the fleet.")

        if data.route_id:
            cursor.execute("SELECT id FROM transport_routes WHERE id = ?;", (data.route_id,))
            if not cursor.fetchone():
                cursor.close()
                raise ValueError(f"Route ID {data.route_id} does not exist.")
        cursor.close()

        with transaction(conn) as cur:
            cur.execute(
                """
                INSERT INTO transport_vehicles (
                    route_id, vehicle_number, driver_name, driver_phone, capacity, status
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    data.route_id,
                    data.vehicle_number.strip().upper(),
                    data.driver_name.strip(),
                    data.driver_phone.strip(),
                    data.capacity,
                    data.status,
                ),
            )
            vehicle_id = cur.lastrowid

        return TransportService.get_vehicle_by_id(conn, vehicle_id)  # type: ignore

    @staticmethod
    def issue_transit_pass(conn: sqlite3.Connection, data: TransportPassCreate) -> dict:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, first_name, last_name, enrollment_no FROM students WHERE id = ?;",
            (data.student_id,),
        )
        student = cursor.fetchone()
        if not student:
            cursor.close()
            raise ValueError(f"Student ID {data.student_id} not found.")

        cursor.execute(
            "SELECT id, route_name, status FROM transport_routes WHERE id = ?;",
            (data.route_id,),
        )
        route = cursor.fetchone()
        if not route:
            cursor.close()
            raise ValueError(f"Route ID {data.route_id} not found.")
        if route["status"] != "ACTIVE":
            cursor.close()
            raise ValueError(f"Route '{route['route_name']}' is currently inactive.")

        # Check existing active pass for same academic year
        cursor.execute(
            """
            SELECT id FROM transport_passes
            WHERE student_id = ? AND academic_year = ? AND status = 'ACTIVE';
            """,
            (data.student_id, data.academic_year),
        )
        if cursor.fetchone():
            cursor.close()
            raise ValueError(
                f"Student already has an active transit pass for academic year {data.academic_year}."
            )

        year = datetime.now().year
        cursor.execute("SELECT COUNT(id) FROM transport_passes;")
        count = cursor.fetchone()[0] + 1
        pass_number = f"PASS-{year}-{count:04d}"
        cursor.close()

        with transaction(conn) as cur:
            cur.execute(
                """
                INSERT INTO transport_passes (
                    student_id, route_id, pass_number, pickup_stop, academic_year, valid_until, status
                ) VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE');
                """,
                (
                    data.student_id,
                    data.route_id,
                    pass_number,
                    data.pickup_stop.strip(),
                    data.academic_year.strip(),
                    data.valid_until,
                ),
            )
            pass_id = cur.lastrowid

        passes = TransportService.list_passes(conn)
        for p in passes:
            if p["id"] == pass_id:
                return p
        return {"id": pass_id, "pass_number": pass_number, "status": "ACTIVE"}

    @staticmethod
    def list_passes(
        conn: sqlite3.Connection,
        route_id: Optional[int] = None,
        student_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[dict]:
        query = """
            SELECT p.id, p.student_id, p.route_id, p.pass_number, p.pickup_stop,
                   p.academic_year, p.valid_until, p.status, p.created_at,
                   s.first_name || ' ' || s.last_name AS student_name,
                   s.enrollment_no, d.code AS department_code,
                   r.route_name
            FROM transport_passes p
            JOIN students s ON p.student_id = s.id
            JOIN departments d ON s.department_id = d.id
            JOIN transport_routes r ON p.route_id = r.id
            WHERE 1=1
        """
        params = []
        if route_id:
            query += " AND p.route_id = ?"
            params.append(route_id)
        if student_id:
            query += " AND p.student_id = ?"
            params.append(student_id)
        if status:
            query += " AND p.status = ?"
            params.append(status)

        query += " ORDER BY p.created_at DESC;"
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def cancel_pass(conn: sqlite3.Connection, pass_id: int) -> bool:
        with transaction(conn) as cur:
            cur.execute(
                "UPDATE transport_passes SET status = 'CANCELLED' WHERE id = ?;",
                (pass_id,),
            )
            return cur.rowcount > 0

    @staticmethod
    def get_stats(conn: sqlite3.Connection) -> Dict[str, Any]:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(id) FROM transport_routes;")
        total_routes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(id) FROM transport_routes WHERE status = 'ACTIVE';")
        active_routes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(id), COALESCE(SUM(capacity), 0) FROM transport_vehicles;")
        v_row = cursor.fetchone()
        total_vehicles = v_row[0]
        total_capacity = v_row[1]

        cursor.execute("SELECT COUNT(id) FROM transport_passes WHERE status = 'ACTIVE';")
        active_passes = cursor.fetchone()[0]
        cursor.close()

        occupancy_pct = (
            round((active_passes / total_capacity) * 100, 1) if total_capacity > 0 else 0.0
        )

        return {
            "total_routes": total_routes,
            "active_routes": active_routes,
            "total_vehicles": total_vehicles,
            "active_passes": active_passes,
            "total_capacity": total_capacity,
            "fleet_occupancy_pct": occupancy_pct,
        }
