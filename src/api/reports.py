"""Institutional Reports & Analytics API Router."""

import sqlite3
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from src.database.connection import get_db
from src.services.reports_service import ReportsService

router = APIRouter(prefix="/api/reports", tags=["Reports & Analytics"])


@router.get("/analytics-summary")
def get_analytics_summary(
    department_id: Optional[int] = Query(None, description="Filter analytics by department ID"),
    conn: sqlite3.Connection = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve full institutional telemetry, attendance risk sentinel, and financial recovery metrics."""
    return ReportsService.get_analytics_summary(conn, department_id=department_id)


@router.get("/export/students/csv")
def export_students_csv(
    department_id: Optional[int] = Query(None, description="Filter export by department ID"),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    """Download registered scholar directory as a standardized CSV file."""
    csv_data = ReportsService.export_students_csv(conn, department_id=department_id)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=students_roster.csv"},
    )


@router.get("/export/attendance-risk/csv")
def export_attendance_risk_csv(
    department_id: Optional[int] = Query(None, description="Filter export by department ID"),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    """Download attendance sentinel at-risk (< 75%) scholar report as CSV."""
    csv_data = ReportsService.export_attendance_risk_csv(conn, department_id=department_id)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance_risk_sentinel.csv"},
    )


@router.get("/export/finances/csv")
def export_finances_csv(
    department_id: Optional[int] = Query(None, description="Filter export by department ID"),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    """Download bursar fee ledger and student invoice audit as CSV."""
    csv_data = ReportsService.export_financial_ledger_csv(conn, department_id=department_id)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=financial_ledger_audit.csv"},
    )
