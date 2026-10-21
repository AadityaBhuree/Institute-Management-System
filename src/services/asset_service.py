"""Campus Assets, Laboratory Equipment & Inventory Circulation Hub Service."""

import sqlite3
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from src.database.connection import transaction
from src.models.asset import (
    AssetCheckoutCreate,
    AssetCreate,
    AssetMaintenanceCreate,
    AssetMaintenanceStatusUpdate,
    AssetReturnUpdate,
    AssetUpdate,
)


class AssetService:
    @staticmethod
    def _generate_asset_tag(
        conn: sqlite3.Connection, department_id: Optional[int], purchase_date: str
    ) -> str:
        """Generate unique asset tag: AST-{DEPT_CODE}-{YEAR}-{XXXX}."""
        try:
            year = datetime.strptime(purchase_date, "%Y-%m-%d").year
        except ValueError:
            year = datetime.now().year

        dept_code = "GEN"
        if department_id:
            cursor = conn.cursor()
            cursor.execute("SELECT code FROM departments WHERE id = ?;", (department_id,))
            dept = cursor.fetchone()
            cursor.close()
            if dept and dept["code"]:
                dept_code = dept["code"].strip().upper()

        prefix = f"AST-{dept_code}-{year}-"
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM assets WHERE asset_tag LIKE ?;",
            (f"{prefix}%",),
        )
        count = cursor.fetchone()["cnt"] + 1
        cursor.close()

        tag = f"{prefix}{count:04d}"
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM assets WHERE asset_tag = ?;", (tag,))
        while cursor.fetchone():
            count += 1
            tag = f"{prefix}{count:04d}"
            cursor.execute("SELECT id FROM assets WHERE asset_tag = ?;", (tag,))
        cursor.close()
        return tag

    @staticmethod
    def _generate_checkout_code(conn: sqlite3.Connection, checkout_date: str) -> str:
        """Generate unique checkout slip: CHK-{YEAR}-{XXXX}."""
        try:
            year = datetime.strptime(checkout_date, "%Y-%m-%d").year
        except ValueError:
            year = datetime.now().year

        prefix = f"CHK-{year}-"
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM asset_checkouts WHERE checkout_code LIKE ?;",
            (f"{prefix}%",),
        )
        count = cursor.fetchone()["cnt"] + 1
        cursor.close()

        code = f"{prefix}{count:04d}"
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM asset_checkouts WHERE checkout_code = ?;", (code,))
        while cursor.fetchone():
            count += 1
            code = f"{prefix}{count:04d}"
            cursor.execute("SELECT id FROM asset_checkouts WHERE checkout_code = ?;", (code,))
        cursor.close()
        return code

    @staticmethod
    def _generate_maint_code(conn: sqlite3.Connection, scheduled_date: str) -> str:
        """Generate unique maintenance code: MNT-{YEAR}-{XXXX}."""
        try:
            year = datetime.strptime(scheduled_date, "%Y-%m-%d").year
        except ValueError:
            year = datetime.now().year

        prefix = f"MNT-{year}-"
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM asset_maintenance WHERE maintenance_code LIKE ?;",
            (f"{prefix}%",),
        )
        count = cursor.fetchone()["cnt"] + 1
        cursor.close()

        code = f"{prefix}{count:04d}"
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM asset_maintenance WHERE maintenance_code = ?;", (code,))
        while cursor.fetchone():
            count += 1
            code = f"{prefix}{count:04d}"
            cursor.execute("SELECT id FROM asset_maintenance WHERE maintenance_code = ?;", (code,))
        cursor.close()
        return code

    @staticmethod
    def list_assets(
        conn: sqlite3.Connection,
        category: Optional[str] = None,
        status: Optional[str] = None,
        department_id: Optional[int] = None,
        lab_room: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List equipment and campus assets with department information and current status."""
        query = """
            SELECT a.id, a.asset_tag, a.name, a.category, a.department_id,
                   a.lab_room, a.serial_number, a.model_number, a.manufacturer,
                   a.purchase_date, a.purchase_cost, a.warranty_expiry, a.status,
                   a.created_at,
                   d.name AS department_name,
                   d.code AS department_code
            FROM assets a
            LEFT JOIN departments d ON a.department_id = d.id
            WHERE 1=1
        """
        params: List[Any] = []
        if category:
            query += " AND a.category = ?"
            params.append(category)
        if status:
            query += " AND a.status = ?"
            params.append(status)
        if department_id:
            query += " AND a.department_id = ?"
            params.append(department_id)
        if lab_room:
            query += " AND a.lab_room LIKE ?"
            params.append(f"%{lab_room.strip()}%")
        if search:
            term = f"%{search.strip()}%"
            query += " AND (a.name LIKE ? OR a.asset_tag LIKE ? OR a.serial_number LIKE ? OR a.lab_room LIKE ?)"
            params.extend([term, term, term, term])

        query += " ORDER BY a.id DESC;"
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_asset_by_id(conn: sqlite3.Connection, asset_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve single asset details with current checkouts and maintenance history."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT a.id, a.asset_tag, a.name, a.category, a.department_id,
                   a.lab_room, a.serial_number, a.model_number, a.manufacturer,
                   a.purchase_date, a.purchase_cost, a.warranty_expiry, a.status,
                   a.created_at,
                   d.name AS department_name,
                   d.code AS department_code
            FROM assets a
            LEFT JOIN departments d ON a.department_id = d.id
            WHERE a.id = ?;
            """,
            (asset_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        if not row:
            return None

        asset = dict(row)
        # Fetch checkouts for this asset
        asset["checkouts"] = AssetService.list_checkouts(conn, asset_id=asset_id, limit=20)
        # Fetch maintenance records for this asset
        asset["maintenance"] = AssetService.list_maintenance(conn, asset_id=asset_id, limit=20)
        return asset

    @staticmethod
    def create_asset(conn: sqlite3.Connection, data: AssetCreate) -> Dict[str, Any]:
        """Register a new institutional asset or laboratory instrument."""
        if data.department_id:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM departments WHERE id = ?;", (data.department_id,))
            if not cursor.fetchone():
                cursor.close()
                raise ValueError(f"Department ID {data.department_id} does not exist.")
            cursor.close()

        if data.serial_number and data.serial_number.strip():
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM assets WHERE serial_number = ?;",
                (data.serial_number.strip(),),
            )
            if cursor.fetchone():
                cursor.close()
                raise ValueError(
                    f"Asset with serial number '{data.serial_number.strip()}' is already registered."
                )
            cursor.close()

        asset_tag = AssetService._generate_asset_tag(conn, data.department_id, data.purchase_date)

        with transaction(conn) as cursor:
            cursor.execute(
                """
                INSERT INTO assets (
                    asset_tag, name, category, department_id, lab_room,
                    serial_number, model_number, manufacturer, purchase_date,
                    purchase_cost, warranty_expiry, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    asset_tag,
                    data.name.strip(),
                    data.category,
                    data.department_id,
                    data.lab_room.strip(),
                    data.serial_number.strip() if data.serial_number else None,
                    data.model_number.strip() if data.model_number else None,
                    data.manufacturer.strip() if data.manufacturer else None,
                    data.purchase_date,
                    data.purchase_cost,
                    data.warranty_expiry,
                    data.status,
                ),
            )
            asset_id = cursor.lastrowid

        created = AssetService.get_asset_by_id(conn, asset_id)  # type: ignore
        return created  # type: ignore

    @staticmethod
    def update_asset(conn: sqlite3.Connection, asset_id: int, data: AssetUpdate) -> Dict[str, Any]:
        """Update asset location, specifications, or lifecycle status."""
        asset = AssetService.get_asset_by_id(conn, asset_id)
        if not asset:
            raise ValueError(f"Asset ID {asset_id} does not exist.")

        fields: List[str] = []
        values: List[Any] = []

        if data.name is not None:
            fields.append("name = ?")
            values.append(data.name.strip())
        if data.lab_room is not None:
            fields.append("lab_room = ?")
            values.append(data.lab_room.strip())
        if data.status is not None:
            fields.append("status = ?")
            values.append(data.status)
        if data.warranty_expiry is not None:
            fields.append("warranty_expiry = ?")
            values.append(data.warranty_expiry)
        if data.model_number is not None:
            fields.append("model_number = ?")
            values.append(data.model_number.strip())
        if data.manufacturer is not None:
            fields.append("manufacturer = ?")
            values.append(data.manufacturer.strip())

        if fields:
            values.append(asset_id)
            query = f"UPDATE assets SET {', '.join(fields)} WHERE id = ?;"
            with transaction(conn) as cursor:
                cursor.execute(query, values)

        return AssetService.get_asset_by_id(conn, asset_id)  # type: ignore

    @staticmethod
    def checkout_asset(conn: sqlite3.Connection, data: AssetCheckoutCreate) -> Dict[str, Any]:
        """Checkout an asset to a student or faculty member."""
        asset = AssetService.get_asset_by_id(conn, data.asset_id)
        if not asset:
            raise ValueError(f"Asset ID {data.asset_id} not found.")

        if asset["status"] != "AVAILABLE":
            raise ValueError(
                f"Asset '{asset['name']}' ({asset['asset_tag']}) is currently {asset['status']} and cannot be checked out."
            )

        if data.due_date < data.checkout_date:
            raise ValueError(
                f"Due date '{data.due_date}' cannot be earlier than checkout date '{data.checkout_date}'."
            )

        cursor = conn.cursor()
        if data.borrower_type == "STUDENT":
            if not data.student_id:
                cursor.close()
                raise ValueError("Student ID is required for student checkout.")
            cursor.execute(
                "SELECT id, first_name, last_name, enrollment_no, status FROM students WHERE id = ?;",
                (data.student_id,),
            )
            student = cursor.fetchone()
            if not student:
                cursor.close()
                raise ValueError(f"Student ID {data.student_id} not found.")
            if student["status"] in ("WITHDRAWN", "SUSPENDED"):
                cursor.close()
                raise ValueError(
                    f"Student {student['first_name']} {student['last_name']} has status '{student['status']}' and cannot borrow campus equipment."
                )
        elif data.borrower_type == "FACULTY":
            if not data.faculty_id:
                cursor.close()
                raise ValueError("Faculty ID is required for faculty checkout.")
            cursor.execute(
                "SELECT id, first_name, last_name, faculty_id, status FROM faculty WHERE id = ?;",
                (data.faculty_id,),
            )
            faculty = cursor.fetchone()
            if not faculty:
                cursor.close()
                raise ValueError(f"Faculty ID {data.faculty_id} not found.")
            if faculty["status"] != "ACTIVE":
                cursor.close()
                raise ValueError(
                    f"Faculty {faculty['first_name']} {faculty['last_name']} is not active and cannot borrow equipment."
                )
        cursor.close()

        checkout_code = AssetService._generate_checkout_code(conn, data.checkout_date)

        with transaction(conn) as cursor:
            cursor.execute(
                """
                INSERT INTO asset_checkouts (
                    checkout_code, asset_id, borrower_type, student_id, faculty_id,
                    checkout_date, due_date, condition_out, status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?);
                """,
                (
                    checkout_code,
                    data.asset_id,
                    data.borrower_type,
                    data.student_id if data.borrower_type == "STUDENT" else None,
                    data.faculty_id if data.borrower_type == "FACULTY" else None,
                    data.checkout_date,
                    data.due_date,
                    data.condition_out,
                    data.notes.strip() if data.notes else None,
                ),
            )
            checkout_id = cursor.lastrowid

            cursor.execute(
                "UPDATE assets SET status = 'CHECKED_OUT' WHERE id = ?;",
                (data.asset_id,),
            )

        checkouts = AssetService.list_checkouts(conn, limit=50)
        for c in checkouts:
            if c["id"] == checkout_id:
                return c
        return {"id": checkout_id, "checkout_code": checkout_code, "status": "ACTIVE"}

    @staticmethod
    def return_asset(
        conn: sqlite3.Connection, checkout_id: int, data: AssetReturnUpdate
    ) -> Dict[str, Any]:
        """Process return of an asset with condition inspection."""
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM asset_checkouts WHERE id = ?;", (checkout_id,))
        checkout = cursor.fetchone()
        cursor.close()

        if not checkout:
            raise ValueError(f"Checkout slip ID {checkout_id} not found.")

        if checkout["status"] == "RETURNED":
            raise ValueError("This checkout has already been returned.")

        asset_id = checkout["asset_id"]
        ret_date = data.returned_date or date.today().isoformat()
        cond_in = data.condition_in

        # If returned in damaged condition, move asset to MAINTENANCE; else back to AVAILABLE
        new_asset_status = "MAINTENANCE" if cond_in == "DAMAGED" else "AVAILABLE"

        with transaction(conn) as cursor:
            cursor.execute(
                """
                UPDATE asset_checkouts
                SET returned_date = ?, condition_in = ?, status = 'RETURNED', notes = COALESCE(?, notes)
                WHERE id = ?;
                """,
                (
                    ret_date,
                    cond_in,
                    data.notes.strip() if data.notes else None,
                    checkout_id,
                ),
            )

            cursor.execute(
                "UPDATE assets SET status = ? WHERE id = ?;",
                (new_asset_status, asset_id),
            )

        checkouts = AssetService.list_checkouts(conn, limit=50)
        for c in checkouts:
            if c["id"] == checkout_id:
                return c
        return {"id": checkout_id, "status": "RETURNED", "condition_in": cond_in}

    @staticmethod
    def schedule_maintenance(
        conn: sqlite3.Connection, data: AssetMaintenanceCreate
    ) -> Dict[str, Any]:
        """Schedule calibration, preventative servicing, or equipment repair."""
        asset = AssetService.get_asset_by_id(conn, data.asset_id)
        if not asset:
            raise ValueError(f"Asset ID {data.asset_id} not found.")

        if asset["status"] == "CHECKED_OUT":
            raise ValueError(
                f"Asset '{asset['name']}' is currently checked out to a borrower and cannot enter maintenance until returned."
            )

        maint_code = AssetService._generate_maint_code(conn, data.scheduled_date)

        with transaction(conn) as cursor:
            cursor.execute(
                """
                INSERT INTO asset_maintenance (
                    maintenance_code, asset_id, maintenance_type, scheduled_date,
                    technician_name, cost, status, resolution_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    maint_code,
                    data.asset_id,
                    data.maintenance_type,
                    data.scheduled_date,
                    data.technician_name.strip(),
                    data.cost,
                    data.status,
                    data.resolution_notes.strip() if data.resolution_notes else None,
                ),
            )
            maint_id = cursor.lastrowid

            if data.status in ("IN_PROGRESS", "SCHEDULED"):
                # Transition asset to MAINTENANCE if starting now
                if data.status == "IN_PROGRESS":
                    cursor.execute(
                        "UPDATE assets SET status = 'MAINTENANCE' WHERE id = ?;",
                        (data.asset_id,),
                    )

        records = AssetService.list_maintenance(conn, limit=50)
        for r in records:
            if r["id"] == maint_id:
                return r
        return {"id": maint_id, "maintenance_code": maint_code, "status": data.status}

    @staticmethod
    def update_maintenance_status(
        conn: sqlite3.Connection,
        maintenance_id: int,
        data: AssetMaintenanceStatusUpdate,
    ) -> Dict[str, Any]:
        """Update maintenance record status and return asset to service upon completion."""
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM asset_maintenance WHERE id = ?;", (maintenance_id,))
        record = cursor.fetchone()
        cursor.close()

        if not record:
            raise ValueError(f"Maintenance ticket ID {maintenance_id} not found.")

        asset_id = record["asset_id"]
        fields: List[str] = ["status = ?"]
        values: List[Any] = [data.status]

        if data.completed_date is not None:
            fields.append("completed_date = ?")
            values.append(data.completed_date)
        elif data.status == "COMPLETED" and not record["completed_date"]:
            fields.append("completed_date = ?")
            values.append(date.today().isoformat())

        if data.cost is not None:
            fields.append("cost = ?")
            values.append(data.cost)
        if data.resolution_notes is not None:
            fields.append("resolution_notes = ?")
            values.append(data.resolution_notes.strip())

        values.append(maintenance_id)

        with transaction(conn) as cursor:
            cursor.execute(
                f"UPDATE asset_maintenance SET {', '.join(fields)} WHERE id = ?;",
                values,
            )

            if data.status == "IN_PROGRESS":
                cursor.execute(
                    "UPDATE assets SET status = 'MAINTENANCE' WHERE id = ?;",
                    (asset_id,),
                )
            elif data.status == "COMPLETED":
                # Restore to AVAILABLE
                cursor.execute(
                    "UPDATE assets SET status = 'AVAILABLE' WHERE id = ?;",
                    (asset_id,),
                )
            elif data.status == "CANCELLED":
                cursor.execute(
                    "UPDATE assets SET status = 'AVAILABLE' WHERE id = ? AND status = 'MAINTENANCE';",
                    (asset_id,),
                )

        records = AssetService.list_maintenance(conn, limit=50)
        for r in records:
            if r["id"] == maintenance_id:
                return r
        return {"id": maintenance_id, "status": data.status}

    @staticmethod
    def list_checkouts(
        conn: sqlite3.Connection,
        status: Optional[str] = None,
        asset_id: Optional[int] = None,
        student_id: Optional[int] = None,
        faculty_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List equipment checkouts with borrower details and overdue indicators."""
        today_str = date.today().isoformat()
        query = """
            SELECT c.id, c.checkout_code, c.asset_id, c.borrower_type,
                   c.student_id, c.faculty_id, c.checkout_date, c.due_date,
                   c.returned_date, c.condition_out, c.condition_in, c.status,
                   c.notes, c.created_at,
                   a.asset_tag, a.name AS asset_name,
                   CASE
                       WHEN c.borrower_type = 'STUDENT' THEN (s.first_name || ' ' || s.last_name)
                       ELSE (f.first_name || ' ' || f.last_name)
                   END AS borrower_name,
                   CASE
                       WHEN c.borrower_type = 'STUDENT' THEN s.enrollment_no
                       ELSE f.faculty_id
                   END AS borrower_identifier,
                   CASE
                       WHEN c.status = 'ACTIVE' AND c.due_date < ? THEN 1
                       ELSE 0
                   END AS is_overdue
            FROM asset_checkouts c
            JOIN assets a ON c.asset_id = a.id
            LEFT JOIN students s ON c.student_id = s.id
            LEFT JOIN faculty f ON c.faculty_id = f.id
            WHERE 1=1
        """
        params: List[Any] = [today_str]
        if status:
            query += " AND c.status = ?"
            params.append(status)
        if asset_id:
            query += " AND c.asset_id = ?"
            params.append(asset_id)
        if student_id:
            query += " AND c.student_id = ?"
            params.append(student_id)
        if faculty_id:
            query += " AND c.faculty_id = ?"
            params.append(faculty_id)

        query += " ORDER BY c.id DESC LIMIT ?;"
        params.append(limit)

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()

        results = []
        for row in rows:
            d = dict(row)
            d["is_overdue"] = bool(d["is_overdue"])
            results.append(d)
        return results

    @staticmethod
    def list_maintenance(
        conn: sqlite3.Connection,
        status: Optional[str] = None,
        asset_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List maintenance tickets with equipment information."""
        query = """
            SELECT m.id, m.maintenance_code, m.asset_id, m.maintenance_type,
                   m.scheduled_date, m.completed_date, m.technician_name,
                   m.cost, m.status, m.resolution_notes, m.created_at,
                   a.asset_tag, a.name AS asset_name
            FROM asset_maintenance m
            JOIN assets a ON m.asset_id = a.id
            WHERE 1=1
        """
        params: List[Any] = []
        if status:
            query += " AND m.status = ?"
            params.append(status)
        if asset_id:
            query += " AND m.asset_id = ?"
            params.append(asset_id)

        query += " ORDER BY m.id DESC LIMIT ?;"
        params.append(limit)

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_stats(conn: sqlite3.Connection) -> Dict[str, Any]:
        """Calculate inventory telemetry KPIs and active risk metrics."""
        today_str = date.today().isoformat()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_assets,
                COALESCE(SUM(purchase_cost), 0.0) AS total_valuation,
                COUNT(CASE WHEN status = 'AVAILABLE' THEN 1 END) AS available_assets,
                COUNT(CASE WHEN status = 'CHECKED_OUT' THEN 1 END) AS active_checkouts,
                COUNT(CASE WHEN status = 'MAINTENANCE' THEN 1 END) AS in_maintenance
            FROM assets;
            """
        )
        row = cursor.fetchone()
        stats = (
            dict(row)
            if row
            else {
                "total_assets": 0,
                "total_valuation": 0.0,
                "available_assets": 0,
                "active_checkouts": 0,
                "in_maintenance": 0,
            }
        )

        # Calculate overdue checkouts
        cursor.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM asset_checkouts
            WHERE status = 'ACTIVE' AND due_date < ?;
            """,
            (today_str,),
        )
        overdue_cnt = cursor.fetchone()["cnt"]
        stats["overdue_checkouts"] = overdue_cnt
        cursor.close()
        return stats
