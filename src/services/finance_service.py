"""Financial database service for fee structures, invoices, payments, and audit ledgers."""

import datetime
import sqlite3
import uuid
from typing import Any, Dict, List, Optional

from src.database.connection import transaction
from src.models.finance import FeeInvoiceCreate, FeeStructureCreate, PaymentCreate


class FinanceService:
    @staticmethod
    def _sync_overdue_invoices(conn: sqlite3.Connection) -> None:
        """Mark invoices past due date as OVERDUE if not already PAID or CANCELLED."""
        today_str = datetime.date.today().isoformat()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE fee_invoices
            SET status = 'OVERDUE'
            WHERE status IN ('UNPAID', 'PARTIAL')
              AND due_date < ?;
            """,
            (today_str,),
        )
        conn.commit()
        cursor.close()

    @staticmethod
    def create_fee_structure(
        conn: sqlite3.Connection, fee_in: FeeStructureCreate
    ) -> Dict[str, Any]:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM departments WHERE id = ?;", (fee_in.department_id,))
        dept_row = cursor.fetchone()
        if not dept_row:
            cursor.close()
            raise ValueError(f"Department ID {fee_in.department_id} does not exist.")

        try:
            with transaction(conn) as t_cursor:
                t_cursor.execute(
                    """
                    INSERT INTO fee_structures (
                        department_id, semester, fee_type, amount, academic_year
                    ) VALUES (?, ?, ?, ?, ?);
                    """,
                    (
                        fee_in.department_id,
                        fee_in.semester,
                        fee_in.fee_type,
                        fee_in.amount,
                        fee_in.academic_year,
                    ),
                )
                struct_id = t_cursor.lastrowid
        except sqlite3.IntegrityError as err:
            raise ValueError(
                f"Fee structure for dept {fee_in.department_id}, sem {fee_in.semester}, "
                f"type '{fee_in.fee_type}' already exists for {fee_in.academic_year}."
            ) from err

        return {
            "id": struct_id,
            "department_id": fee_in.department_id,
            "department_name": dept_row["name"],
            "semester": fee_in.semester,
            "fee_type": fee_in.fee_type,
            "amount": fee_in.amount,
            "academic_year": fee_in.academic_year,
        }

    @staticmethod
    def list_fee_structures(
        conn: sqlite3.Connection,
        department_id: Optional[int] = None,
        semester: Optional[int] = None,
        academic_year: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        query = """
            SELECT fs.*, d.name AS department_name
            FROM fee_structures fs
            JOIN departments d ON fs.department_id = d.id
            WHERE 1=1
        """
        params: List[Any] = []
        if department_id:
            query += " AND fs.department_id = ?"
            params.append(department_id)
        if semester:
            query += " AND fs.semester = ?"
            params.append(semester)
        if academic_year:
            query += " AND fs.academic_year = ?"
            params.append(academic_year)

        query += " ORDER BY fs.department_id ASC, fs.semester ASC, fs.id ASC;"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(r) for r in rows]

    @staticmethod
    def create_invoice(
        conn: sqlite3.Connection, invoice_in: FeeInvoiceCreate
    ) -> Dict[str, Any]:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, first_name, last_name, enrollment_no FROM students WHERE id = ?;",
            (invoice_in.student_id,),
        )
        student_row = cursor.fetchone()
        if not student_row:
            cursor.close()
            raise ValueError(f"Student ID {invoice_in.student_id} does not exist.")

        today_str = datetime.date.today().isoformat()
        # Generate clean human-readable invoice identifier
        unique_token = uuid.uuid4().hex[:6].upper()
        invoice_no = f"INV-2026-{unique_token}"

        status = "OVERDUE" if invoice_in.due_date < today_str else "UNPAID"

        with transaction(conn) as t_cursor:
            t_cursor.execute(
                """
                INSERT INTO fee_invoices (
                    invoice_no, student_id, title, term_name, total_amount,
                    paid_amount, balance_amount, status, due_date, issued_date
                ) VALUES (?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?);
                """,
                (
                    invoice_no,
                    invoice_in.student_id,
                    invoice_in.title,
                    invoice_in.term_name,
                    invoice_in.total_amount,
                    invoice_in.total_amount,
                    status,
                    invoice_in.due_date,
                    today_str,
                ),
            )
            inv_id = t_cursor.lastrowid

        student_name = f"{student_row['first_name']} {student_row['last_name']}"
        return {
            "id": inv_id,
            "invoice_no": invoice_no,
            "student_id": invoice_in.student_id,
            "student_name": student_name,
            "enrollment_no": student_row["enrollment_no"],
            "title": invoice_in.title,
            "term_name": invoice_in.term_name,
            "total_amount": invoice_in.total_amount,
            "paid_amount": 0.0,
            "balance_amount": invoice_in.total_amount,
            "status": status,
            "due_date": invoice_in.due_date,
            "issued_date": today_str,
        }

    @staticmethod
    def list_invoices(
        conn: sqlite3.Connection,
        student_id: Optional[int] = None,
        status: Optional[str] = None,
        department_id: Optional[int] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        FinanceService._sync_overdue_invoices(conn)
        cursor = conn.cursor()
        query = """
            SELECT fi.*,
                   s.first_name || ' ' || s.last_name AS student_name,
                   s.enrollment_no,
                   d.name AS department_name
            FROM fee_invoices fi
            JOIN students s ON fi.student_id = s.id
            JOIN departments d ON s.department_id = d.id
            WHERE 1=1
        """
        params: List[Any] = []
        if student_id:
            query += " AND fi.student_id = ?"
            params.append(student_id)
        if status:
            query += " AND fi.status = ?"
            params.append(status.upper())
        if department_id:
            query += " AND s.department_id = ?"
            params.append(department_id)
        if search:
            query += (
                " AND (fi.invoice_no LIKE ? OR s.first_name LIKE ? "
                "OR s.last_name LIKE ? OR s.enrollment_no LIKE ?)"
            )
            term = f"%{search}%"
            params.extend([term, term, term, term])

        query += " ORDER BY fi.created_at DESC, fi.id DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_invoice_by_id(
        conn: sqlite3.Connection, invoice_id: int
    ) -> Optional[Dict[str, Any]]:
        FinanceService._sync_overdue_invoices(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT fi.*,
                   s.first_name || ' ' || s.last_name AS student_name,
                   s.enrollment_no,
                   d.name AS department_name
            FROM fee_invoices fi
            JOIN students s ON fi.student_id = s.id
            JOIN departments d ON s.department_id = d.id
            WHERE fi.id = ?;
            """,
            (invoice_id,),
        )
        row = cursor.fetchone()
        if not row:
            cursor.close()
            return None

        invoice_dict = dict(row)

        cursor.execute(
            """
            SELECT * FROM fee_payments
            WHERE invoice_id = ?
            ORDER BY payment_date DESC, id DESC;
            """,
            (invoice_id,),
        )
        payment_rows = cursor.fetchall()
        cursor.close()
        invoice_dict["payments"] = [dict(p) for p in payment_rows]
        return invoice_dict

    @staticmethod
    def record_payment(
        conn: sqlite3.Connection, payment_in: PaymentCreate
    ) -> Dict[str, Any]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT fi.*, s.first_name || ' ' || s.last_name AS student_name
            FROM fee_invoices fi
            JOIN students s ON fi.student_id = s.id
            WHERE fi.id = ?;
            """,
            (payment_in.invoice_id,),
        )
        invoice = cursor.fetchone()
        if not invoice:
            cursor.close()
            raise ValueError(f"Invoice ID {payment_in.invoice_id} does not exist.")

        if invoice["status"] == "PAID" or invoice["balance_amount"] <= 0.001:
            cursor.close()
            raise ValueError(f"Invoice {invoice['invoice_no']} is already fully settled.")

        if payment_in.amount > invoice["balance_amount"]:
            cursor.close()
            raise ValueError(
                f"Payment amount (${payment_in.amount:.2f}) exceeds outstanding balance "
                f"(${invoice['balance_amount']:.2f})."
            )

        unique_token = uuid.uuid4().hex[:6].upper()
        payment_no = f"REC-2026-{unique_token}"

        new_paid = round(invoice["paid_amount"] + payment_in.amount, 2)
        new_balance = max(0.0, round(invoice["balance_amount"] - payment_in.amount, 2))
        new_status = "PAID" if new_balance <= 0.001 else "PARTIAL"

        with transaction(conn) as t_cursor:
            t_cursor.execute(
                """
                INSERT INTO fee_payments (
                    invoice_id, payment_no, amount, payment_method,
                    transaction_ref, notes, received_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    payment_in.invoice_id,
                    payment_no,
                    payment_in.amount,
                    payment_in.payment_method.upper(),
                    payment_in.transaction_ref,
                    payment_in.notes,
                    payment_in.received_by or "Bursar Counter",
                ),
            )
            pay_id = t_cursor.lastrowid

            t_cursor.execute(
                """
                UPDATE fee_invoices
                SET paid_amount = ?, balance_amount = ?, status = ?
                WHERE id = ?;
                """,
                (new_paid, new_balance, new_status, payment_in.invoice_id),
            )

        cursor.close()
        return {
            "id": pay_id,
            "payment_no": payment_no,
            "invoice_id": payment_in.invoice_id,
            "invoice_no": invoice["invoice_no"],
            "student_name": invoice["student_name"],
            "amount": payment_in.amount,
            "payment_method": payment_in.payment_method.upper(),
            "transaction_ref": payment_in.transaction_ref,
            "notes": payment_in.notes,
            "received_by": payment_in.received_by or "Bursar Counter",
            "payment_date": datetime.datetime.now().isoformat(),
            "new_balance": new_balance,
            "invoice_status": new_status,
        }

    @staticmethod
    def list_payments(
        conn: sqlite3.Connection,
        invoice_id: Optional[int] = None,
        student_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        query = """
            SELECT fp.*,
                   fi.invoice_no,
                   s.first_name || ' ' || s.last_name AS student_name,
                   s.enrollment_no
            FROM fee_payments fp
            JOIN fee_invoices fi ON fp.invoice_id = fi.id
            JOIN students s ON fi.student_id = s.id
            WHERE 1=1
        """
        params: List[Any] = []
        if invoice_id:
            query += " AND fp.invoice_id = ?"
            params.append(invoice_id)
        if student_id:
            query += " AND fi.student_id = ?"
            params.append(student_id)

        query += " ORDER BY fp.payment_date DESC, fp.id DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_financial_summary(conn: sqlite3.Connection) -> Dict[str, Any]:
        FinanceService._sync_overdue_invoices(conn)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                COALESCE(SUM(total_amount), 0.0) AS total_billed,
                COALESCE(SUM(paid_amount), 0.0) AS total_collected,
                COALESCE(SUM(balance_amount), 0.0) AS total_outstanding,
                COUNT(id) AS total_invoices,
                SUM(CASE WHEN status = 'PAID' THEN 1 ELSE 0 END) AS paid_count,
                SUM(CASE WHEN status = 'PARTIAL' THEN 1 ELSE 0 END) AS partial_count,
                SUM(CASE WHEN status = 'UNPAID' THEN 1 ELSE 0 END) AS unpaid_count,
                SUM(CASE WHEN status = 'OVERDUE' THEN 1 ELSE 0 END) AS overdue_count
            FROM fee_invoices;
            """
        )
        stat = cursor.fetchone()

        total_billed = float(stat["total_billed"]) if stat else 0.0
        total_collected = float(stat["total_collected"]) if stat else 0.0
        total_outstanding = float(stat["total_outstanding"]) if stat else 0.0
        total_invoices = int(stat["total_invoices"]) if stat else 0
        paid_count = int(stat["paid_count"] or 0) if stat else 0
        partial_count = int(stat["partial_count"] or 0) if stat else 0
        unpaid_count = int(stat["unpaid_count"] or 0) if stat else 0
        overdue_count = int(stat["overdue_count"] or 0) if stat else 0

        rate = round((total_collected / total_billed * 100), 2) if total_billed > 0 else 0.0

        cursor.execute(
            """
            SELECT fp.*,
                   fi.invoice_no,
                   s.first_name || ' ' || s.last_name AS student_name
            FROM fee_payments fp
            JOIN fee_invoices fi ON fp.invoice_id = fi.id
            JOIN students s ON fi.student_id = s.id
            ORDER BY fp.payment_date DESC, fp.id DESC
            LIMIT 5;
            """
        )
        recent_rows = cursor.fetchall()
        cursor.close()

        return {
            "total_billed": total_billed,
            "total_collected": total_collected,
            "total_outstanding": total_outstanding,
            "collection_rate": rate,
            "total_invoices": total_invoices,
            "paid_count": paid_count,
            "partial_count": partial_count,
            "unpaid_count": unpaid_count,
            "overdue_count": overdue_count,
            "recent_payments": [dict(r) for r in recent_rows],
        }
