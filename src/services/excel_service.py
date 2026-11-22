"""Streaming Excel (.xlsx) Data Exporter Service.
High-performance workbook generation with styling, cell formats, zebra striping,
conditional risk highlights, and auto column width using openpyxl.
"""

import io
import logging
import sqlite3
from typing import Any, List, Optional

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from src.services.reports_service import ReportsService

logger = logging.getLogger("ims")


class ExcelService:
    """Enterprise spreadsheet workbook compiler."""

    # Reusable styling presets
    HEADER_FILL = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    SUB_HEADER_FILL = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")
    ZEBRA_FILL = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    TOTALS_FILL = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")

    GREEN_FILL = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
    YELLOW_FILL = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    RED_FILL = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")

    HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    BOLD_FONT = Font(name="Calibri", size=10, bold=True, color="0F172A")
    REGULAR_FONT = Font(name="Calibri", size=10, color="334155")
    CODE_FONT = Font(name="Consolas", size=9.5, color="1E293B")

    THIN_SIDE = Side(border_style="thin", color="CBD5E1")
    GRID_BORDER = Border(left=THIN_SIDE, right=THIN_SIDE, top=THIN_SIDE, bottom=THIN_SIDE)

    @staticmethod
    def _apply_autowidth(
        ws: openpyxl.worksheet.worksheet.Worksheet, max_col_width: int = 45
    ) -> None:
        """Dynamically compute column widths from cell character lengths with visual padding."""
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                # Avoid extreme widths on multiline cells
                line_len = max(len(line) for line in val_str.split("\n")) if val_str else 0
                max_len = max(max_len, line_len)
            ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), max_col_width)

    @staticmethod
    def export_students_excel(
        conn: sqlite3.Connection, department_id: Optional[int] = None
    ) -> bytes:
        """Compile complete scholar registry workbook."""
        cursor = conn.cursor()
        query = """
            SELECT
                s.enrollment_no, s.first_name, s.last_name, s.email, s.phone,
                d.code AS department_code, d.name AS department_name,
                s.current_semester, s.status, s.admission_date
            FROM students s
            JOIN departments d ON s.department_id = d.id
            WHERE 1=1
        """
        params: List[Any] = []
        if department_id:
            query += " AND s.department_id = ?"
            params.append(department_id)
        query += " ORDER BY s.enrollment_no ASC;"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Scholars Directory"
        ws.views.sheetView[0].showGridLines = True

        headers = [
            "Enrollment No",
            "First Name",
            "Last Name",
            "Email Address",
            "Phone Number",
            "Dept Code",
            "Department Name",
            "Semester",
            "Status",
            "Admission Date",
        ]
        ws.append(headers)

        for _col_idx, cell in enumerate(ws[1], start=1):
            cell.fill = ExcelService.HEADER_FILL
            cell.font = ExcelService.HEADER_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = ExcelService.GRID_BORDER
        ws.row_dimensions[1].height = 26

        for r_idx, r in enumerate(rows, start=2):
            row_data = [
                r["enrollment_no"],
                r["first_name"],
                r["last_name"],
                r["email"],
                r["phone"] or "N/A",
                r["department_code"],
                r["department_name"],
                r["current_semester"],
                r["status"],
                r["admission_date"],
            ]
            ws.append(row_data)

            is_even = r_idx % 2 == 0
            fill = ExcelService.ZEBRA_FILL if is_even else None

            for col_idx, cell in enumerate(ws[r_idx], start=1):
                cell.font = ExcelService.REGULAR_FONT
                cell.border = ExcelService.GRID_BORDER
                if fill:
                    cell.fill = fill

                # Alignment rules
                if col_idx in (1, 6, 8, 10):
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                elif col_idx == 9:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    if cell.value == "ENROLLED":
                        cell.fill = ExcelService.GREEN_FILL
                    elif cell.value == "PROBATION":
                        cell.fill = ExcelService.RED_FILL

        ws.freeze_panes = "A2"
        ExcelService._apply_autowidth(ws)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    @staticmethod
    def export_finances_excel(
        conn: sqlite3.Connection, department_id: Optional[int] = None
    ) -> bytes:
        """Compile multi-tab institutional fiscal ledger and departmental recovery workbook."""
        cursor = conn.cursor()
        query = """
            SELECT
                fi.invoice_no, s.enrollment_no, s.first_name || ' ' || s.last_name AS student_name,
                d.code AS department_code, fi.title, fi.term_name,
                fi.total_amount, fi.paid_amount, fi.balance_amount,
                fi.status, fi.due_date, fi.created_at
            FROM fee_invoices fi
            JOIN students s ON fi.student_id = s.id
            JOIN departments d ON s.department_id = d.id
            WHERE 1=1
        """
        params: List[Any] = []
        if department_id:
            query += " AND s.department_id = ?"
            params.append(department_id)
        query += " ORDER BY fi.created_at DESC;"
        cursor.execute(query, params)
        invoices = cursor.fetchall()
        cursor.close()

        wb = openpyxl.Workbook()

        # TAB 1: Invoices Ledger
        ws1 = wb.active
        ws1.title = "Fee Ledger & Invoices"
        ws1.views.sheetView[0].showGridLines = True

        headers1 = [
            "Invoice No",
            "Enrollment No",
            "Student Name",
            "Dept",
            "Invoice Title",
            "Term",
            "Total Billed ($)",
            "Paid Amount ($)",
            "Balance Due ($)",
            "Status",
            "Due Date",
            "Issued On",
        ]
        ws1.append(headers1)
        for cell in ws1[1]:
            cell.fill = ExcelService.HEADER_FILL
            cell.font = ExcelService.HEADER_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = ExcelService.GRID_BORDER
        ws1.row_dimensions[1].height = 26

        tot_billed = 0.0
        tot_paid = 0.0
        tot_balance = 0.0

        for r_idx, inv in enumerate(invoices, start=2):
            billed = float(inv["total_amount"])
            paid = float(inv["paid_amount"])
            bal = float(inv["balance_amount"])
            tot_billed += billed
            tot_paid += paid
            tot_balance += bal

            status_str = str(inv["status"]).upper()
            row_data = [
                inv["invoice_no"],
                inv["enrollment_no"],
                inv["student_name"],
                inv["department_code"],
                inv["title"],
                inv["term_name"],
                billed,
                paid,
                bal,
                status_str,
                inv["due_date"],
                str(inv["created_at"])[:10],
            ]
            ws1.append(row_data)

            is_even = r_idx % 2 == 0
            fill = ExcelService.ZEBRA_FILL if is_even else None

            for col_idx, cell in enumerate(ws1[r_idx], start=1):
                cell.font = ExcelService.REGULAR_FONT
                cell.border = ExcelService.GRID_BORDER
                if fill:
                    cell.fill = fill

                # Format currencies
                if col_idx in (7, 8, 9):
                    cell.number_format = '"$"#,##0.00'
                    cell.alignment = Alignment(horizontal="right")
                elif col_idx in (1, 2, 4, 11, 12):
                    cell.alignment = Alignment(horizontal="center")
                elif col_idx == 10:
                    cell.alignment = Alignment(horizontal="center")
                    if status_str == "PAID":
                        cell.fill = ExcelService.GREEN_FILL
                    elif status_str == "OVERDUE":
                        cell.fill = ExcelService.RED_FILL
                    elif status_str == "PARTIAL":
                        cell.fill = ExcelService.YELLOW_FILL

        # Summary Row
        summary_row_idx = len(invoices) + 2
        ws1.append(
            [
                "TOTAL AUDIT",
                f"{len(invoices)} Invoices",
                "",
                "",
                "",
                "",
                tot_billed,
                tot_paid,
                tot_balance,
                f"{round(tot_paid / tot_billed * 100, 1) if tot_billed > 0 else 0}% Collected",
                "",
                "",
            ]
        )
        for col_idx, cell in enumerate(ws1[summary_row_idx], start=1):
            cell.font = ExcelService.BOLD_FONT
            cell.fill = ExcelService.TOTALS_FILL
            cell.border = ExcelService.GRID_BORDER
            if col_idx in (7, 8, 9):
                cell.number_format = '"$"#,##0.00'
                cell.alignment = Alignment(horizontal="right")
            elif col_idx in (1, 2, 10):
                cell.alignment = Alignment(horizontal="center")

        ws1.freeze_panes = "A2"
        ExcelService._apply_autowidth(ws1)

        # TAB 2: Department Summary
        analytics = ReportsService.get_analytics_summary(conn, department_id=department_id)
        dept_metrics = analytics.get("department_metrics", [])

        ws2 = wb.create_sheet(title="Department Fiscal Summary")
        ws2.views.sheetView[0].showGridLines = True
        headers2 = [
            "Dept Code",
            "Department Name",
            "Students Enrolled",
            "Courses Count",
            "Total Billed ($)",
            "Total Collected ($)",
            "Outstanding Balance ($)",
            "Recovery Rate (%)",
        ]
        ws2.append(headers2)
        for cell in ws2[1]:
            cell.fill = ExcelService.SUB_HEADER_FILL
            cell.font = ExcelService.HEADER_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = ExcelService.GRID_BORDER
        ws2.row_dimensions[1].height = 26

        for r_idx, d in enumerate(dept_metrics, start=2):
            inv = float(d["invoiced"])
            col = float(d["collected"])
            bal = float(d["balance"])
            rate = float(d["recovery_rate_pct"])

            ws2.append(
                [
                    d["department_code"],
                    d["department_name"],
                    d["students_count"],
                    d["courses_count"],
                    inv,
                    col,
                    bal,
                    f"{rate:.1f}%",
                ]
            )
            is_even = r_idx % 2 == 0
            fill = ExcelService.ZEBRA_FILL if is_even else None

            for col_idx, cell in enumerate(ws2[r_idx], start=1):
                cell.font = ExcelService.REGULAR_FONT
                cell.border = ExcelService.GRID_BORDER
                if fill:
                    cell.fill = fill

                if col_idx in (5, 6, 7):
                    cell.number_format = '"$"#,##0.00'
                    cell.alignment = Alignment(horizontal="right")
                elif col_idx in (1, 3, 4, 8):
                    cell.alignment = Alignment(horizontal="center")
                    if col_idx == 8 and rate >= 80.0:
                        cell.fill = ExcelService.GREEN_FILL
                    elif col_idx == 8 and rate < 50.0:
                        cell.fill = ExcelService.RED_FILL

        ws2.freeze_panes = "A2"
        ExcelService._apply_autowidth(ws2)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    @staticmethod
    def export_attendance_excel(
        conn: sqlite3.Connection, department_id: Optional[int] = None
    ) -> bytes:
        """Compile attendance register and risk sentinel audit workbook."""
        summary = ReportsService.get_analytics_summary(conn, department_id=department_id)
        at_risk = summary.get("at_risk_scholars", [])

        wb = openpyxl.Workbook()

        # TAB 1: Attendance Risk Sentinel
        ws1 = wb.active
        ws1.title = "Risk Sentinel (< 75%)"
        ws1.views.sheetView[0].showGridLines = True

        headers1 = [
            "Enrollment No",
            "First Name",
            "Last Name",
            "Email Address",
            "Department",
            "Semester",
            "Total Sessions",
            "Attended Sessions",
            "Absent Sessions",
            "Late Sessions",
            "Attendance Rate (%)",
            "Risk Assessment",
        ]
        ws1.append(headers1)
        for cell in ws1[1]:
            cell.fill = ExcelService.HEADER_FILL
            cell.font = ExcelService.HEADER_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = ExcelService.GRID_BORDER
        ws1.row_dimensions[1].height = 26

        for r_idx, s in enumerate(at_risk, start=2):
            pct = float(s["attendance_pct"])
            risk_level = str(s["risk_level"])
            ws1.append(
                [
                    s["enrollment_no"],
                    s["first_name"],
                    s["last_name"],
                    s["email"],
                    s["department_name"],
                    s["current_semester"],
                    s["total_sessions"],
                    s["attended_sessions"],
                    s["absent_sessions"],
                    s["late_sessions"],
                    f"{pct:.1f}%",
                    risk_level,
                ]
            )
            is_even = r_idx % 2 == 0
            fill = ExcelService.ZEBRA_FILL if is_even else None

            for col_idx, cell in enumerate(ws1[r_idx], start=1):
                cell.font = ExcelService.REGULAR_FONT
                cell.border = ExcelService.GRID_BORDER
                if fill:
                    cell.fill = fill

                if col_idx in (1, 6, 7, 8, 9, 10, 11, 12):
                    cell.alignment = Alignment(horizontal="center")
                if col_idx == 12:
                    if risk_level == "CRITICAL":
                        cell.fill = ExcelService.RED_FILL
                    elif risk_level == "WARNING":
                        cell.fill = ExcelService.YELLOW_FILL

        ws1.freeze_panes = "A2"
        ExcelService._apply_autowidth(ws1)

        # TAB 2: Institutional Overview
        ws2 = wb.create_sheet(title="Attendance Overview")
        ws2.views.sheetView[0].showGridLines = True
        ws2.append(["Telemetry Metric", "Audited Value", "Institutional Benchmark / Target"])
        for cell in ws2[1]:
            cell.fill = ExcelService.SUB_HEADER_FILL
            cell.font = ExcelService.HEADER_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = ExcelService.GRID_BORDER
        ws2.row_dimensions[1].height = 26

        overview_metrics = [
            (
                "Institutional Attendance Rate",
                f"{summary.get('overall_attendance_pct', 0.0)}%",
                ">= 75.0% Mandatory",
            ),
            (
                "Total Verified Class Sessions",
                str(summary.get("total_attendance_sessions", 0)),
                "Full Academic Term",
            ),
            (
                "Scholars Below Threshold (< 75%)",
                str(len(at_risk)),
                "0 Scholars (Sentinel Alert Triggered if > 0)",
            ),
            ("Total Enrolled Students", str(summary.get("total_students", 0)), "Active Cohort"),
        ]
        for r_idx, (m, v, b) in enumerate(overview_metrics, start=2):
            ws2.append([m, v, b])
            for col_idx, cell in enumerate(ws2[r_idx], start=1):
                cell.font = ExcelService.REGULAR_FONT
                cell.border = ExcelService.GRID_BORDER
                if col_idx == 2:
                    cell.font = ExcelService.BOLD_FONT
                    cell.alignment = Alignment(horizontal="center")

        ws2.freeze_panes = "A2"
        ExcelService._apply_autowidth(ws2)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()
